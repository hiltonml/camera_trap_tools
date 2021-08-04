"""
Trail Camera Animal Detector Base Class
Mike Hilton, Eckerd College
2021/07/06

The class TrailCamObjectDetector is an abstract base class for animal
detectors compatible with the programs in the Eckerd Camera_Trap_Tools
package.

To create an animal detector that works with your species of interest,
you should create a new class that inherits from TrailCamObjectDetector
and implements the method 
    _object_detection(self, image_file)
where image_file is the file path of the image to run the animal detector on. 
The result should be an N x 4 numpy array of bounding boxes indicating 
the extent of each object detected.  You can implement an image classifier
instead of an object detector. In that case, if no animal was detected, 
return an empty list; if an animal was detected, return an array 
containing a single bounding box the size of the entire image.
 
You might also wish to implement the method 
    _postprocessBoxes(self, boxes)
where boxes is the numpy array returned by the _object_detection method.
The purpose of this method is to perform any application- or camera-specific 
postprocessing to eliminate spurious boxes.

See the documentation for both methods below.  You can also refer to the 
example implementation included in the tortosedetector folder.

You are free to use whatever machine learning library you wish in your 
implementation.
"""

# standard Python modules
import os

# 3rd party modules
import numpy as np

# modules that are part of this package
from . trailcamutils import imagePathFromFilename


class TrailCamObjectDetector:
    def __init__(self, app_config):
        """
        Input:
            app_config      ConfigParser object created by instantiating program
        """
        self.app_config = app_config
        # general settings shared by multiple trail_camera_tools programs        
        settings = app_config.app_config["General_Settings"]
        self.detection_box_folder = settings.get(                       # path to folder where animal detection box data is written
            "detection_box_folder", None)
        self.detection_log = settings.get(                              # path to detection log file
            "detection_log_file", None)
        # settings specific to this program
        settings = app_config.app_config["Animal_Detector"]
        self.nms_overlap = float(settings.get("max_nms_overlap", 0.1))  # maximum fraction of bounding box overlap allowed before non-maxima suppression routine prunes smaller box 
        self.supported_views = settings.get("supported_views", "")      # abbreviated names of views detector can be run on

        # split supported_views string into a list of views
        self.supported_views = [x.strip() for x in self.supported_views.split(",")]
        # open the detection log for appending
        if self.detection_log is not None:
            self.detection_log = open(self.detection_log, "a")


    def close(self):
        """
        Releases any resources allocated 
        """
        if self.detection_log is not None:
            self.detection_log.close()


    def detect(self, image_file, abbrev_view=None):
        """
        Run the animal detection algorithm on the specified image.
        Input:
            image_file          string; path to image file
            abbrev_view         string; Abbreviated name of camera view associated with this image.
                                    If None, detection is always run on image; otherwise, abbrev_view
                                    must be a member of the supported views list for detection to be
                                    run.
        """
        if (abbrev_view is None) or (abbrev_view in self.supported_views):
            # detect objects
            boxes = self._object_detection(image_file) 
            boxes2 = self._postprocessBoxes(boxes)      

            # log the number of detected objects  
            count = len(boxes2)                                       
            if (count > 0) and (self.detection_log is not None):
                self.detection_log.write(f"{image_file}, {count}\n")

            # write the bounding box info file
            if self.detection_box_folder is not None:
                box_file = os.path.join(
                    self.detection_box_folder,
                    imagePathFromFilename(image_file, self.app_config.prefix, self.app_config.views),
                    os.path.splitext(image_file)[0] + ".boxes"
                )
                self._write_boxes(box_file, boxes2, (0, 255, 0))


    def _non_max_suppression(self, boxes, threshold):
        """
        Non-maxima suppression implemented using Malisiewicz et al. algorithm.  Filters
        the boxes list to remove smaller boxes that overlap with a larger box.
        Inputs:
            boxes       N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper); 
                            the bounding boxes containing what the object detector thinks 
                            are objects of interest  
            threshold   float; Overlap threshold
        Returns:
            Numpy array of integer indices indicating which boxes to keep
        """
        # if there are no boxes, return an empty list
        if len(boxes) == 0:
            return []

        # if the bounding boxes integers, convert them to floats --
        # this is important since we'll be doing a bunch of divisions
        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        # grab the coordinates of the bounding boxes
        y1 = boxes[:,0]
        x1 = boxes[:,1]
        y2 = boxes[:,2]
        x2 = boxes[:,3]

        # compute the area of the bounding boxes and sort the bounding
        # boxes by the bottom-right y-coordinate of the bounding box
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(y2)

        # keep looping while some indexes still remain in the indexes
        # list
        pick = []
        while len(idxs) > 0:
            # grab the last index in the indexes list and add the
            # index value to the list of picked indexes
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)
            # find the largest (x, y) coordinates for the start of
            # the bounding box and the smallest (x, y) coordinates
            # for the end of the bounding box
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])
            # compute the width and height of the bounding box
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
            # compute the ratio of overlap
            overlap = (w * h) / area[idxs[:last]]
            # delete all indexes from the index list that have too much overlap
            idxs = np.delete(idxs, np.concatenate(([last],
                np.where(overlap > threshold)[0])))

        # return a list of indices for the bounding boxes that were picked 
        return np.asarray(pick)


    def _object_detection(self, image_file):
        """
        ******* YOU WILL NEED TO IMPLEMENT THIS METHOD IN YOUR SUBCLASS.

        Object detection driver.  The result is an N x 4 numpy array of
        of bounding boxes indicating the extent of each object detected.
        Inputs:
            image_file      string; path to image
        Returns:
            N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper), bounding boxes around
            the detected objects  
        """
        return np.asarray([(10, 10, 50, 75)])


    def _postprocessBoxes(self, boxes):
        """
        ******* YOU SHOULD PROBABLY IMPLEMENT THIS METHOD IN YOUR SUBCLASS, TO HANDLE ISSUES 
        ******* SPECIFIC TO YOUR APPLICATION.

        Perform any additional filtering that needs to be done on the boxes.
        Inputs:
            boxes   N x 4 numpy array of format (y_lower, x_lower, y_upper, x_upper); 
                        the bounding boxes containing what the object detector thinks are objects of interest   
        Returns:
            A list of tuples, each of which is a list of the form (y_lower, x_lower, y_upper, x_upper)      
        """
        # remove the smaller of overlapping boxes
        idxs = self._non_max_suppression(boxes, self.nms_overlap)
        answer = boxes[idxs]
        return answer.tolist()
    

    def _write_boxes(self, file_path, boxes, color):
        """
        Write information about the detections to a text file.
        Inputs:
            file_path       string; path to the text file
            boxes           list of [yl, xl, yu, xu] bounding box coordinates
            color           tuple of (Blue, Green, Red) color values
        """
        if len(boxes) > 0:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "a") as f:
                for i in range(len(boxes)):
                    yl, xl, yu, xu = boxes[i]
                    f.write(f"{yl},{xl},{yu},{xu},{color[0]},{color[1]},{color[2]}\n")