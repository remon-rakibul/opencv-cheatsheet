import microgear.client as microgear
import cv2
import numpy as np
import imutils
from imutils.video import VideoStream
import time
import argparse

key = 'your key'
secret = 'your secret key'
app = 'your app id'
microgear.create(key, secret, app, {'debugmode': True})
connected = False


def connection():
    global connected
    connected = True
    print("Connected")


def callback_error(msg):
    print(msg)


def callback_reject(msg):
    print(msg)
    print("Script exited")
    exit(0)


def subscription(topic, msg):
    if msg == "b'?'":
        microgear.publish("/countPeople", countPeople)


def CheckLineCrossing(centerMove, CoorExitLine1, CoorExitLine2):
    (x, y) = centerMove
    # outside
    if (y > CoorExitLine1[1]) and (x >= CoorExitLine1[0]):
        return True
    # inside
    else:
        return False


def autoPop(arr, lenght):
    if len(arr) > lenght:
        arr.pop(0)


def definePoint12(rec):
    return (rec[0], rec[1]), (rec[2]+rec[0], rec[3]+rec[1])


def setCenter(box):
    return (int(box[0]+box[2]/2), int(box[1]+box[3]/2))


def findDistance(rec1, rec2):
    distance = 10000
    if rec1 is not None and rec2 is not None:
        centerRec1 = setCenter(rec1)
        centerRec2 = setCenter(rec2)
        diffMinX = abs(centerRec1[0] - centerRec2[0])
        diffMinY = abs(centerRec1[1] - centerRec2[1])
        distance = (pow(diffMinX, 2) + pow(diffMinY, 2))**(1/2)
    return distance


def findTrack(bbox, focus):
    index = -1
    if pointMove != []:
        # set dif of last
        last = pointMove[len(pointMove)-1][len(pointMove[len(pointMove)-1])-1]
        distanceMin = findDistance(last, bbox)
        index = len(pointMove)-1
        for i in range(len(pointMove)-1):
            rec = pointMove[i][len(pointMove[i])-1]
            distance = findDistance(rec, bbox)
            if distance < distanceMin:
                index = i
                distanceMin = distance
        rec = pointMove[index][len(pointMove[index])-1]
        pdistance = findDistance(focus, bbox)

        distanceMax = int(0.003 * pdistance ** (2))
        if rec[2] * rec[3] > bbox[2] * bbox[3]:
            max = ((pow(rec[2], 2) + pow(rec[3], 2))**(1/2))/2
        else:
            max = ((pow(bbox[2], 2) + pow(bbox[3], 2))**(1/2))/2
        if distanceMin >= distanceMax + max:
            index = -1
    return index


def TrackMove(rec, pfocus):
    global pointMove, firstTrack, statusMove
    # find track
    indexTrack = findTrack(rec, pfocus)
    p1, p2 = definePoint12(rec)
    # set new track
    if indexTrack == -1:
        indexTrack = len(firstTrack)
        firstTrack.append(rec)
        pointMove.append([])
        pointMove[indexTrack].append(rec)
        statusMove.append(30)
    else:
        pointMove[indexTrack].append(rec)
        statusMove[indexTrack] = 30
    autoPop(pointMove[indexTrack], 2)
    return indexTrack


def popIndex(firstTrack, pointMove, statusMove, i):
    firstTrack.pop(i)
    pointMove.pop(i)
    statusMove.pop(i)


def checkmark(Frame, frameSize, sizeLong, OffsetY, OffsetX):
    # load the Frame
    #frameSize1 = (600, 450)
    areaFrame = frameSize[0] * frameSize[1]

    # define the list of boundaries
    boundary = ([40, 150,  30], [80, 210, 160])

    marks = []
    (lower, upper) = boundary
    # create NumPy arrays from the boundaries
    lower = np.array(lower, dtype="uint8")
    upper = np.array(upper, dtype="uint8")

    # find the colors within the specified boundaries and apply
    # the mask
    image_hsv = cv2.cvtColor(Frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(image_hsv, lower, upper)
    output = cv2.bitwise_and(Frame, Frame, mask=mask)
    # Dilate image and find all the contours
    _, cnts, _ = cv2.findContours(
        mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    for cnt in cnts:
        Area = cv2.contourArea(cnt)
        if Area < areaFrame * 0.00037 or Area > areaFrame * 0.00074:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(output, (x, y), (x+w, y+h), (0, 0, 255), 2)
        if w > h*1.3:
            marks.append(setCenter((x, y, w, h)))
    if len(marks) >= 2:
        if marks[1][0] < marks[0][0]:
            tmp = marks[0]
            marks[0] = marks[1]
            marks[1] = tmp
        sizeLong = int(abs(marks[0][0] - marks[1][0])/2)
        OffsetY = int(frameSize[1] - (marks[0][1] + marks[1][1]) / 2)
        OffsetX = int(frameSize[0]/2 - (marks[0][0] + sizeLong))
        # break
    return sizeLong, OffsetY, OffsetX


#global variables
# Set initial frame size.
frameSize = (800, 600)
areaFrame = frameSize[0] * frameSize[1]

# minimum size 0.01%/maximum size 0.1%
MinCountourArea = areaFrame * 0.01
MaxCountourArea = areaFrame * 0.1

# line's position
OffsetY = int(frameSize[1] * 0.25)
OffsetX = -30
sizeLong = int(frameSize[0] * 0.3)
#padding = frameSize[1] * 0.02
margin = frameSize[1] * 0.03

# tracking variable
pointMove = []
firstTrack = []
statusMove = []

# define counting number of people
countPeople = 0

idle_time = 0

# object for BackgroundSubtractor
fgbg = cv2.createBackgroundSubtractorMOG2(
    history=2000, varThreshold=100, detectShadows=False)
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
args = vars(ap.parse_args())
# How sizeLong have we been tracking


# Initialize mutithreading the video stream.
if args["video"] is None:
    camera = VideoStream(src=0, usePiCamera=True,
                         resolution=frameSize, framerate=32).start()
else:
    camera = cv2.VideoCapture(args["video"])

time.sleep(2.0)


this_name = 'CAMERA'
microgear.setname(this_name)
microgear.on_reject = callback_reject
microgear.on_connect = connection
microgear.on_message = subscription
microgear.on_error = callback_error
microgear.connect(False)
microgear.publish("/countPeople", countPeople)
# Get the next frame.
while True:
    # If using a webcam instead of the Pi Camera,
    if args["video"] is None:
        Frame = camera.read()
    # If using a video file
    else:
        _, Frame = camera.read()
        # cannot fetch Frame
        if (Frame is None):
            break
        Frame = imutils.resize(Frame, width=frameSize[0])
    # cannot fetch Frame
    if (Frame is None):
        break

    # gray-scale convertion and Gaussian blur filter applying
    Gray = cv2.cvtColor(Frame, cv2.COLOR_BGR2GRAY)
    ret, Gray = cv2.threshold(Gray, 40, 100, cv2.THRESH_BINARY)
    if idle_time < 2:
        idle_time += 1
        continue
        #OffsetY += 15
    fgmask = fgbg.apply(Gray)
    fgmask = cv2.erode(fgmask, None, 20)

    _, cnts, _ = cv2.findContours(
        fgmask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    # plot reference lines (entrance and exit lines)
    centerLine = (int(frameSize[0]/2 - OffsetX), int(frameSize[1]-OffsetY))
    CoorExitLine1 = (centerLine[0] - sizeLong, centerLine[1])
    CoorExitLine2 = (centerLine[0] + sizeLong, centerLine[1])
    cv2.line(Frame, CoorExitLine1, CoorExitLine2, (0, 0, 255), 2)
    Line = (CoorExitLine1[0], CoorExitLine1[1], CoorExitLine2[0] -
            CoorExitLine1[0], CoorExitLine2[1] - CoorExitLine2[1])

    # check all found countours
    for c in cnts:
        Area = cv2.contourArea(c)
        rec = cv2.boundingRect(c)
        p1, p2 = definePoint12(rec)
        cv2.rectangle(Frame, p1, p2, (0, 255, 200), 2)
        if Area > MaxCountourArea:
            continue
        elif Area < MinCountourArea:
            break

        # find object's centroid
        ObjectCentroid = setCenter(rec)
        indexTrack = TrackMove(rec, Line)

        (x, y, w, h) = firstTrack[indexTrack]
        colorB = 0
        colorR = 0
        firstCenter = setCenter(firstTrack[indexTrack])

        if CheckLineCrossing(firstCenter, CoorExitLine1, CoorExitLine2):
            colorR = 255
        else:
            colorB = 255

        cv2.rectangle(Frame, p1, p2, (colorB, int(
            (indexTrack+1)*70), colorR), 2)

        if abs(firstCenter[1]-CoorExitLine1[1]) > margin and abs(ObjectCentroid[1]-CoorExitLine1[1]) > margin:
            if not CheckLineCrossing(firstCenter, CoorExitLine1, CoorExitLine2) and CheckLineCrossing(ObjectCentroid, CoorExitLine1, CoorExitLine2):
                countPeople -= 1
                firstTrack[indexTrack] = rec
                microgear.publish(
                    "/countPeople", countPeople, {'retain': True})
            elif not CheckLineCrossing(ObjectCentroid, CoorExitLine1, CoorExitLine2) and CheckLineCrossing(firstCenter, CoorExitLine1, CoorExitLine2):
                countPeople += 1
                firstTrack[indexTrack] = rec
                microgear.publish(
                    "/countPeople", countPeople, {'retain': True})
    for i in range(len(statusMove)):
        if statusMove[i] <= 0:
            popIndex(firstTrack, pointMove, statusMove, i)
            break

    # Write entrance and exit counter values on frame and shows it
    cv2.putText(Frame, "count: {}".format(str(countPeople)), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)

    cv2.imshow("Original Frame", Frame)
    for i in range(len(statusMove)):
        statusMove[i] -= 1
    idle_time += 1
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    # cv2.waitKey(0)

# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
