# Face detection with OpenCV and deep learning

https://www.pyimagesearch.com/2018/02/26/face-detection-with-opencv-and-deep-learning/

# Image

```bash
python detect_faces.py --image rooster.jpg --prototxt deploy.prototxt.txt \
	--model res10_300x300_ssd_iter_140000.caffemodel

python detect_faces.py --image iron_chic.jpg --prototxt deploy.prototxt.txt \
	--model res10_300x300_ssd_iter_140000.caffemodel
```

# Video

```bash
python detect_faces_video.py --prototxt deploy.prototxt.txt \
	--model res10_300x300_ssd_iter_140000.caffemodel
```