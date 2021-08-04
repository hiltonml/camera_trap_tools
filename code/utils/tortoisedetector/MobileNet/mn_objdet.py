"""
Trail Camera Object Detector
Mike Hilton, Eckerd College

The class OD_MobileNet implements an object detector based on the 
Keras MobileNet object detector that has been fine-tuned to recognize
tortoises.
"""

import cv2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import numpy as np
import pickle


class OD_MobileNet:
    def __init__(self, od_config):
        # MobileNet settings
        settings = od_config.config["MobileNet"]
        self.draw_boxes = bool(int(settings["draw_boxes"]))             # indicates if bounding boxes for objects should be drawn on image
        self.model_path = settings["model_path"]						# path to MobileNet h5 file
        self.label_map = settings["label_map"]							# pickle file containing label map
        self.target_class = settings["target_class"]                    # name of the target class
        self.threshold = float(settings["threshold"])					# object detection score threshold
        # initialize the detector
        self.input_dims = (224, 224)        
        self.labels = pickle.loads(open(self.label_map, "rb").read())
        self.model = load_model(self.model_path)


    def draw_boxes(self, image, boxes, scores, color):
        # loop over the bounding box indexes
        for i in range(len(boxes)):
            # draw the bounding box, label, and probability on the image
            (startY, startX, endY, endX) = boxes[i]
            cv2.rectangle(image, (startX, startY), (endX, endY), color, 2)
            y = startY - 10 if startY - 10 > 10 else startY + 10
            text= "{:.2f}%".format(scores[i] * 100)
            cv2.putText(image, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)


    def run_inference_on_boxes(self, image, boxes, draw_detections=None):
        """
        Runs MobileNet on the regions of the image specified by boxes.
        Inputs:
            image       numpy image array
            boxes       numpy N x 4 array of bounding boxes in absolute coordinates
        Returns:
            A tuple of the form (scores, boxes) where:
                scores is a N element numpy array containing the classification scores of the boxes
                boxes is a N x 4 numpy array of the bounding boxes containing what MobileNet thinks are tortoises, [yStart, xStart, yEnd, xEnd]                 
        """
        # initialize the list of region proposals that we'll be classifying
        proposals = []

        # loop over the region proposal bounding box coordinates
        for yl, xl, yu, xu in boxes:
            # extract the proposed region from the input image
            roi = image[yl:yu, xl:xu, :]
            # convert it from the BGR color format used by cv2 to RGB format required by Keras
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            # resize the region to the required input dimensions of the detector            
            roi = cv2.resize(roi, self.input_dims, interpolation=cv2.INTER_CUBIC)        
            # further preprocess the ROI, as required by Keras
            roi = img_to_array(roi)
            roi = preprocess_input(roi)
            # update the proposals list
            proposals.append(roi)
        

        # convert the proposals and bounding boxes into NumPy arrays
        proposals = np.array(proposals, dtype="float32")
        boxes = np.array(boxes, dtype="int32")

        # classify each of the proposal ROIs using the fine-tuned MobileNet model
        scores = self.model.predict(proposals)   

        # filter the predictions to include only those positive for the target class
        labels = self.labels.classes_[np.argmax(scores, axis=1)]
        idxs = np.where(labels == self.target_class)[0]
        boxes = boxes[idxs]
        scores = scores[idxs][:, 1]

        # return only the results for objects with scores above the threshold
        idxs = np.where(scores >= self.threshold)
        scores = scores[idxs]
        boxes = boxes[idxs] 

        self.postprocessBoxes(boxes, scores)

        # draw object bounding boxes if appropriate
        if draw_detections is None:
            draw_detections = self.draw_boxes
        if draw_detections:
            self.draw_boxes(image, boxes, scores, (0, 255, 0))

        return scores, boxes  

    def postprocessBoxes(self, boxes, scores):
        """
        Perform any additional filtering that needs to be done on the boxes.
        Inputs:
            scores is a N element numpy array containing the classification scores of the boxes
            boxes is a N x 4 numpy array of the bounding boxes containing what MobileNet thinks are tortoises, [yStart, xStart, yEnd, xEnd]   
        Returns:
            A pair consisting of (list of boxes, list of scores)
        """
        modBoxes = []
        modScores = []
        
        # remove any objects whose box is totally inside the image banner   
        for i in range(len(boxes)-1,-1, -1):
            pass
