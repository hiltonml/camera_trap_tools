"""
Generate Annotation Files From an Object Detection Log File
Mike Hilton, Eckerd College
2021/07/06

This program ingests the current object detection log file
and creates a draft video segmentation for use by the annotator app.
"""

# standard Python modules
import argparse
import configparser
import os

# modules that are part of this package
import utils.trailcamutils as trailcamutils


class AppConfig:
    """ 
    Configuration settings for this application
    """
    def __init__(self, configFilename):
        """
        Loads settings from the app configuration file.
        """
        self.app_config = configparser.ConfigParser()        
        assert os.path.exists(configFilename), f"Confguration file not found: {configFilename}"
        self.app_config.read(configFilename)

        # general settings shared by multiple trail_camera_tools programs
        settings = self.app_config["General_Settings"]  
        self.annotation_folder = settings["default_annotation_folder"]      # path to folder where annotations go 
        self.boxes_folder = settings["detection_box_folder"]                # path to object detection box files
        self.detection_log_file = settings["detection_log_file"]            # path to detection log
        self.image_folder = settings["default_image_folder"]                # path to folder where images files are
        self.prefix = settings.get("prefix", "")                            # filename prefix string        

        # settings specific to this program 
        settings = self.app_config["Create_Annotations"]        
        self.append_annotations = bool(int(settings.get("append_annotations", 1)))  # indicates if annotations should be appended to existing annotation file
        self.sequence_break_threshold = int(settings.get("sequence_break_threshold", 5))   # number of non-detected images needed to indicate break in sequence

        # camera viewpoint names
        settings = self.app_config["Camera_Views"]
        self.views = {}
        for digit in range(10):
            if str(digit) in settings:
                parts = settings[str(digit)].split(",")
                if len(parts) != 2:
                    raise Exception("Camera view is not of the form <digit> = <full name of view>, <single-character abbreviation of view name>")
                else:
                    self.views[str(digit)] = (parts[0].strip(), parts[1].strip())


class AnnotationCreator:
    def __init__(self, configFile=None):
        """
        Loads settings from the app configuration file.
        """
        # read the configuration file
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)


    def createAnnotationFiles(self, detections):
        """
        Creates annotation files for the supplied detections.
        Input:
            detections      dictionary produced by the ReadDetectionsLogFile method
        """
        # iterate through the detections dictionary
        for _, dates in detections.items():
            for date, detection_files in dates.items():                
                # generate an annotation file for this date
                annotations = []

                # get a list of all the image files for this camera on this date
                images_path = os.path.join(
                    self.app_config.image_folder, 
                    trailcamutils.imagePathFromFilename(detection_files[0][0], self.app_config.prefix, self.app_config.views)
                    )
                if not os.path.exists(images_path):
                    continue
                all_files = trailcamutils.getFilenamesInFolder(images_path)
                
                # iterate across all the detection files, looking for contiguous sequences of files
                startIdx = -1
                prevIdx = 0
                prevCount = 0
                for det_file, count in detection_files:
                    # get the index of det_file in the timeline for this date
                    idx = all_files.index(os.path.basename(det_file))

                    if startIdx == -1:
                        # this marks the start of a new segment
                        startIdx = idx
                        prevIdx = idx
                        prevCount = 0

                    if (idx - prevIdx > self.app_config.sequence_break_threshold) or ((prevCount > 0) and (count != prevCount)):
                        # there is a break in the sequence, so create an annotation entry
                        start_datetime = trailcamutils.datetimeFromImageFilename(all_files[startIdx], self.app_config.prefix, self.app_config.views)
                        end_datetime = trailcamutils.datetimeFromImageFilename(all_files[prevIdx], self.app_config.prefix, self.app_config.views)
                        if prevCount > 1:
                            activity = "> 1"
                        else:
                            activity = "1"
                        annotations.append((activity, 'AI_count', 'AI_count', start_datetime, end_datetime, 'AI'))

                        # start a new segment
                        startIdx = idx
                        prevCount = count

                    prevIdx = idx
                    prevCount = count

                # final segment
                if startIdx != -1:
                    start_datetime = trailcamutils.datetimeFromImageFilename(all_files[startIdx], self.app_config.prefix, self.app_config.views)
                    end_datetime = trailcamutils.datetimeFromImageFilename(all_files[idx], self.app_config.prefix, self.app_config.views)
                    if count > 1:
                        activity = "> 1"
                    else:
                        activity = "1"
                    annotations.append((activity, 'AI_count', 'AI_count', start_datetime, end_datetime, 'AI'))
                   
                # write out the annotation file
                _, site_ID, _, date, _ = trailcamutils.splitImageFilename(detection_files[0][0], self.app_config.prefix, self.app_config.views)
                self.writeAnnotationFile(annotations, trailcamutils.createAnnotationFilename(site_ID, date, self.app_config.prefix))


    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def processDetectionLog(self):
        """
        Main driver for the CreateAnnotations class.  Processes the detection log, creating
        annotation files as needed.
        """
        dict = self.readDetectionLogFile()
        self.createAnnotationFiles(dict)


    def readDetectionLogFile(self):
        """
        Reads the contents of the detection log file.
        Returns:
            A dictionary mapping cameras to dictionaries mapping dates to lists of (filename, object count).
            The lists are sorted by filename, in ascending order.
        """
        # read the log file and segregate contents by camera and date
        master_dict = {}
        with open(self.app_config.detection_log_file, "r") as f:
            for line in f:
                line = line.strip()
                if len(line) > 0:
                    parts = line.split(',')
                    filename = parts[0]
                    count = int(parts[1].strip())
                    camera, _, _, date, _ = trailcamutils.splitImageFilename(filename, self.app_config.prefix, self.app_config.views)
                    # get the dictionary item for the camera
                    if camera in master_dict:
                        camera_dict = master_dict[camera]
                    else:
                        camera_dict = {}
                        master_dict[camera] = camera_dict
                    # get the dictionary item for the date
                    if date in camera_dict:
                        camera_dict[date].append((filename, count))
                    else:
                        camera_dict[date] = [(filename, count)]

        # sort the filenames
        for camera, dates in master_dict.items():
            for date, lyst in dates.items():
                lyst.sort()
        return master_dict


    def readBoxes(self, boxFolder):
        """
        Reads the box files created by the object detector.
        Returns:
            A dictionary mapping cameras to dictionaries mapping dates to lists of (filename, object count).
            The lists are sorted by filename, in ascending order.
        """        
        boxFiles = trailcamutils.getFilePathsInSubfolders(boxFolder, ".boxes")
        master_dict = {}
        for file in boxFiles:
            # count the number of boxes in file
            count = 0
            with open(file, "r") as f:
                for aLine in f:
                    if len(aLine.strip()) > 0:
                        count += 1

            if count > 0:
                filename = os.path.splitext(os.path.basename(file))[0] + ".JPG"
                camera, _, _, date, _ = trailcamutils.splitImageFilename(filename, self.app_config.prefix, self.app_config.views)
                # get the dictionary item for the camera
                if camera in master_dict:
                    camera_dict = master_dict[camera]
                else:
                    camera_dict = {}
                    master_dict[camera] = camera_dict
                # get the dictionary item for the date
                if date in camera_dict:
                    camera_dict[date].append((filename, count))
                else:
                    camera_dict[date] = [(filename, count)]

        # sort the filenames
        for camera, dates in master_dict.items():
            for date, lyst in dates.items():
                lyst.sort()
        return master_dict


    def writeAnnotationFile(self, annotations, filename):
        """
        Writes an annotation file. Overwrites any existing annotations.
        """
        os.makedirs(self.app_config.annotation_folder, exist_ok=True)
        filename = os.path.join(self.app_config.annotation_folder, filename)
        specifier = "a" if self.app_config.append_annotations else "w"

        with open(filename, specifier) as f:
            for a in annotations:
                f.write(f"{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}\n")



def parseCommandLine():
    """
    Parse the command line arguments.
    Returns a dictionary containing the arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")
    args = vars(ap.parse_args())
    return args

if __name__ == "__main__":
    args = parseCommandLine()    
    app = AnnotationCreator(args["config"])

    app.processDetectionLog()

