"""
Gopher Tortoise Detector
Mike Hilton, Eckerd College
2021/07/06

This is an example animal detector for use with the Eckerd Camera Trap Tools.

To use this detector, you must have the TensorFlow Object Detection API installed.
Google "tensorflow object detection api" to find the latest instructions on how to 
install the API.

The class TortoiseDetector implements a neural net-based tortoise detector that
combines the EfficientDet object detector and the MobileNet image classifier to 
create a hybrid architecture that gives decent performance using a small number of
training images.  The EfficientDet object detector is run with a low required confidence 
level (say, 20%) resulting in many tortoise candidates being detected.  The region 
associated with each candidate is extracted from the original image, resized to 
224 × 224 pixels, and fed into the MobileNet image classifier to determine if the 
region contains a tortoise.  Only those candidate regions determined to contain a 
tortoise with a degree of confidence greater than a user-specified threshold (say, 
90%) are kept.  For this scheme to work properly, MobileNet must be trained on 
sample candidate images generated by EfficientDet.  In the parlance of object detection, 
EfficientDet is acting as a “region proposal network” for MobileNet.
"""

# 3rd party modules
import cv2
import numpy as np
import tensorflow as tf

# modules that are part of this package
from .. animal_detector import TrailCamObjectDetector
from . EfficientDet0.ed_objdet import OD_EfficientDet0
from . MobileNet.mn_objdet import OD_MobileNet

# magic words necessary to make tensorflow work properly on my GPU
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)


class TortoiseDetector(TrailCamObjectDetector):
    def __init__(self, app_config):
        """
        Input:
            app_config      ConfigParser object created by instantiating program
        """
        super().__init__(app_config)
        self.od1 = OD_EfficientDet0(app_config)
        self.od2 = OD_MobileNet(app_config)


    def _object_detection(self, image_file):
        """
        Run the object detection algorithm on the supplied image.
        Inputs:
            image_file      string; path to image
        Returns:
            N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper), bounding boxes around
            the detected objects 
        """
        # load the file
        img = cv2.imread(image_file) 
        if img is None:
            raise Exception("Tortoise detector unable to read image file: " + image_file)
            
        # the first detection pass uses the EfficientDet0 CNN as a region proposal generator
        _, boxes1, _ = self.od1.run_inference_on_image(img, False)
        if boxes1.shape[0] == 0:
            return []

        # convert the normalized boxes1 into absolute coordinates for use by MobileNet
        abs_boxes1 = []
        for yl, xl, yu, xu in boxes1:
            # convert the normalized coordinates into integer coordinates
            xl = int(xl * img.shape[1])
            yl = int(yl * img.shape[0])
            xu = int(xu * img.shape[1])
            yu = int(yu * img.shape[0])   
            abs_boxes1.append([yl, xl, yu, xu])

        # the second detection pass uses MobileNet CNN to confirm the presence of a tortoise in the box
        _, boxes2 = self.od2.run_inference_on_boxes(img, abs_boxes1)  

        return boxes2


    def _postprocessBoxes(self, boxes):
        """
        Perform any additional filtering that needs to be done on the boxes.  Non-maxima suppression
        is used, then objects are removed that are mostly inside the information banner at the bottom of the 
        Meidase SL122 Pro camera's 4-megapixel image, and finally, objects that are smaller than 50,000
        pixels in area are removed.        
        Inputs:
            boxes is a N x 4 numpy array of the bounding boxes containing what MobileNet thinks are tortoises, [yStart, xStart, yEnd, xEnd]   
        Returns:
            A list of boxes, each of which is a list of the form [yStart, xStart, yEnd, xEnd]       
        """
        # remove the smaller of overlapping boxes
        idxs = self._non_max_suppression(boxes, self.nms_overlap)
        modBoxes = boxes[idxs]

        answer = []
        for i in range(modBoxes.shape[0]):
            remove = False
            
            # remove any objects whose box is mostly inside the image banner   
            if (modBoxes[i][0] > 1288) and (modBoxes[i][2] > 1288):
                remove = True

            # remove any objects that are too small
            area = abs(modBoxes[i][0] - modBoxes[i][2]) * abs(modBoxes[i][1] - modBoxes[i][3])
            if area < 50000:
                remove = True            

            if not remove:
                answer.append(modBoxes[i].tolist())

        return answer
    
