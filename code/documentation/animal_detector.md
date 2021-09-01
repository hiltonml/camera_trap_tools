# Animal Detectors

The ```autocopy.py``` program can be configured to run an animal detection algorithm
on images as they are copied from an SD card.  The Camera Trap Tools suite is
currently designed to support only binary detectors, i.e., algorithms that indicate
the presence or absence of the species of interest.  The animal detection results are
used to create a draft video segmentation indicating which frames of the time-lapse video
contain animals.  (See the documentation for the [```create_annotations.py```](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/create_annotations.md) and [```annotator.py```](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/annotator.md)
programs.)

## Creating Animal Detectors

Two example animal detector implementations are provided:
- The ```utils/genericdetector``` folder contains an image classifier-based
algorithm that indicates if one or more animals of the species of interest is present in an image, but does
not indicate where the animals are in the image.  A Google Colab [notebook](https://github.com/hiltonml/camera_trap_tools/blob/main/code/utils/genericdetector/Generic_Animal_Detector.ipynb) is provided showing one way to train
an image classifier for use with the generic detector.
- The ```utils/tortoisedetector``` folder contains an object detection-based algorithm that indicates if one or more gopher tortoises
are present in an image and provides bounding box coordinates indicating the location of each tortoise.  These bounding boxes are displayed by the ```annotator.py``` program.

The examples provided use TensorFlow, but you are free to use whatever machine learning library you wish in your 
implementations.

The class ```TrailCamObjectDetector```, found in the ```utils/animal_detector.py``` file, is the abstract base class for animal
detectors.  To create an animal detector that works with your species of interest,
you should create a new class that inherits from ```TrailCamObjectDetector```
and implements the method 
    ```_object_detection(self, image_file)```
where *image_file* is the file path of the image to run the animal detector on. 
The result should be an _N_ x 4 numpy array of bounding boxes indicating 
the extent of each of the _N_ animals detected.  

You can implement an image classifier
instead of an object detector. In that case, if no animal was detected, 
return an empty list; if an animal was detected, return a 1 x 4 numpy array 
containing a single bounding box the size of the entire image.
 
You might also wish to implement the method 
    ```_postprocessBoxes(self, boxes)```
where *boxes* is the numpy array returned by the ```_object_detection``` method.
The purpose of this method is to perform any application- or camera-specific 
postprocessing to eliminate spurious boxes.

