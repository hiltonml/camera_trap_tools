"""
Camera Trap Video Compositing Utility
Mike Hilton, Eckerd College
2021/07/06

This script creates a video for each view present in the source images, for
each day found.  A time-aligned side-by-side video is also created that combines
two views, if both views are available for the same day.  The open-source
program ffmpeg is used to create the videos; it must be installed on your
computer.

The source images are expected to be organized in the folder structure created
by the autocopy.py program.  The folder structure is scanned and the videos are
created for each day, except in the following situations:
- If a video already exists, it is not recreated unless the --force option is used
- Videos are not created for the final camera days.  The reason for this is the 
    assumption that more images taken on the "current" final day will be downloaded
    the next time the camera SD card is swapped.  We want to include those new images
    in the day's video.

Command line arguments for this program are listed below.  All arguments are optional; default values 
can be provided in a configuration file.
    -c, --config    <path>      Configuration file.  If not provided, defaults to "compose_video.config" located
                                in the same directory as this program.
    -s, --source    <path>      Image source directory.  This path must be either a folder containing sites or
                                    a day folder.
    -d, --dest      <path>      Video destination directory.  
    -f, --force                 Force creation of video, even if one of the same name exists
"""

# standard Python modules
import argparse
import configparser
import datetime
import functools
import operator
import os

# 3rd party modules
import numpy as np
import cv2
from PIL import Image

# modules that are part of this package
import utils.trailcamutils as trailcamutils


class AppConfig:
    """ 
    Configuration settings for this application.
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
        self.box_folder = settings["detection_box_folder"]                  # folder where single image file object detection box files are located        
        self.images_folder = settings["default_image_folder"]               # root of raw image folder 
        self.error_log_file = settings.get("error_log_file", "error.log")   # path to error log
        self.video_folder = settings["default_video_folder"]                # destination folder for videos
        self.prefix = settings.get("prefix", "")                            # filename prefix string        
        
        # settings specific to this program
        settings = self.app_config["Compose_Video"]  
        self.compose_scale = float(settings.get("compose_scale", 0.25))     # image scaling factor for side-by-side composite video
        self.composite_views = settings.get("composite_views", "")          # two view names to be composited
        self.create_composite = bool(int(settings.get("create_composite", 1)))  # should a composite be created?
        self.force = bool(int(settings.get("force", 0)))                    # force the creation of video files, even if one of the same name already exists
        self.image_extension = settings.get("image_extension", "JPG")       # file extension of source images
        self.max_interval = float(settings.get("max_interval", 3))          # maximum time interval (in seconds) allowed when time-aligning composite image frames 
        self.recompress = bool(int(settings.get("recompress_composite", 1))) # recompress the videos using FFMPEG for maximum compression
 
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

        # split the composite view names
        self.composite_views = [x.strip() for x in self.composite_views.split(",")]
        # make sure these views are legal
        if len(self.composite_views) != 0:
            if len(self.composite_views) != 2:
                raise Exception("The composite_views configuration value must contain two comma-separated view names")
            view_names = map(lambda x: x[0], self.views.values())
            if not functools.reduce(
                operator.and_, 
                map(lambda x: x in view_names, self.composite_views)
                ):
                raise Exception("One or more composite_views configuration values is not a legal view name")

              

class ComposeVideo:
    COMPRESSOR = "mp4v"

    def __init__(self, configFile=None):
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)


    def concatImages(self, image1, image2, scale):
        """
        Returns a cv2 (numpy) image that is the horizontal concatenation of scaled versions of image1 and image2.
        """
        # scale the image sizes
        w1 = int(image1.width * scale)
        h1 = int(image1.height * scale)
        w2 = int(image2.width * scale)
        # use PIL to concatenate the images
        videoWidth = w1 + w2 + 10
        cat = Image.new("RGB", (videoWidth, int(image1.height * scale)))
        cat.paste(image1.resize((w1, h1)))
        cat.paste(image2.resize((w2, h1)), (w1 + 10, 0))
        # convert the PIL image into a cv2 image
        opencvImage = cv2.cvtColor(np.array(cat), cv2.COLOR_RGB2BGR)
        return opencvImage


    def createVideo(self, day, sourceFolder, destinationFolder, imageExtension, siteID):
        """
        Creates a video sequence from time-lapses images.
        Inputs:
            day                     string; date to process
            sourceFolder            string; folder where images live
            destinationFolder       string; folder where video is written to
            imageExtension          string; extension of image files to include in video
            day                     string; the date (folder name) of the source images
            siteID                  string; the ID of site (parent folder name) for the source images 
        """   
        # create folder paths
        viewAbbrevs = { x[0]:x[1] for (key, x) in self.app_config.views.items() }
        view1_ImageDir = os.path.join(sourceFolder, trailcamutils.imagePathFromParts(siteID, viewAbbrevs[self.app_config.composite_views[0]], day, self.app_config.views))
        view2_ImageDir = os.path.join(sourceFolder, trailcamutils.imagePathFromParts(siteID, viewAbbrevs[self.app_config.composite_views[1]], day, self.app_config.views))
        dateFolder = os.path.split(view1_ImageDir)[0]

        # if both view1 and view2 images exist, make a composite video
        if self.app_config.create_composite and os.path.exists(view1_ImageDir) and os.path.exists(view2_ImageDir):
            outputFilename = os.path.join(destinationFolder, trailcamutils.videoFilenameFromParts(siteID, day, "composite", "mp4"))
            indexFilename = os.path.join(destinationFolder, trailcamutils.videoFilenameFromParts(siteID, day, "composite", "index"))

            if not self.app_config.recompress:
                tempFile = outputFilename
            else:
                # The cv2 video writer does not do a very good job compressing the video, so it is first
                # created to a temporary file, which will later be compressed by ffmpeg
                tempFile = os.path.join(destinationFolder, "temporary.mp4")                 
            if self.app_config.force or (not os.path.exists(outputFilename)):
                print("Creating " + outputFilename)
                self.imagesPlusImagesCompose(
                    view1_ImageDir,
                    view2_ImageDir,
                    tempFile,
                    imageExtension,
                    indexFilename
                    )
                print()     
                # compress the video using ffmpeg
                if self.app_config.recompress and os.path.exists(tempFile):
                    os.system(f'ffmpeg -y -i "{tempFile}" -b:v 30M "{outputFilename}"')
                    os.remove(tempFile)

        # make a video for each view
        for key, val in self.app_config.views.items():
            viewName, viewAbbrev = val
            viewDir = os.path.join(dateFolder, viewName)
            if os.path.exists(viewDir):
                outputFilename = os.path.join(destinationFolder, trailcamutils.videoFilenameFromParts(siteID, day, viewName.lower(), "mp4"))
                indexFilename = os.path.join(destinationFolder, trailcamutils.videoFilenameFromParts(siteID, day, viewName.lower(), "index"))   
                boxFilename = os.path.join(destinationFolder, trailcamutils.videoFilenameFromParts(siteID, day, viewName.lower(), "vboxes"))
                imagesBoxFolder = os.path.join(self.app_config.box_folder, siteID, day, viewName)         
                if self.app_config.force or (not os.path.exists(outputFilename)):
                    print("Creating " + outputFilename)
                    self.singleViewVideo(
                        viewDir,
                        imagesBoxFolder,
                        imageExtension,
                        outputFilename,
                        indexFilename,
                        boxFilename
                        )
                    print()                



    def createVideoWriter(self, filename, fourccType, width, height):
        """
        Returns a video writer object
        """
        fourcc = cv2.VideoWriter_fourcc(*fourccType)
        writer = cv2.VideoWriter(filename, fourcc, 30, (width, height), True)
        return writer
    

    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def imagesPlusImagesCompose(self, view1_ImageDir, view2_ImageDir, videoOut, imageExtension, indexFilename):
        """
        Create a time-aligned video that concatenates still images from two views.
        The names of the images are expected to in prefix-YYMMDD-HHmmss format.
        Inputs:
            view1_ImageDir: folder containing the overhead still images
            view2_ImageDir: folder containing the frontal still images
            videoOut: path for concatenated video output
            imageExtension: the file extension of still images
            indexFilename: path for time index file
        """
        # get the time-sorted lists of image files to be aligned
        view2Files = self.readFileTimes(view2_ImageDir, imageExtension)
        view1Files = self.readFileTimes(view1_ImageDir, imageExtension)
        if len(view2Files) == 0:
            print("[ERROR] No image files found in " + view2_ImageDir)
            return
        elif len(view1Files) == 0:
            print("[ERROR] No image files found in " + view1_ImageDir)
            return       
        else:
            # load the first image in the view2 image list to find its dimensions
            img = Image.open(view2Files[0][1])
            IMAGE_SIZE = (img.width, img.height)
            # load the first image in the view1 image list to find its dimensions
            img = Image.open(view1Files[0][1])
            VIDEO_SIZE = (img.width, img.height)       

        # initialize the video output stream
        scaledImageWidth = int(((VIDEO_SIZE[1] / IMAGE_SIZE[1]) * IMAGE_SIZE[0]) * self.app_config.compose_scale)
        writer = self.createVideoWriter(videoOut, self.COMPRESSOR,
                                    int(VIDEO_SIZE[0] * self.app_config.compose_scale) + scaledImageWidth + 10, 
                                    int(VIDEO_SIZE[1] * self.app_config.compose_scale))  

        # create a black image to use on occassion
        blackImage = Image.new("RGB", IMAGE_SIZE)

        # create a time index file
        with open(indexFilename, "w") as indexFile:
            frameTime = None    # time value to use for this frame of video; top is preferred

            # loop over all the images
            view1Image = blackImage
            view2Image = blackImage
            frameCounter = 0    # counter for eye candy 
            while (len(view2Files) > 0) or (len(view1Files) > 0):
                if len(view2Files) == 0:
                    view2Image = blackImage
                    f = view1Files.pop(0)  
                    frameTime = trailcamutils.datetimeFromImageFilename(f[1], self.app_config.prefix, self.app_config.views)         
                    try:
                        view1Image = Image.open(f[1])
                    except Exception as e:
                        print(e)                
                        continue
                elif len(view1Files) == 0:
                    view1Image = blackImage
                    f = view2Files.pop(0)  
                    frameTime = trailcamutils.datetimeFromImageFilename(f[1], self.app_config.prefix, self.app_config.views)              
                    try:
                        view2Image = Image.open(f[1])
                    except Exception as e:
                        print(e)                
                        continue               
                elif view1Files[0][0] < view2Files[0][0]:
                    # time of topFile is earlier
                    f = view1Files.pop(0)  
                    frameTime = trailcamutils.datetimeFromImageFilename(f[1], self.app_config.prefix, self.app_config.views)             
                    try:
                        view1Image = Image.open(f[1])
                    except Exception as e:
                        print(e)
                        continue
                    # check if frontalFiles[0] is close enough to topImage for a match
                    if (abs((view2Files[0][0] - f[0]).total_seconds()) < self.app_config.max_interval):
                        f = view2Files.pop(0)
                        try:
                            view2Image = Image.open(f[1])
                        except Exception as e:
                            print(e)

                else:
                    # time of frontalFile is earlier
                    f = view2Files.pop(0)   
                    frameTime = trailcamutils.datetimeFromImageFilename(f[1], self.app_config.prefix, self.app_config.views)             
                    try:
                        view2Image = Image.open(f[1])
                    except Exception as e:
                        print(e)
                        continue
                    # check if topFiles[0] is close enough to frontalImage for a match
                    if (abs((view1Files[0][0] - f[0]).total_seconds()) < self.app_config.max_interval):
                        f = view1Files.pop(0)
                        try:
                            view1Image = Image.open(f[1])
                        except Exception as e:
                            print(e)
                try:
                    # place the images side-by-side
                    newFrame = self.concatImages(view1Image, view2Image, self.app_config.compose_scale)

                    # write the new frame to video output
                    writer.write(newFrame)

                    # append frameTime to index file
                    indexFile.write(f"{frameTime}\n")
                except:
                    pass

                # eye candy / progress indicator
                frameCounter += 1
                if (frameCounter % 36) == 0:
                    print(".", end="", flush=True)
                if (frameCounter % 720) == 0:
                    print()                    

        # release the video file pointer
        writer.release()


    def main(self, sourceFolder, destinationFolder, imageExtension="jpg", force=False, composite=True):
        """
        Main driver for video compositing program.
        Inputs:
            sourceFolder        string; folder containing the images to be processed
            destinationFolder   string; path for composited video output files
            imageExtension      string; the file extension of still images in sourceFolder
            force               boolean; indicates if video should always be created, even if one of the same name already exists
            composite           boolean; indicates if the composite (side-by-side) video should be created
        """   
        self.app_config.force = force
        self.app_config.create_composite = composite 
        if sourceFolder == self.app_config.images_folder:
            # process every site in the default folder
            dirs = os.listdir(sourceFolder)
            dirs.sort()
            for d in dirs:
                siteFolder = os.path.join(sourceFolder, d)
                if os.path.isdir(siteFolder):     
                    self.processSite(sourceFolder, destinationFolder, d, imageExtension)  
        else:
            # this must be a date folder
            p, date = os.path.split(os.path.abspath(sourceFolder))
            p, siteID = os.path.split(p)
            self.processDay(p, destinationFolder, siteID, date, imageExtension)
     

    def processSite(self, sourceFolder, destinationFolder, siteID, imageExtension):
        """
        Create videos for each day (but the last) in the specified site.  The last day is
        not processed on the theory that it may be a partial day, caught between SD card changes.
        If the "force" configuration item is True, the last day will be processed.
        Inputs:
            sourceFolder        string; folder containing the images to be processed
            destinationFolder   string; path for composited video output files
            imageExtension      string; the file extension of still images in sourceFolder
        """
        sitePath = os.path.join(sourceFolder, siteID)  
        dirs = os.listdir(sitePath)
        dirs.sort()

        if self.app_config.force:
            limit = len(dirs) 
        else:
            limit = len(dirs) - 1

        for i in range(0, limit):
            day = dirs[i]
            dayFolder = os.path.join(sitePath, day)
            if os.path.isdir(dayFolder):
                self.processDay(sourceFolder, destinationFolder, siteID, day, imageExtension)


    def processDay(self, sourceFolder, destinationFolder, siteID, day, imageExtension):
        """
        Create videos for the specified site and date.
        """
        videoPath = os.path.join(destinationFolder, trailcamutils.videoPathFromParts(siteID, day))
        os.makedirs(videoPath, exist_ok=True)
        self.createVideo(day, sourceFolder, videoPath, imageExtension, siteID)    


    def readFileTimes(self, sourceDir, fileType):
        """
        Returns a list of (filename, datetime) pairs for all files of the specified
        type in sourceDir, sorted by datetime in ascending order
        """
        fileType = "." + fileType.lower()
        files = trailcamutils.getFilenamesInFolder(sourceDir, fileType)
        # extract datetimes from filenames
        answer = []
        for f in files:
            _, _, _, date, time = trailcamutils.splitImageFilename(f, self.app_config.prefix, self.app_config.views)
            try:
                dt = datetime.datetime.strptime(date + ' ' + time, '%Y-%m-%d %H:%M:%S')
                answer.append((dt, os.path.join(sourceDir, f)))
            except Exception:
                print("Bad datetime: ", f)
        return answer


    def singleViewVideo(self, imageDir, boxDir, imageExtension, videoFilename, indexFilename, boxFilename):
        """
        Create a video from a directory of still images.
        The names of the images are exepected to in prefix-YYMMDD-HHmmss format.
        Inputs:
            imageDir:           string; folder containing the still images
            boxDir:             string; folder containing source object detection box files
            imageExtension:     string; file extension for images
            videoFilename:      string; path for video output
            indexFilename:      string; path for time index file
            boxFilename:        string; path for the video object detection boxes file
        """
        # get the time-sorted list of image files
        imageFiles = self.readFileTimes(imageDir, imageExtension)
        if (len(imageFiles) == 0):
            print("[ERROR] No image files found in " + imageDir)
            return
        else:
            print("Processing " + imageDir)           

        # get the time-sorted list of box files
        if (boxDir is not None) and os.path.exists(boxDir):
            boxFiles = trailcamutils.getFilePathsInSubfolders(boxDir, ".boxes")
        else:
            boxFiles = []

        # create time index file and video box file
        frame = 0
        boxIdx = 0
        with open(indexFilename, "w") as indexFile:
            if (boxFilename is not None) and (len(boxFiles) > 0):
                os.makedirs(os.path.dirname(boxFilename), exist_ok=True)
                boxFile = open(boxFilename, "w")
            else:
                boxFile = None

            for f in imageFiles:
                # index file data
                frameTime = trailcamutils.datetimeFromImageFilename(f[1], self.app_config.prefix, self.app_config.views)
                indexFile.write(f"{frameTime}\n")

                # box file data
                if (boxFile is not None) and (len(boxFiles) > boxIdx) and (frameTime in boxFiles[boxIdx]):
                    with open(boxFiles[boxIdx], "r") as inFile:
                        for aLine in inFile:
                            if len(aLine.strip()) > 0:
                                boxFile.write(f"{frame},{aLine}")
                    boxIdx += 1

                frame += 1
            
            if boxFile is not None:
                boxFile.close()

        # get the actual file extension 
        _, ext = os.path.splitext(os.path.basename(imageFiles[0][1]))

        # compress the files using FFMPEG       
        pattern = os.path.join(imageDir, f"*{ext}")
        os.system(f'ffmpeg -y -pattern_type glob -framerate 30 -i "{pattern}" -b:v 30M "{videoFilename}"')     


def parseCommandLine():
    """
    Returns a dictionary containing parse command line arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")
    ap.add_argument("-d", "--dest", required=False, default=None, help="path to video destination directory")
    ap.add_argument("-f", "--force", required=False, action='store_true', help="force creation of video, even if one of the same name exists")
    ap.add_argument("-s", "--source", required=False, default=None, help="path to image source directory")
    args = vars(ap.parse_args())
    return args


if __name__ == "__main__":
    args = parseCommandLine()
    app = ComposeVideo(args["config"])

    # assign any command line arguments to app configuration variables
    if args["dest"] is not None:
        app.app_config.video_folder = args["dest"]
    if args["force"]:
        app.app_config.force = True 
    if args["source"] is not None:
        app.app_config.images_folder = args["source"]

    app.main(
        app.app_config.images_folder, 
        app.app_config.video_folder,
        app.app_config.image_extension, 
        app.app_config.force,
        app.app_config.create_composite
        )