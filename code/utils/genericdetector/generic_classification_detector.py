"""
Generic Image Classification-Based Animal Detector 
Mike Hilton, Eckerd College
3 August 2021

This is a generic image classification-based animal detector for use with 
the autocopy.py program found in the Eckerd Camera Trap Tools suite.  This
image classifier is based on XceptionNet.  A companion Google Colab notebook
shows how to train a classifier for your species of interest.
"""

# standard Python modules
import configparser
import os
import pickle

# 3rd party modules
import numpy as np
import tensorflow as tf
import tensorflow.keras as keras

# modules that are part of this package
from .. animal_detector import TrailCamObjectDetector

INPUT_DIMS = [299, 299]                     # size of images handled by Xception


class ClassifierConfig:
    """ 
    Configuration settings for this animal detector.   
    """
    def __init__(self, config_filename):
        """
        Loads settings from the object detector's configuration file.
        Inputs:
            config_filename     string; path to configuration file
            app_config          parent application's configuration object
        """
        self.config = configparser.ConfigParser()         
        assert os.path.exists(config_filename), f"Confguration file not found: {config_filename}"
        self.config.read(config_filename)

        # read the settings
        settings = self.config["Generic_Detector"]
        # file containing the trained convolutional neural net weights, in H5 format
        self.model_file = os.path.join(os.path.dirname(__file__), settings["model_h5_file"])
        # pickle file containing the label encoder
        self.label_encoder = os.path.join(os.path.dirname(__file__), settings["label_encoder"])
        # label for the animal present class
        self.present_label = settings["present_label"]
        # confidence threshold
        self.threshold = float(settings.get("threshold", 0.9))




class GenericDetector(TrailCamObjectDetector):        
    def __init__(self, app_config):
        """
        Input:
            app_config      ConfigParser object created by instantiating program
        """
        super().__init__(app_config) 

        # read the configuration file
        configFile = self.getConfigFilename()
        self.gd_config = ClassifierConfig(configFile)

        # initialize the label binarizer
        self.lb = pickle.loads(open(self.gd_config.label_encoder, "rb").read()) 
        self.classes = self.lb.classes_

        # load the saved neural net
        self.model = tf.keras.models.load_model(self.gd_config.model_file)


    def getConfigFilename(self):
        """
        Creates a config filename from this module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def _object_detection(self, image_file):
        """
        Run the animal detection algorithm on the supplied image.
        Inputs:
            image_file      string; path to image
        Returns:
            N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper), bounding boxes around
            the detected objects 
        """
        # load the image file
        image = keras.preprocessing.image.load_img(image_file, target_size=INPUT_DIMS)
        image = keras.preprocessing.image.img_to_array(image)
        return self._object_detection_from_image(image)


    def _object_detection_from_image(self, image):
        """
        Run the animal detection algorithm on the supplied numpy array.
        Inputs:
            image       numpy array
        Returns:
            N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper), bounding boxes around
            the detected objects         
        """
        # resize image if necessary
        if image.shape[0] != INPUT_DIMS[0] or image.shape[1] != INPUT_DIMS[1]:
            img = tf.image.resize(image, INPUT_DIMS)
        else:
            img = image

        img = keras.applications.xception.preprocess_input(img)            
        data = np.array([img], dtype="float32")

        # run the model
        scores = self.model.predict(data)

        # get label for the class with highest score
        labels = self.classes[np.argmax(scores, axis=1)]
        idxs = np.where(labels == self.gd_config.present_label)[0]   

        # check that scores are >= threshold
        scores = scores[idxs][:, 1]
        idxs = np.where(scores >= self.gd_config.threshold)

        if len(idxs[0]) > 0:
            # focal species was present
            answer = [[0, 0, image.shape[0], image.shape[1]]]
        else:
            # focal species not found
            answer = []

        return answer        


    def _postprocessBoxes(self, boxes):
        """
        Perform any additional filtering that needs to be done on the boxes.                  
        Inputs:
            boxes is a N x 4 numpy array of the bounding boxes containing what MobileNet thinks are tortoises, [yStart, xStart, yEnd, xEnd]   
        Returns:
            A list of boxes, each of which is a list of the form [yStart, xStart, yEnd, xEnd]       
        """
        # no processing needs to be done for image classification-based detectors
        return boxes
    
