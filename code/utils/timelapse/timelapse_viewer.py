"""
Time Lapse Image Viewing Widget
Mike Hilton, Eckerd College

This module contains a Pyside2-, Qt5-based widget for viewing
video and still image sequences one frame at a time.
"""

# standard Python modules
import os

# 3rd party modules
import cv2
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets

# modules that are part of this package
from .image_sequence import VideoSequence, StillSequence
from .scaled_label import ScaledLabel


class TimeLapseViewer(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        # initialize the private instance variables
        self._myPath = os.path.dirname(os.path.realpath(__file__))
        self._convertToGrayscale = False    # flags if the video should be converted to greyscale when read in 
        self._currentFrame = None           # frame currently being displayed
        self._duration = None               # duration of the video, in seconds
        self._filename = None               # path of video file loaded in viewer
        self._frameChangeCallback = None    # client callback function that is fired whenever the current frame is changed
        self._frameRate = None              # time for displaying a single frame in the original video
        self._iconPause = QtGui.QIcon(os.path.join(self._myPath, "icons/icon-pause.png"))
        self._iconPlay = QtGui.QIcon(os.path.join(self._myPath, "icons/icon-play.png"))
        self._iconFullSizeImage = QtGui.QIcon(os.path.join(self._myPath, "icons/icon-zoom-fullsize.png"))      
        self._iconScaleImage = QtGui.QIcon(os.path.join(self._myPath, "icons/icon-zoom-fixed.png"))
        self._imageSequence = None          # currently loaded image sequence object        
        self._parent = parent               # parent widget containing this viewer
        self._playbackRate = 0.033          # video player speed, time spent per frame
        self._scaleImage = True             # flags if video size is scaled to window (True) or full size (False)
        self._timer = None                  # timer for playing video

        # Create a QTimer object that will call the app.run()
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.goForwardOneFrame)        

        # create the Qt widgets comprising the viewer
        self.layout = QtWidgets.QVBoxLayout(self)   
        self._createVideoImage()
        self._createVideoFrameControls()
        self._createMediaPlayerControls()

        self.setMediaControlsEnable(False)

    def _createVideoImage(self):
        # scrollable image display area  
        # I'm not taking advantage of the scrolling capability at this time...       
        self.scrollableArea = QtWidgets.QScrollArea(self)
        self.layout.addWidget(self.scrollableArea)          
        self.scrollableArea.setWidgetResizable(True)        
        self.image = ScaledLabel()
        self.image.setText("")
        self.image.setAlignment(QtCore.Qt.AlignLeft)    
        self.image.setScaledContents(True)       
        self.scrollableArea.setWidget(self.image)


    def _createVideoFrameControls(self):
        self.videoFrameControls = QtWidgets.QFrame(self)
        self.videoFrameControlsLayout = QtWidgets.QHBoxLayout(self.videoFrameControls)
        self.videoFrameControlsLayout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.videoFrameControls)
        self.frameSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.videoFrameControlsLayout.addWidget(self.frameSlider)         
        self.frameSlider.setMinimum(1)
        self.frameSlider.setMaximum(10)
        self.frameSlider.valueChanged.connect(self._sliderChanged)
        self.frameSlider.sliderPressed.connect(self._sliderPressed)
        self.frameSlider.sliderReleased.connect(self._sliderReleased)
        self.timeLabel = QtWidgets.QLabel()      
        self.videoFrameControlsLayout.addWidget(self.timeLabel)  


    def _createMediaPlayerControls(self):              
        """Create the widgets used to control playback"""
        self.mediaPlayerControlsContainer = QtWidgets.QFrame(self)
        self.layout.addWidget(self.mediaPlayerControlsContainer)
        self.mediaPlayerControlsContainerLayout = QtWidgets.QHBoxLayout(self.mediaPlayerControlsContainer)
        self.mediaPlayerControls = QtWidgets.QFrame(self)
        self.mediaPlayerControlsContainerLayout.addWidget(self.mediaPlayerControls)
        self.mediaPlayerControlsLayout = QtWidgets.QHBoxLayout(self.mediaPlayerControls)
        self.mediaPlayerControlsLayout.setContentsMargins(0,0,0,0)
        self.mediaPlayerControls.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)        
        # playback speed spinbox      
        self.frameSpeedLabel = QtWidgets.QLabel()
        self.frameSpeedLabel.setText("Playback Speed (FPS):")
        self.mediaPlayerControlsLayout.addWidget(self.frameSpeedLabel)
        self.playbackSpeed = QtWidgets.QSpinBox()
        self.playbackSpeed.setWrapping(False)
        self.playbackSpeed.setMinimum(1)
        self.playbackSpeed.setMaximum(1000)
        self.playbackSpeed.setValue(45)
        self.playbackSpeed.valueChanged.connect(self._playbackSpeedChanged)
        self.playbackSpeed.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.playbackSpeed.setStyleSheet("max-width: 5em; min-width: 2em;")
        self.mediaPlayerControlsLayout.addWidget(self.playbackSpeed)
        # video player buttons
        self.firstFrameBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-start.png"), self.goFirstFrame)
        self.backSeveralBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-fast-backward.png"),self.goBackTenFrames)
        self.backOneBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-backward-one.png"), self.goBackOneFrame) 
        self.playBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-play.png"), self.playFrames)
        self.playBtn.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space))
        self.forwardOneBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-forward-one.png"), self.goForwardOneFrame)
        self.forwardSeveralBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-fast-forward.png"), self.goForwardTenFrames)                                
        self.lastFrameBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-end.png"), self.goLastFrame)
        # goto frame button
        self.gotoFrameBtn = QtWidgets.QPushButton("Go To Frame")
        self.gotoFrameBtn.clicked.connect(self.gotoFrameDialog)
        self.gotoFrameBtn.setStyleSheet("max-width: 7em; min-width: 7em;")
        self.gotoFrameBtn.setEnabled(False)
        self.mediaPlayerControlsLayout.addWidget(self.gotoFrameBtn)
        # scale button
        self.scaleImageBtn = self._createMediaPlayerButton(os.path.join(self._myPath, "icons/icon-zoom-fullsize.png"), self.toggleScale)


    def _createIconButton(self, iconFile, action, background="white"):
        """Creates a QPushButton with the specified icon, click action, and background color"""
        btn = QtWidgets.QPushButton()
        btn.setIcon(QtGui.QIcon(iconFile))
        btn.clicked.connect(action)
        btn.setStyleSheet("background-color: " + background)
        return btn

    def _createMediaPlayerButton(self, iconFile, action):
        """Creates an icon button and adds it to the mediaPlayerControlsLayout"""
        btn = self._createIconButton(iconFile, action)
        self.mediaPlayerControlsLayout.addWidget(btn)
        return btn


    # getters and setters
    def getConvertToGrayscale(self):
        return self._convertToGrayscale

    def setConvertToGrayscale(self, boolean):
        self._convertToGrayscale = boolean

    def getCurrentFrame(self):
        return self._currentFrame

    def getDuration(self):
        return self._imageSequence.getDuration()

    def getFrameCount(self):
        return self._imageSequence.getFrameCount()

    def getFrameFilename(self, index):
        return self._imageSequence.getImageFilename(index)

    def getFilename(self):
        return self._filename

    def setFilename(self, f):
        self._filename = f

    def getFrameRate(self):
        return self._imageSequence.getFrameRate()

    def getFrameSliderWidth(self):
        return self.frameSlider.width()

    def getImageSequence(self):
        return self._imageSequence

    # frame-related methods
    def clearImageClick(self):
        self.image.clearImageClick()

    def displayFrame(self, i):
        """
        Displays frame[i] in the viewer.  Reads frame[i] from the video file, if necessary.
        Returns True is a frame was successfully read; otherwise, returns False.
        """
        # read frame         
        frame = self.readFrame(i)  
        if frame is None:
            print(f"Unable to read frame {i}")
            return  False      
        # if the frame actual has changed, invoke the client frame change callback
        if i != self._currentFrame and self._frameChangeCallback is not None:
            func = self._frameChangeCallback
            func(i)
        self._currentFrame = i

        if type(frame) is QtGui.QImage:
            pixmap = QtGui.QPixmap.fromImage(frame)        
        else:
            # this is a cv2 image
            # convert the image into the proper format for Qt              
            if len(frame.shape) == 3:
                # this is a color image        
                qimg = QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QtGui.QImage.Format_BGR888)
                pixmap = QtGui.QPixmap.fromImage(qimg)
        
            else:
                # this is a grayscale image
                pixmap = QtGui.QPixmap.fromImage(
                            QtGui.QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[1], QtGui.QImage.Format_Grayscale8) 
                            )            
        self.image.setPixmap(pixmap)                              
        # update the slider
        self.frameSlider.setValue(i+1)
        # update the time label
        self.timeLabel.setText(f"{i+1}/{self.getFrameCount()}")
        return True


    def frame(self, i):
        """Returns frame[i] of the video"""
        f = self._imageSequence.frame(i)
        return f


    def goBackOneFrame(self):
        """Displays the previous frame in the video"""
        self.displayFrame(max(0, self._currentFrame - 1))        


    def goBackTenFrames(self):
        """Moves back ten frames in the video, if possible"""
        self.displayFrame(max(0, self._currentFrame - 10))


    def goFirstFrame(self):
        """Displays the first frame in the video"""
        self.displayFrame(0)


    def goForwardOneFrame(self):
        """Displays the next frame in the video, if there is one."""
        if self._currentFrame < self.getFrameCount()-1:
            if not self.displayFrame(self._currentFrame + 1):
                # error reading frame; move past the frame
                self._currentFrame += 1
        elif self._timer.isActive():
            self._timer.stop()
            self.playBtn.setIcon(self._iconPlay)
            self.setMediaControlsEnable(True)


    def goForwardTenFrames(self):
        """Moves forward ten frames in the video, if possible"""
        self.displayFrame(min(self.getFrameCount()-1, self._currentFrame + 10))

    def goLastFrame(self):
        """Displays the last frame that has been read so far, which may not be the last frame in the video file."""
        # the first time this is called for a video, it may take a while
        # so disable the controls and put up a wait cursor
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.setMediaControlsEnable(False)
        self.displayFrame(self._imageSequence.numberOfFrames()-1)
        self.setMediaControlsEnable(True)
        QtGui.QGuiApplication.restoreOverrideCursor()

    def gotoFrame(self, i):
        """Go to frame i"""
        self.displayFrame(min(i, self.getFrameCount()-1))


    def gotoFrameDialog(self):
        """Callback function for clicking the Go To Frame button.  Prompts the user for frame to go to,
        the goes."""
        frame, ok = QtWidgets.QInputDialog().getInt(self, "Go To Frame", "Frame Number:", 1, 1, self.getFrameCount())
        if ok:
            self.gotoFrame(frame - 1)


    def imageClick(self):
        """Returns the point of the most recent mouse click on the video image, in image coordinates"""
        return self.image.getImageClick()


    def openImageFolder(self, path):
        """Open the specified image sequence folder and load its first frame into the viewer"""
        self.setFilename(path)
        self._imageSequence = StillSequence(path, self.getConvertToGrayscale())
        self.openAfterAction()


    def openVideoFile(self, filename):
        """Open the specified video file and load its first frame into the viewer"""
        self._imageSequence = VideoSequence(filename, self.getConvertToGrayscale())
        self.openAfterAction()
        self.setFilename(filename)

    def openAfterAction(self):
        """Actions to be run after a video file is opened"""
        # set up the display controls
        self.frameSlider.setMinimum(1)
        self.frameSlider.setMaximum(self.getFrameCount())  
        self._currentFrame = None     
        self.displayFrame(0)
        self.playbackSpeed.setValue(int(self.getFrameRate()))
        self.setMediaControlsEnable(True)
        self.gotoFrameBtn.setEnabled(True)


    def _playbackSpeedChanged(self):
        """Update the playback rate using spin button value"""
        self._playbackRate = 1.0 / self.playbackSpeed.value()
        if self._timer.isActive():
            self._timer.stop()
            self._timer.start(self._playbackRate * 1000)


    def playFrames(self):
        """Toggles the playing of video"""
        if self._timer.isActive():
            self._timer.stop()
            self.playBtn.setIcon(self._iconPlay)
            self.setMediaControlsEnable(True)
        else:
            self.playBtn.setIcon(self._iconPause)
            self._timer.start(self._playbackRate * 1000)
            # disable the other buttons
            self.setMediaControlsEnable(False)
            self.playBtn.setEnabled(True)


    def readFrame(self, i):
        """Ensures that frame[i] has been read from the video file and is
        stored in the frame cache."""
        if i >= self.getFrameCount():
            raise Exception(f"Request frame {i} exceeds the length of this video ({self.getFrameCount()})")
        else:
            return self._imageSequence.readFrame(i)


    def saveAsVideo(self, filename, startFrame, stopFrame):
        """Saves the current image sequence as a video file"""
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.setMediaControlsEnable(False)
        self._imageSequence.saveAsVideo(filename, startFrame, stopFrame)
        self.setMediaControlsEnable(True)
        QtGui.QGuiApplication.restoreOverrideCursor()        


    def setDrawCallback(self, function):
        """Sets the client callback function for drawing on the video frame image.  The callback
        should take one argument, the painter to be used for drawing.
        """
        self.image.setDrawFunction(function)


    def setFrameChangeCallback(self, function):
        """Sets the client callback function for notifying when the current frame changes.  The
        callback should take one argument, the new current frame."""
        self._frameChangeCallback = function


    def setImageClickCallback(self, function):
        """Sets the client callback function for the click event on the image.  The callback
        should take one argument, the click point."""
        self.image.setClickCallback(function)


    def setMediaControlsEnable(self, val):
        """Enables/disables all the media player controls"""
        self.firstFrameBtn.setEnabled(val)
        self.backSeveralBtn.setEnabled(val)
        self.backOneBtn.setEnabled(val)
        self.playBtn.setEnabled(val)
        self.forwardOneBtn.setEnabled(val)
        self.forwardSeveralBtn.setEnabled(val)                              
        self.lastFrameBtn.setEnabled(val)   
        self.scaleImageBtn.setEnabled(val)
        self.frameSlider.setEnabled(val)
        self.repaint()
        
    def _sliderChanged(self):
        """Displays the frame with index specified by the frameSlider"""
        if self._currentFrame != (self.frameSlider.value() - 1):
            self.displayFrame(self.frameSlider.value() - 1)

    def _sliderPressed(self):
        """Disables media controls while slider is pressed"""
        self.setMediaControlsEnable(False)

    def _sliderReleased(self):
        """Enables media controls when slider is released"""
        self.setMediaControlsEnable(True)

    def toggleScale(self):
        """Toggles video display between scaling image to fit the app window
        and showing full-size image"""
        self._scaleImage = not self._scaleImage
        if self._scaleImage:
            self.scaleImageBtn.setIcon(self._iconFullSizeImage)
            self.scrollableArea.setWidgetResizable(True)            
        else:
            self.scaleImageBtn.setIcon(self._iconScaleImage)
            self.scrollableArea.setWidgetResizable(False)            
            if self._currentFrame is not None:
                frame = self.frame(self._currentFrame)
                if type(frame) is QtGui.QImage:
                    size = (frame.height(), frame.width())
                else:
                    size = frame.shape
                self.image.resize(size[1], size[0])

    

            
        
        










 
