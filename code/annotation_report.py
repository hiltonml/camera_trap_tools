"""
Camera Trap Video Annotation Export Utility
Mike Hilton, Eckerd College
2021/07/06

This program combines the contents of all video annotation files and dumps
them to a single CSV file suitable for analyzing with the statistical software
of your choice.

Command line arguments for this program are listed below.  All arguments are optional; default values 
can be provided in a configuration file.
    -c, --config    <path>      Configuration file.  If not provided, defaults to "annotation_report.config" located
                                in the same directory as this program.
    -o, --out       <path>      Path to output report file.  If not provided, the report is printed to stdout.
"""

# standard Python modules
import argparse
import configparser
import os

# modules that are part of this package
from utils.annotation import AnnotationList
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
        self.annotation_folder = settings["default_annotation_folder"]        # folder where annotation files live


class AnnotationReport:
    def __init__(self, configFile=None):
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)


    def exportAnnotations(self, annotationDict, filename):
        """
        Writes out the annotation records to a CSV file with the specified filename.
        Inputs:
            annotationDict      Dictionary mapping site IDs to tuples of the form 
                                    (date, AnnotationList objects, frame count) 
            filename            pathname of report file to generate, or None if 
                                    output goes to stdout
        """
        if filename is None:
            print("site,file,activity,kind,individual,startTime,endTime,user")
            for site, data in annotationDict.items():
                for date, annots in data:
                    for annot in annots:
                        print(f"{site},{date},{annot.behavior},{annot.kind},{annot.individual},{annot.startTime},{annot.endTime},{annot.user}")
        else:
            with open(filename, "w") as outFile:
                outFile.write("site,file,activity,kind,individual,startTime,endTime,user\n")
                for site, data in annotationDict.items():
                    for date, annots in data:
                        for annot in annots:
                            outFile.write(f"{site},{date},{annot.behavior},{annot.kind},{annot.individual},{annot.startTime},{annot.endTime},{annot.user}\n")


    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def main(self, filename):
        """
        Generates report.
        Input:
            filename        string; path to report file to generate
        """
        annotationDict = self.readAnnotationFiles()
        self.exportAnnotations(annotationDict, filename)
        

    def readAnnotationFile(self, filename):
        """
        Reads in an annotation file.
        Inputs:
            filename        string; path to annotation file to read       
        Returns:
            An AnnotationList object containing the annotations in file.
        """
        lyst = AnnotationList()
        lyst.readFromFile(filename, None)
        return lyst


    def readAnnotationFiles(self):
        """
        Reads all the annotation files in the annotation folder.
        Returns:
            A dictionary mapping site IDs to lists of tuples of the form
                (date, AnnotationList objects)
        """    
        annotations = {}

        files = trailcamutils.getFilenamesInFolder(self.app_config.annotation_folder, '.annotations')    
        for filename in files:
            site, date = trailcamutils.splitAnnotationFilename(filename)
            # read the annotation file
            annots = self.readAnnotationFile(os.path.join(self.app_config.annotation_folder, filename))
            # add annotations to dictionary
            if site in annotations:
                annotations[site].append((date, annots))
            else:
                annotations[site] = [(date, annots)]

        return annotations  

        
def parseCommandLine():
    """
    Parse the command line arguments.
    Returns a dictionary containing the arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")
    ap.add_argument("-o", "--output", required=False, default=None, help="path for output report file")    
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    args = parseCommandLine()    
    app = AnnotationReport(args["config"])
    app.main(args["output"])    