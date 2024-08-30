"""
Utility for extracting video clips from trail camera time-lapse image sequences
Mike Hilton, Eckerd College

This program creates mp4 video clips of annotated segments of image sequences.
"""
# standard Python modules
import argparse
import configparser
from datetime import datetime
import os
import shutil

# modules that are part of this package
from utils.annotation import AnnotationList
from utils.timelapse.image_sequence import StillSequence
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
        assert os.path.exists(configFilename), f"Configuration file not found: {configFilename}"
        self.app_config.read(configFilename)
        
        # general settings shared by multiple trail_camera_tools programs
        settings = self.app_config["General_Settings"] 
        self.annotation_folder = settings["default_annotation_folder"]        # folder where annotation files live
        self.default_image_folder = settings["default_image_folder"]          # folder where image sequences live
        self.prefix = settings["prefix"]

        # settings specific to this program
        settings = self.app_config["Extract_Clips"]   
        self.image_extension = settings["image_extension"]
        self.output_path = settings["default_output_path"]
        self.segments_to_extract = [s.strip() for s in settings["segments_to_extract"].split(",")]
        self.views_to_process = settings["views_to_process"].split(",")

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


class ExtractClips():
    def __init__(self, configFile=None):
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)


    def createIndexFile(self, indexPath, timeline, startFrame, endFrame):
        """
        Creates a frame index file for the section of the timeline between 
        startFrame and endFrame (inclusive).
        Inputs:
            indexPath   path for index file
            timeline    ImageSequence object
            startFrame  int; index of starting frame
            endFrame    int; index of ending frame
        """
        with open(indexPath, "w") as outFile:
            for i in range(startFrame, endFrame+1):
                outFile.write(trailcamutils.convertPythonDatetimeToTrailcamDatetime(timeline.frameTime(i)) + "\n")


    def extractClip(self, imgSequence, destinationPath, site, day, view, behavior, start, end):
        """
        Extract a single video clip and write it to the output folder.
        Inputs:
            imgSequence         ImageSequence; source image sequence
            destinationPath     string; path to folder where clip should go
            site                string; site identifier
            day                 date; day of video clip
            view                string; camera view
            behavior            string; annotation behavior tag
            start               datetime; starting time of clip
            end                 datetime; ending time of clip
        """
        day = day.replace("-", "")
        startString = start.strftime("%H%M%S")
        os.makedirs(destinationPath, exist_ok=True)
        
        if end is not None:
            # this is a duration event, so a video will get created
            endString = end.strftime("%H%M%S")
            # create the file paths needed
            destVideoFilename = f"{self.app_config.prefix}{site}-{day}-{startString}-{endString}-{view}-{behavior}.mp4"
            destVideoPath = os.path.join(destinationPath, destVideoFilename)
            destIndexPath = destVideoPath[:-3] + "index"
            print(destVideoFilename)

        # find the frame indices for clip boundary
        startFrame = imgSequence.frameAtTime(start)
        if end is not None:
            endFrame = imgSequence.frameAtTime(end)
            # create the index file for the clip
            self.createIndexFile(destIndexPath, imgSequence, startFrame, endFrame)
            # write out the video clip
            imgSequence.saveAsVideo(destVideoPath, startFrame, endFrame)   
        else:
            # copy the image file
            imageName, imageExt = os.path.splitext(os.path.split(imgSequence.getImageFilename(startFrame))[1])
            destImagePath = os.path.join(destinationPath, f"{self.app_config.prefix}{site}-{day}-{startString}-{view}-{behavior}{imageExt}")
            shutil.copyfile(imgSequence.getImageFilename(startFrame), destImagePath)


    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"   


    def main(self):
        """
        Extract the clips specified in the inputFile
        """
        # process every site in the raw images folder
        dirs = os.listdir(self.app_config.default_image_folder)
        dirs.sort()
        for d in dirs:
            siteId = d[len(self.app_config.prefix):]
            siteFolder = os.path.join(self.app_config.default_image_folder, d)
            if os.path.isdir(siteFolder):
                self.processSite(
                    self.app_config.default_image_folder, 
                    self.app_config.output_path, 
                    self.app_config.annotation_folder,
                    siteId, 
                    self.app_config.image_extension
                    )
        return


    def processSite(self, sourceFolder, destinationFolder, annotationFolder, siteID, imageExtension):
            """
            Create videos for each day in the specified site, if it has an annotation file.
            Inputs:
                sourceFolder        string; folder containing the images to be processed
                destinationFolder   string; path for composited video output files
                annotationFolder    string; path to where annotation files live
                imageExtension      string; the file extension of still images in sourceFolder
            """
            sitePath = os.path.join(sourceFolder, app.app_config.prefix + siteID)
            dirs = os.listdir(sitePath)
            dirs.sort()
            limit = len(dirs)

            for i in range(0, limit):
                day = dirs[i]
                dayFolder = os.path.join(sitePath, day)
                if os.path.isdir(dayFolder):
                    annotFile = os.path.join(
                        self.app_config.annotation_folder, 
                        trailcamutils.createAnnotationFilename(siteID, day, self.app_config.prefix)
                        )
                    if os.path.exists(annotFile):
                        for view in app.app_config.views_to_process:
                            imagesFolder = os.path.join(dayFolder, view)
                            if os.path.exists(imagesFolder):
                                self.processDay(imagesFolder, destinationFolder, annotFile, siteID, day, view, imageExtension)


    def processDay(self, sourceFolder, destinationFolder, annotationFile, siteID, day, view, imageExtension):
        """
        Create videos for the specified site and date.
        Inputs:
            sourceFolder        string; folder containing the images to be processed
            destinationFolder   string; path for video output files
            annotationFile      string; path to annotation file for this day
            siteID              string; site ID
            day                 string; date
            view                string; camera view
            imageExtension      string; the file extension of still images in sourceFolder
        """
        if os.path.exists(sourceFolder):                    
            # create the source image sequence
            imgSequence = StillSequence(sourceFolder, False)

            # read the annotations and filter out segments to be processed
            clips = self.readClipSpecifications(annotationFile)

            if len(clips) > 0:
                videoPath = os.path.join(destinationFolder, 
                                            trailcamutils.videoPathFromParts(
                                                app.app_config.prefix + siteID, day))
                os.makedirs(videoPath, exist_ok=True)  
                # generate video or image for each clip
                for behavior, segments in clips.items():
                    for segment in segments:
                        self.extractClip(imgSequence, videoPath, siteID, day, view, behavior, segment[0], segment[1])


    def readClipSpecifications(self, annotationFile):
        """
        Reads an annotation file and filters out the segments that match the config file's
        segments_to_extract
        Inputs:
            annotationFile       string; path to annotation file
        Returns:
            A dictionary mapping segment name to list of the form (start time, end time)
        """
        wildcard = "*" in self.app_config.segments_to_extract 
        # filter the annotations
        lyst = AnnotationList()
        lyst.readFromFile(annotationFile, None)
        clips = {}
        for annot in lyst:
            behavior = annot.getBehavior()
            kind = annot.getKind()
            if ((behavior in self.app_config.segments_to_extract) or
                ((kind != "AI_count") and wildcard)):
                if behavior not in clips:
                    clips[behavior] = []
                clips[behavior].append((annot.getStartTime(), annot.getEndTime()))

        return clips




def parseCommandLine():
    """
    Parse the command line arguments.
    Returns a dictionary containing the arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")     
    ap.add_argument("-o", "--output", required=False, default=None, help="path for output directory")    
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    args = parseCommandLine()  
    app = ExtractClips(args["config"])

    # overwrite default config values
    if args["output"] is not None: 
        app.app_config.output_path = args["output"]

    app.main()    

