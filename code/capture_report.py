"""
Generate a Report on the Status of Images Captured Each Camera Day
Mike Hilton, Eckerd College
2021/07/06

This program generates a CSV file detailing the number of images captured by
each camera on each day, whether those images have been compressed into videos,
and if an annotation file exists for that camera day.  The companion R script 
capture_report.R can be used to create a graphic from the CSV file.

Command line arguments for this program are listed below.  All arguments are optional; default values 
can be provided in a configuration file.
    -c, --config    <path>      Configuration file.  If not provided, defaults to "capture_report.config" located
                                in the same directory as this program.
    -m, --month     <YYYY-MM>   Month for which to create a report, in YYYY-MM format.  If not provided,
                                the report is created for the entire period of time data has been recorded.
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
        self.image_folder = settings["default_image_folder"]                # path to folder where images files are
        self.prefix = settings.get("prefix", "")                            # filename prefix string          
        self.video_folder = settings["default_video_folder"]                # destination folder for videos

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


class CaptureReport:
    def __init__(self, configFile=None):
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)


    def countFrames(self, videoFile):
        """
        Returns the number of frames in the specified video file.
        """
        frames = 0
        # create the name of the frame index file
        indexFile = os.path.splitext(videoFile)[0] + ".index"
        # read the contents of the index file
        if os.path.exists(indexFile):
            with open(indexFile, "r") as inFile:
                # get number of lines in the file
                frames = len(inFile.readlines())
        return frames


    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def main(self, month=None):
        """
        Main driver for creating the capture report.
        Input:
            month   string; Optional.  Month for which to create a report, in YYYY-MM format.
                        If not provided, the report is created for the entire period of time
                        data has been recorded.
        """
        videoDict, frameCntDict = self.tallyVideos(self.app_config.video_folder, month)    
        annotationDict = self.tallyAnnotations(self.app_config.annotation_folder)
        imageDict = self.tallyImages(self.app_config.image_folder)
        self.writeReport(annotationDict, imageDict, frameCntDict, videoDict, month)


    def tallyAnnotations(self, annotationFolder):
        """
        Returns a dictionary recording the annotated video dates for each camera.
        """
        files = trailcamutils.getFilenamesInFolder(annotationFolder, extension=".annotations")   
        cameraDict = {}
        for f in files:
            camera, date = trailcamutils.splitAnnotationFilename(f)
            if camera is not None:
                if camera in cameraDict:
                    cameraDict[camera].append(date)
                else:
                    cameraDict[camera] = [date]
        return cameraDict


    def tallyImages(self, rawImageFolder):
        """
        Returns a dictionary of dictionaries recording the number
        of images taken each day by each camera.
        """
        # tally the files taken each day
        cameraDict = {}     # dictionary of info about each camera   
        files = trailcamutils.getFilePathsInSubfolders(rawImageFolder)     
        for f in files:
            _, cameraID, view, date, _  = trailcamutils.splitImageFilename(f, self.app_config.prefix, self.app_config.views)            
            camera = self.app_config.prefix + cameraID + view

            # get the date dictionary associated with this camera
            if camera in cameraDict:
                dateDict = cameraDict[camera]
            else:
                dateDict = {}
                cameraDict[camera] = dateDict

            # increment the images taken on this date
            if date in dateDict:
                dateDict[date] += 1
            else:
                dateDict[date] = 1
        return cameraDict


    def tallyVideos(self, videoFolder, month):
        """
        Returns a dictionary recording the videos taken by each camera.
        """
        files = trailcamutils.getFilePathsInSubfolders(videoFolder, extension=".mp4")   
        cameraDict = {}
        frameCntDict = {}
        for f in files:
            siteID, viewAbbrev, date = trailcamutils.splitVideoFilename(f, self.app_config.prefix, self.app_config.views)
            if siteID is not None:
                # if this video does not belong to the month of interest, skip it
                if (month is not None) and (not date.startswith(month)):
                    continue

                camera = self.app_config.prefix + siteID + viewAbbrev

                # add video to cameraDict
                if camera in cameraDict:
                    cameraDict[camera].append(date)
                else:
                    cameraDict[camera] = [date]

                # get the frameCnt date dictionary associated with this camera
                if camera in frameCntDict:
                    dateDict = frameCntDict[camera]
                else:
                    dateDict = {}
                    frameCntDict[camera] = dateDict

                # add number of frames to frameCnt date dictionary
                dateDict[date] = self.countFrames(f)

        return cameraDict, frameCntDict


    def writeReport(self, annotationDict, imageDict, frameCntDict, videoDict, month):
        # write out the report
        if month is None:
            filename = "capture_report.csv"
        else:
            filename = f"capture_report_{month}.csv"

        with open(filename, "w") as reportFile:
            reportFile.write("Camera, Date, ImageCount, FrameCount, Video, Annotation\n")

            # sort camera names
            cameras = set(videoDict.keys())
            cameras.update(set(imageDict.keys()))
            cameras = list(cameras)
            cameras.sort()

            for camera in cameras:
                # sort the dates for this camera
                dates = set()
                if camera in videoDict:
                    dates.update(set(videoDict[camera]))
                if camera in imageDict:
                    dates.update(set(imageDict[camera].keys()))
                dates = list(dates)
                dates.sort()

                for date in dates:
                    if (month is None) or date.startswith(month):
                        # check if a video exists for this date
                        videoExists = False
                        if camera in videoDict:
                            if date in videoDict[camera]:
                                videoExists = True
                        # check if an annotation file exists for this date
                        annotExists = False
                        if camera[:-1] in annotationDict:
                            if date in annotationDict[camera[:-1]]:
                                annotExists = True
                        # get image count for this date
                        imageCnt = 0
                        if camera in imageDict:
                            if date in imageDict[camera]:
                                imageCnt = imageDict[camera][date]
                        # get frame count for this date
                        frameCnt = 0
                        if camera in frameCntDict:
                            if date in frameCntDict[camera]:
                                frameCnt = frameCntDict[camera][date]

                        reportFile.write(f"{camera}, {date}, {imageCnt}, {frameCnt}, {videoExists}, {annotExists}\n")



def parseCommandLine():
    """
    Parse the command line arguments.
    Returns a dictionary containing the arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")
    ap.add_argument("-m", "--month", required=False, default=None, help="month for which to generate a report, in YYYY-MM format")    
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    args = parseCommandLine()    
    app = CaptureReport(args["config"])
    app.main(args["month"])

