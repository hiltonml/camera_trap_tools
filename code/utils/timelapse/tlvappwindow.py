"""
Time-Lapse Video Player Application Window
Mike Hilton, Eckerd College

This file contains a Pyside2-, Qt5-based application that demonstrates
the use of the TimeLapseViewer widget.  This application can be used 
as the starting point for applications that analyze or manipulate
individual frames of image sequences.
"""

import configparser
import cv2
import os
import signal
import sys

from PySide2 import QtCore, QtWidgets

from .filehistory import FileHistoryManager
from .timelapse_viewer import TimeLapseViewer


class TLV_ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # instance variables
        self._appTitle = "Time Lapse Viewer"            # application's title text
        self._config = configparser.ConfigParser()      # configuration manager for this app
        self._configFilename = "app.config"             # name of config file for this app   
        self._fileHistory = None                        # opened file history manager 
        self._main = QtWidgets.QWidget()                # the central widget for this app
        self._sequenceFolder = None                     # default location of image sequences
        self._videoFolder = None                        # default location of videos
        self._videoOpen = False                         # indicates if the images viewed are from a video file
        # initialization actions
        self.setWindowTitle(self.getAppTitle())          
        self.setCentralWidget(self._main)                 
        # load a config object from the app.config file, if there is one
        if os.path.exists(self.getConfigFilename()):
            self.getConfig().read(self.getConfigFilename())
        # initialize the file history
        self._fileHistory = FileHistoryManager(self._config)
        self._fileHistory.loadHistory()
        # create menu bar
        self._createMenus()
        # create the main body of the app
        self.mainLayout = QtWidgets.QGridLayout(self._main)
        self.tlviewer = TimeLapseViewer(self)
        self.mainLayout.addWidget(self.tlviewer, 0, 0)

    def afterLoadingSequence(self):
        """
        This method is called after a video or image sequence is loaded.
        This method is intended to be overridden by an inheriting child class.
        """
        pass   

    def beforeLoadingSequence(self):
        """
        This method is called before a video or image sequence is loaded.
        This method is intended to be overridden by an inheriting child class.
        """
        pass

    def _createMenus(self):
        """
        Creates the File menu structure for the app
        """
        bar = self.menuBar()
        # file commands
        fileMenu = bar.addMenu("File")
        ## file opening-related commands
        fileOpenVideoAction = fileMenu.addAction("Load Video")
        fileOpenVideoAction.triggered.connect(self.loadVideo)
        fileOpenImagesAction = fileMenu.addAction("Load Image Sequence")
        fileOpenImagesAction.triggered.connect(self.loadImages)       
        self._recentFilesMenu = fileMenu.addMenu("Recent Files...")
        self._fileHistory.refreshMenu(self._recentFilesMenu, self.openHistoryItem)
        ## file save-related commands
        fileMenu.addSeparator()   
        self.menu_fileSaveVideoAction = fileMenu.addAction("Save Sequence as Video")
        self.menu_fileSaveVideoAction.triggered.connect(self.saveAsVideo)
        self.menu_fileSaveVideoAction.setDisabled(True)
        self.menu_fileSaveImageAction = fileMenu.addAction("Save Frame as Image")
        self.menu_fileSaveImageAction.triggered.connect(self.saveFrame)  
        self.menu_fileSaveImageAction.setDisabled(True)     
        ## exit command
        fileMenu.addSeparator()          
        fileExit = fileMenu.addAction("Exit") 
        fileExit.triggered.connect(self.exit)

    def exit(self):
        """
        Exits the application
        """
        self.close()

    def getAppTitle(self):
        """
        Returns the application's title text
        """
        return self._appTitle

    def getCentralLayout(self):
        """
        Returns the layout manager for the app's central widget.  This is
        where you would add new widgets to the app.
        """
        return self.mainLayout

    def getConfig(self):
        """
        Returns the configuration object for this application
        """
        return self._config

    def getConfigFilename(self):
        """
        Returns the name of the config file for this application
        """
        return self._configFilename

    def getCurrentFrame(self):
        """
        Returns the index of the current video frame
        """
        return self.tlviewer.getCurrentFrame()

    def getFrameFilename(self, index):
        """
        Returns the file name of the current image sequence frame.
        """
        return self.tlviewer.getFrameFilename(index)

    def getFilename(self):
        """
        Returns the name of the video file, or folder name of the image
        sequence, currently loaded.
        """
        return self.tlviewer.getFilename()

    def getFrameCount(self):
        """
        Returns the number of frames in the video
        """
        return self.tlviewer.getFrameCount()

    def getTimeLapseViewer(self):
        """
        Returns the TimeLapseViewer object.
        """
        return self.tlviewer

    def imageClick(self):
        """
        Returns a QPoint indicating the location of the most recent mouse click
        on the time-lapse image.  If no mouse click has been made, None is returned.
        """
        return self.tlviewer.imageClick()

    def loadImages(self):
        """
        Presents the user with a folder selection dialog to select a folder containing an image sequence,
        which is then displayed in the time-lapse viewer widget.
        """
        dialog = QtWidgets.QFileDialog(self, caption="Open Folder Containing Images", directory=self._sequenceFolder)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        if dialog.exec_():
            folder = dialog.selectedFiles()[0]
            self.openImageSequence(folder)


    def loadVideo(self):
        """
        Presents the user with a file open dialog to select a video file,
        which is then displayed in the time-lapse viewer widget.
        """      
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open Video", filter="Video Files (*.mpg *.mp4 *.avi)", dir=self._videoFolder)
        if len(fileName) > 0:
            self.openVideo(fileName)


    def openHistoryItem(self, checked, filepath):
        """
        Opens an image sequence or video present in the file history
        """
        # check if this is a video file
        _, ext = os.path.splitext(filepath)
        if ext in [".mp4", ".mpg", ".avi"]:
            self.openVideo(filepath)
        else:
            # this must be an image sequence
            self.openImageSequence(filepath)  

    def openImageSequence(self, folder):
        """
        Opens an image sequence located in folder.
        """
        self.beforeLoadingSequence()        
        self._fileHistory.updateMenu(folder, self._recentFilesMenu, self.openHistoryItem)   
        self.writeConfig()  
        self._videoOpen = False           
        self.tlviewer.openImageFolder(folder)
        self.setWindowTitle(self.getAppTitle() + ": " + folder)
        self.updateMenuItems()
        self.afterLoadingSequence()

    def openVideo(self, fileName):
        """
        Opens the video file specified by fileName.
        """
        self.beforeLoadingSequence()        
        self._fileHistory.updateMenu(fileName, self._recentFilesMenu, self.openHistoryItem)   
        self.writeConfig()       
        try:
            self._videoOpen = True   
            self.tlviewer.openVideoFile(fileName)     
            self.updateMenuItems()                 
        except:
            QtWidgets.QMessageBox.information(self, "Load Video", "Error loading video", QtWidgets.QMessageBox.StandardButton.Ok)
        self.setWindowTitle(self.getAppTitle() + ": " + os.path.basename(fileName))  
        self.afterLoadingSequence() 

    def safe_timer(self, timeout, func, *args, **kwargs):
        """
        Create a timer that is safe against garbage collection and overlapping
        calls. See: http://ralsina.me/weblog/posts/BB974.html
        """
        def timer_event():
            try:
                func(*args, **kwargs)
            finally:
                QtCore.QTimer.singleShot(timeout, timer_event)
        QtCore.QTimer.singleShot(timeout, timer_event)

    def saveAsVideo(self):
        """
        Writes the image sequence (or video) currently displayed in the time-lapse viewer widget as a new video
        file.  Presents the user with a file save dialog to specify the video file that will be written.
        """  
        stopFrame, ok = QtWidgets.QInputDialog().getInt(self, "Save Video Frame Range", "Final Frame:", self.getFrameCount(), self.getCurrentFrame()+1, self.getFrameCount())
        if ok:
            filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save As Video", filter="Video Files (*.mp4);;All Files (*)")
            if len(filename[0]) > 0:
                self.tlviewer.saveAsVideo(filename[0], self.getCurrentFrame(), stopFrame)
                QtWidgets.QMessageBox.information(self, "Save Complete", "Video saved.", QtWidgets.QMessageBox.StandardButton.Ok)

    def saveFrame(self):
        """
        Writes out the current frame as a still image.
        """
        filename = QtWidgets.QFileDialog.getSaveFileName(self, caption="Save As Image", filter="Image Files (*.jpg);;All Files (*)")
        if len(filename[0]) > 0:
            base, ext = os.path.splitext(filename[0])
            if ext == '':
                ext = '.jpg'
            frame = self.tlviewer.frame(self.getCurrentFrame())
            cv2.imwrite(base + ext, frame)

    def setAppTitle(self, title):
        """
        Sets the application title text.
        """
        self._appTitle = title

    def setConfigFile(self, path):
        """
        Sets the application configuration file.
        """
        self._configFilename = path

    def setDrawCallback(self, function):
        """
        Sets the client callback function for drawing on the video frame image.  The callback
        should take one argument of type QtGui.QPainter, which is the painter to be used for drawing.
        """
        self.tlviewer.setDrawCallback(function)

    def setFrameChangeCallback(self, function):
        """
        Sets the client callback function for notifying when the current frame changes.  The
        callback should take one argument of type integer, which is the new current frame index.
        """
        self.tlviewer.setFrameChangeCallback(function)

    def setImageClickCallback(self, function):
        """
        Sets the client callback function for the click event on the image.  The callback
        should take one argument of type QtCore.QPoint, which is the click location.
        """
        self.tlviewer.setImageClickCallback(function)        

    def setup_interrupt_handling(self):
        """
        Setup handling of KeyboardInterrupt (Ctrl-C) for PySide2.
        """
        signal.signal(signal.SIGINT, _interrupt_handler)
        # Regularly run some (any) python code, so the signal handler gets a
        # chance to be executed:
        self.safe_timer(50, lambda: None)

    def updateMenuItems(self):
        """
        Enables/Disables menu items based on state of self.
        """
        seq = self.tlviewer._imageSequence
        self.menu_fileSaveVideoAction.setDisabled(seq is None)
        self.menu_fileSaveImageAction.setDisabled(seq is None)



    def videoIsOpen(self):
        """
        Returns a boolean indicating if a video is open (True) or an image sequence (False).
        """
        return self._videoOpen

    def writeConfig(self):
        """
        Writes out the config file.
        """
        with open(self.getConfigFilename(), "w") as outFile:
            self.getConfig().write(outFile)  


# Define this as a global function to make sure it is not garbage
# collected when going out of scope:
def _interrupt_handler(signum, frame):
    """Handle KeyboardInterrupt: quit application."""
    QtWidgets.QApplication.quit()



if __name__ == "__main__":
    
    qapp = QtWidgets.QApplication(sys.argv)
    app = TLV_ApplicationWindow()

    # install a handler to kill the app when ^-C is typed in command window
    app.setup_interrupt_handling()

    app.show()
    qapp.exec_()


