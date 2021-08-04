"""
Classes providing random access to frames in a video sequence
Mike Hilton, Eckerd College

This module contains three classes that support random access
to indexable frames in video/image sequences:
- ImageSequence is the base abstract class 
- VideoSequence works on video files
- StillSequence works with folders containing a sequence of still images

OpenCV is used for reading image and video files.
"""

import cv2
from datetime import datetime
import os
from PySide2 import QtGui



class ImageSequence:
    def __init__(self, convertToGrayscale):   
        self._convertToGrayscale = convertToGrayscale    # flags if images should be converted to grayscale when read 
        self._duration = None               # duration of image sequence   
        self._frameCount = 0                # number of frames in the total sequence
        self._frameRate = 45                # number of frames per second, as determined from video file
        self._frameTimes = []               # datetime for each frame in the sequence           

    # getters and setters
    def getConvertToGrayscale(self):
        return self._convertToGrayscale

    def getDuration(self):
        return self._duration

    def _setDuration(self, duration):
        self._duration = duration 

    def getFilename(self):
        """ 
        This method is intended to be overridden by child classes.
        """
        pass

    def getFrameCount(self):
        return self._frameCount

    def _setFrameCount(self, fc):
        self._frameCount = fc

    def getFrameRate(self):
        if self._frameRate is not None:
            return self._frameRate
        else:
            return 30.0

    def _setFrameRate(self, rate):
        self._frameRate = rate     

    def getFrameTimes(self):
        return self._frameTimes
        
    # instance methods
    def _createVideoWriter(self, filename, fourccType, width, height):
        """Returns a video writer object"""
        fourcc = cv2.VideoWriter_fourcc(*fourccType)
        writer = cv2.VideoWriter(filename, fourcc, 30, (width, height), True)
        return writer

    def frame(self, i):
        """Returns frame[i] of the video"""
        return self.readFrame(i)

    def frameAtTime(self, datetimeObj):
        """Returns the index of the first frame whose time is equal to or greater than the specified time"""
        i = 0
        for t in self._frameTimes:            
            if t >= datetimeObj:
                return i
            i += 1
        return i-1

    def frameTime(self, i):
        """Returns datetime object of frame[i] of the video"""
        if i >= self.getFrameCount():
            raise Exception(f"Request frameTime {i} exceeds the length of this image sequence ({self.getFrameCount()})")
        else:          
            return self._frameTimes[i]      

    def numberOfFrames(self):
        return self.getFrameCount()

    def readFrame(self, i):
        """Abstract method to read the i'th frame from the sequence source"""
        pass

    def readIndexFile(self, indexFilename):
        """
        Reads in a frame time index file.
        """
        answer = []
        if os.path.exists(indexFilename):
            with open(indexFilename, "r") as indexFile:
                for line in indexFile:
                    answer.append(datetime.strptime(line.strip(), '%Y%m%d-%H%M%S'))   
        self._frameTimes = answer 

    def saveAsVideo(self, filename, startFrame, stopFrame):
        """Saves the image sequence as a video file"""
        height, width = self.frame(0).shape[:2]
        writer = self._createVideoWriter(filename, "mp4v", width, height)        
        for i in range(startFrame, stopFrame):
            self.readFrame(i)
            writer.write(self.frame(i))
        writer.release()




class VideoSequence(ImageSequence):
    def __init__(self, filename, convertToGrayscale):
        super().__init__(convertToGrayscale)
        # initialize the instance variables
        self._filename = filename           # path of video file loaded in sequence                
        self._videoReader = None            # OpenCV video reader
        # open the video sequence
        vr = cv2.VideoCapture(filename)
        if vr.isOpened():
            self._setVideoReader(vr)
            self._setFrameCount(int(vr.get(7)))
            # self._setFrameRate(vr.get(5))
            self._setDuration(self.getFrameCount() * self.getFrameRate())

            # read in the frame time index file, if one exists
            indexFilename = os.path.splitext(filename)[0] + ".index"
            if os.path.exists(indexFilename):
                with open(indexFilename, "r") as indexFile:
                    for line in indexFile:
                        self._frameTimes.append(datetime.strptime(line.strip(), '%Y%m%d-%H%M%S'))

        else:
            raise Exception("Unable to open video file")        
         
    # getters and setters
    def getFilename(self):
        return self._filename

    def getVideoReader(self):
        return self._videoReader

    def _setVideoReader(self, r):
        self._videoReader = r

    # instance methods            
    def isVideo(self):
        return True

    def readFrame(self, i):
        """Ensures that frame[i] has been read from the video file and is
        stored in the frame list."""
        if i >= self.getFrameCount():
            raise Exception(f"Request frame {i} exceeds the length of this video ({self.getFrameCount()})")
        else:
            # the frame needs to be read from the video file
            self.getVideoReader().set(1, i)
            result, f = self.getVideoReader().read()
            if result:
                if self.getConvertToGrayscale():
                    f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                return f
            else:
                raise Exception(f"Unable to read frame {i} from video file")


class StillSequence(ImageSequence):
    def __init__(self, path, convertToGrayscale):
        super().__init__(convertToGrayscale)
        # initialize instance variables
        self._folder = path         # path to the folder containing the sequence of still images  
        self._fileNames = []        # alphabetic list of image file names that make up this image sequence
        # open the image sequence
        self._gatherImageNames(path)
        self._setFrameCount(len(self._fileNames))
        self._setDuration(self.getFrameCount() * self.getFrameRate())
        # get frame times for each image in sequence
        for f in self._fileNames:
            name, _ = os.path.splitext(os.path.basename(f))
            idx = name.find("-")
            dt = name[idx+1:] 
            self._frameTimes.append(datetime.strptime(dt, '%Y%m%d-%H%M%S'))          

    # instance methods
    def frame(self, i):
        """Returns frame i of the image sequence"""
        if i >= self._frameCount:
            raise Exception(f"Request frame {i} exceeds the length of this image sequence ({self.getFrameCount()})")
        else:
            return self.readFrame(i)

    def _gatherImageNames(self, folder):
        """Adds the names of the image files in folder to self._fileNames"""
        fileTypes = [".jpg", ".jpeg", ".png", ".bmp", ".JPG", ".JPEG", ".PNG", ".BMP"]
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_file():
                    # only keep files with allowed extensions
                    if os.path.splitext(entry.path)[1] in fileTypes:
                        self._fileNames.append(entry.path)
        self._fileNames.sort()

    def getImageFilename(self, i):
        """
        Returns the file name of the Ith image in the sequence.
        """
        if i >= self.getFrameCount():
            raise Exception(f"Request frame {i} exceeds the length of this image sequence ({self.getFrameCount()})")
        else:            
            return self._fileNames[i]

    def getFilename(self):
        """
        Returns the folder name for the image sequence
        """
        return self._folder
        
    def isVideo(self):
        return False

    def readFrame(self, i):
        """Ensures that image i has been read and is stored in the frame cache."""
        if i >= self.getFrameCount():
            raise Exception(f"Request frame {i} exceeds the length of this image sequence ({self.getFrameCount()})")
        else:            
            filename = self._fileNames[i]
            if self.getConvertToGrayscale():
                img = cv2.imread(filename, cv2.COLOR_BGR2GRAY)
            else:
                img = cv2.imread(filename)
                #img = QtGui.QImage(filename)
            return img

