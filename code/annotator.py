#! /usr/bin/python3
"""
Camera Trap Time-Lapse Video Annotation App
Mike Hilton and Mark Yamane, Eckerd College
"""

# standard Python modules
import argparse
import configparser
import getpass
import __main__
import os
import sys

# 3rd party modules
import cv2
from PySide2 import QtCore, QtGui, QtWidgets

# modules that are part of this package
import utils
from utils.annotation import AnnotationList
from utils.annotation_count_editor import CountEditor
from utils.annotation_editor import AnnotationEditor
from utils.annotation_table import AnnotationTable
from utils.annotation_timeline import TimeLineDisplay
from utils.timelapse.tlvappwindow import TLV_ApplicationWindow
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
        self.annotationFolder = settings["default_annotation_folder"]       # path to folder where annotation files are kept
        if not os.path.exists(self.annotationFolder):
            os.makedirs(self.annotationFolder, exist_ok=True)
        self.boxesFolder = settings["detection_box_folder"]                 # path to object detection folders for images
        self.prefix = settings.get("prefix", "")                            # filename prefix string          
        self.sequenceFolder = settings["default_image_folder"]
        self.videoBoxesFolder = settings["default_video_folder"]           # path to object detection folder for videos
        self.videoFolder = settings["default_video_folder"]

        # settings specific to this application
        settings = self.app_config["Annotator"]
        self.mode = int(settings.get("mode", 0))                            # annotation mode; 0=count only; 1=focal species; 2=focal and commensal species
        self.showOdBoxes = bool(int(settings.get("show_detection_boxes", 1))) # indicates if object detection boxes should be drawn on images if available
        self.trainingFolder = settings["training_folder"]                   # folder where ML training images are written

        self.countOnly = (self.mode == 0)                                   # Show the animal count editor, instead of activity editor
        self.showCommensal = (self.mode == 2)                               # indicates if commensal editor should be shown        

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


class AnnotatorApp(TLV_ApplicationWindow):
    def __init__(self, configFile):
        # read the configuration file
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)

        super().__init__()
        # intialize instance variables        
        self._annotations = AnnotationList()    # list of annotations for the current video             
        self.commensalBehaviors = {}            # dictionary mapping commensal ID to properties dictionary
        self._commensalEditor = None            # AnnotationEditor object for commensals
        self._countEditor = None                # CountEditor object               
        self._dirty = False                     # tracks if contents of _annotations has changed
        self._odBoxes = None                    # list of object detection boxes for current frame                      
        self._tortoiseEditor = None             # AnnotationEditor object for tortoises
        self.tortoiseBehaviors = {}             # dictionary mapping tortoise ID to properties dictionary          
        self.userName = None                    # username of person running this program      
        self._videoOdBoxes = None               # dictionary mapping frame indices to lists of object detection boxes
        # perform intialization actions
        self.setAppTitle("Video Annotator")
        self.setWindowTitle(self.getAppTitle())  
        self._sequenceFolder = self.app_config.sequenceFolder
        self._videoFolder = self.app_config.videoFolder       
        self.userName = getpass.getuser()
        self._addAnnotatorMenus()
        self._addAnnotatorWidgets()
        self._annotations.modified.connect(self._isDirty)
        self._annotations.modified.connect(self._timeline.annotationsModified)
        self._annotations.modified.connect(self._annotTable.fillTable)
        # set up the callbacks
        self.setFrameChangeCallback(self._frameChangeCallback)
        self.setDrawCallback(self._frameDrawCallback)

    def _addAnnotatorMenus(self):
        """
        Add a new menu items to the app
        """
        bar = self.menuBar()
        # Annotator commands
        menu = bar.addMenu("Annotator") 
        self.menu_annotatorNextVideo = menu.addAction("Next Video in Series")
        self.menu_annotatorNextVideo.triggered.connect(self.nextVideoInSequence)
        self.menu_annotatorNextVideo.setDisabled(True)
        noSave = menu.addAction("Exit Without Saving Annotations")
        noSave.triggered.connect(self.exitNoSave)
        menu.addSeparator()   
        self.menu_annotationWriteTraining = menu.addAction("Save Frame For Training")
        self.menu_annotationWriteTraining.triggered.connect(self.writeFrameToTrainingDir)
        self.menu_annotationWriteTraining.setDisabled(True)

    def _addAnnotatorWidgets(self):
        """
        Add a new widget to the app.
        """
        layout = self.getCentralLayout() 
        self.setContentsMargins(0,0,0,0)         
        self._createTimeLineWidgets(layout)
        self._createEditorWidgets(layout)  

    def afterLoadingSequence(self):
        """
        This method is called after a new video file or image sequence is loaded.
        """
        # reset the annotation editors
        if self.app_config.countOnly:
            self._countEditor.reset()
        else:
            self._tortoiseEditor.reset()        
            if self._commensalEditor is not None:
                self._commensalEditor.reset()
        # load the annotations for this sequence
        filename = self._getAnnotationFilename()
        if os.path.exists(filename):
            self._annotations.readFromFile(filename, self.tlviewer.getImageSequence())
        # if this is a video, look for boxes file
        self._odBoxes = None
        self._videoOdBoxes = None
        if self._videoOpen:
            filename = self.getFilename()
            burrow_ID, _, _ = trailcamutils.splitVideoFilename(filename, self.app_config.prefix, self.app_config.views)
            box_path = os.path.join(self.app_config.videoBoxesFolder, burrow_ID)			
            box_file = os.path.join(box_path, os.path.splitext(os.path.basename(filename))[0] + ".vboxes")
            if os.path.exists(box_file):
                self._videoOdBoxes = self.readVideoBoxes(box_file)
        # enable the editor container
        self._editorContainer.setEnabled(True)
        # enable menu items
        if self._videoOpen:
            self.menu_annotatorNextVideo.setDisabled(False)
        else:
            self.menu_annotatorNextVideo.setDisabled(False)
        self.menu_annotationWriteTraining.setDisabled(False)
        # enable the event navigation controls
        self.enableTimeLineWidgets(True)


    def beforeLoadingSequence(self):
        """
        This method is called before a new video file or image sequence is loaded.
        """
        if self._dirty:
            self.saveAnnotations()
            self._dirty = False

    def closeEvent(self, event):
        """
        Automatically saves the annotation list when the application closes.
        """
        # save the annotations for this file, if they have changed
        if self._dirty:        
            self.saveAnnotations()
        event.accept()
        
    def _createEditorWidgets(self, layout):
        """
        Creates and initializes the AnnotationEditor and table widgets
        """
        # Create the containers holding the editors.  Multiple nested contains are
        # needed to make automatic horizontal centering of fixed-size editors
        self._editorContainer = QtWidgets.QWidget()
        editorContainerLayout = QtWidgets.QHBoxLayout(self._editorContainer)
        layout.addWidget(self._editorContainer, 3, 0)         
        editors = QtWidgets.QWidget()
        editorContainerLayout.addWidget(editors)
        editors.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)          
        editorLayout = QtWidgets.QGridLayout(editors)     

        # create the counting editor
        self._countEditor = CountEditor(self, 'Number of Focal Animals Visible', self._annotations)
        self.countBehaviors = self._countEditor.getBehaviors()            
        if self.app_config.countOnly:

            editorLayout.addWidget(self._countEditor, 0, 0)

        else:
            # load the focal animal's activities from the application's config file
            self.tortoiseBehaviors = self.readConfigActivities('Focal_Activity')
            ids = self.readConfigList('Focal_ID')
            self._tortoiseEditor = AnnotationEditor(self, 'Focal Animals', 'focal', self.tortoiseBehaviors, ids, self._annotations)
            editorLayout.addWidget(self._tortoiseEditor, 0, 0)
            if self.app_config.showCommensal:
                # load the commensal activities from the application's config file
                self.commensalBehaviors = self.readConfigActivities('Commensal_Activity')
                ids = self.readConfigList('Commensal_ID')
                self._commensalEditor = AnnotationEditor(self, 'Commensal Animals', 'commensal', self.commensalBehaviors, ids, self._annotations)
                editorLayout.addWidget(self._commensalEditor, 0, 1)    

        # create a table view of the annotations
        tableWidget = QtWidgets.QGroupBox('Annotations')
        tableLayout = QtWidgets.QGridLayout(tableWidget)
        tableWidget.setStyleSheet("max-height: 10em;")
        tableWidget.setContentsMargins(0,0,0,0)        
        tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)             
        self._annotTable = AnnotationTable(self, self._annotations)
        tableLayout.addWidget(self._annotTable, 0, 0)
        editorLayout.addWidget(tableWidget, 0, 2)
        self._annotTable.cellClicked.connect(self.tableClicked)

        # disable the editor container
        self._editorContainer.setEnabled(False)

    def _createTimeLineWidgets(self, layout):
        """
        Creates and initializes the time line widgets
        """
        self._timeline = TimeLineDisplay(self, self.getTimeLapseViewer(), self._annotations)
        layout.addWidget(self._timeline, 1, 0)  
        # increase the amount of space needed by the time label of the TimeLapseViewer,
        # to take into account the space required by the vertical scroll bar in the time
        # line
        self.getTimeLapseViewer().timeLabel.setStyleSheet("max-width: 6em; min-width: 6em;")  

        # add next/previous buttons to navigate through annotations
        navBox = QtWidgets.QWidget(self)
        layout.addWidget(navBox, 2, 0)
        navBox.setContentsMargins(0,0,0,0)           
        navBoxLayout = QtWidgets.QHBoxLayout(navBox)
        showBoxes = QtWidgets.QCheckBox('Show Boxes')
        showBoxes.setStyleSheet("max-width: 7em")
        showBoxes.setCheckState(QtCore.Qt.Checked if self.app_config.showOdBoxes else QtCore.Qt.Unchecked)
        navBoxLayout.addWidget(showBoxes)
        showBoxes.stateChanged.connect(self.showBoxes)
        prevAnnot = QtWidgets.QPushButton('< Previous Event')
        navBoxLayout.addWidget(prevAnnot)
        prevAnnot.clicked.connect(self.previousEvent)
        nextAnnot = QtWidgets.QPushButton('Next Event >')
        navBoxLayout.addWidget(nextAnnot)
        nextAnnot.clicked.connect(self.nextEvent)
        
        self.navBox = navBox
        self.enableTimeLineWidgets(False)

    def enableTimeLineWidgets(self, enabled):
        """
        Enables or disables all timeline widgets
        """
        self.navBox.setEnabled(enabled)

    def exitNoSave(self):
        """
        Exit the program without saving the annotations.  Works by setting the _dirty flag to False, then
        exiting.
        """
        self._dirty = False
        self.exit()
         
    def _frameChangeCallback(self, index):
        """
        Frame change callback does the following:
        - loads the object detection boxes into the list self._odBoxes
        - enables the span editor button if the index falls between an annotation segment
        """
        # enable span editor button, if called for
        if self._tortoiseEditor is not None:
            self._tortoiseEditor.spanBtn.setEnabled(
                self._annotations.findSpanningEvent(index+1, "count", None) is not None
                )

        # load object detection boxes
        if not self.app_config.showOdBoxes:
            return
        if self.videoIsOpen():
            if self._videoOdBoxes is not None:
                self._odBoxes = self._videoOdBoxes.get(index, None)
        else:
            # construct path to boxes file
            filename = os.path.basename(self.getFrameFilename(index))            
            imagePath = trailcamutils.imagePathFromFilename(filename, self.app_config.prefix, self.app_config.views)
            base, _ = os.path.splitext(filename)
            boxPath = os.path.join(self.app_config.boxesFolder, imagePath, base + ".boxes")
            if os.path.exists(boxPath):
                self._odBoxes = self.readImageBoxes(boxPath)
            else:
                self._odBoxes = None


    def _frameDrawCallback(self, painter):
        """
        Frame drawing callback.  Draw the boxes (if any) in the list self._odBoxes.
        """
        if (self._odBoxes is not None) and self.app_config.showOdBoxes:
            for box in self._odBoxes:
                rect, color = box
                pen = QtGui.QPen(color)
                pen.setWidth(6)
                painter.setPen(pen)
                painter.drawRect(rect)

    def _getAnnotationFilename(self):
        """
        Returns the name of the annotation file associated with the current
        image sequence.
        """
        # determine if this is a video file or an image sequence
        sequence = self.getTimeLapseViewer().getImageSequence()
        if sequence is None:
            return None
        if type(sequence) is utils.timelapse.image_sequence.VideoSequence:
            base, _ = os.path.splitext(os.path.basename(sequence.getFilename()))
            site_ID, _, date = trailcamutils.splitVideoFilename(base, self.app_config.prefix, self.app_config.views)
            return os.path.join(self.app_config.annotationFolder, 
                                trailcamutils.createAnnotationFilename(site_ID, date, self.app_config.prefix))
        else:
            def splitall(path):
                allparts = []
                while 1:
                    parts = os.path.split(path)
                    if parts[0] == path:  # sentinel for absolute paths
                        allparts.insert(0, parts[0])
                        break
                    elif parts[1] == path: # sentinel for relative paths
                        allparts.insert(0, parts[1])
                        break
                    else:
                        path = parts[0]
                        allparts.insert(0, parts[1])
                return allparts 
            # build a file name from the last three dir names in sequence path
            folder = os.path.abspath(sequence.getFilename())
            parts = splitall(folder)
            parts.reverse()
            fname = trailcamutils.createAnnotationFilename(parts[2], parts[1], "")
            return os.path.join(self.app_config.annotationFolder, fname)

    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__main__.__file__)
        return base + ".config"

    def getFrameDateTime(self, i):
        """
        Returns the datetime object for the current frame.
        """
        sequence = self.getTimeLapseViewer().getImageSequence()
        if sequence is None:
            return ""
        else:
            return sequence.frameTime(i)

    def gotoEvent(self, frame, behavior, individual, kind):
        """
        Sets the current time lapse viewer frame to the start frame of the event, and selects
        the behavior and animal ID buttons to match those specified
        """
        # set the editing controls
        self.getTimeLapseViewer().gotoFrame(frame)
        if kind == "tortoise" and self._tortoiseEditor is not None:
            self._tortoiseEditor.clearSelections()            
            self._tortoiseEditor.selectID(individual)
            self._tortoiseEditor.selectBehavior(behavior)
        elif kind == "commensal" and self.app_config.showCommensal:
            self._commensalEditor.clearSelections()            
            self._commensalEditor.selectID(individual)
            self._commensalEditor.selectBehavior(behavior) 
        elif kind == "count" and self._countEditor is not None:
            if self.app_config.countOnly:
                self._countEditor.clearSelections()
            else:
                # clear the other editors
                self._annotTable.clearSelection()
                if self._tortoiseEditor is not None:
                    self._tortoiseEditor.clearSelections() 
                if self._commensalEditor is not None:
                    self._commensalEditor.clearSelections()



    @QtCore.Slot()
    def _isDirty(self):
        """
        Sets the annotations dirty flag to True.
        """
        self._dirty = True


    def nextEvent(self):
        """
        Navigates from current video frame to the next frame that has an event in the annotation list.
        If there are no events after the current frame, do nothing.
        """
        current = self.getTimeLapseViewer().getCurrentFrame()
        eventFrames = self._annotations.eventFrames(not self.app_config.countOnly)
        # goto the first event frame after current frame
        event = None
        for event in eventFrames:
            if current < event:
                break
        if event is None:
            return

        self.getTimeLapseViewer().gotoFrame(event)
        ann = self._annotTable.gotoEvent(event)
        if ann is not None:
            frame, behavior, id, kind = ann
            self.gotoEvent(frame, behavior, id, kind)

            
    def nextVideoInSequence(self):
        """
        Load the next video or image sequence after the current one.
        """
        seq = self.getTimeLapseViewer()._imageSequence.getFilename()
        folder = os.path.dirname(seq)
        if self.getTimeLapseViewer()._imageSequence.isVideo():
            files = trailcamutils.getFilenamesInFolder(folder, ".mp4")
            idx = files.index(os.path.basename(seq)) + 1
            _, view, currDate = trailcamutils.splitVideoFilename(seq, self.app_config.prefix, self.app_config.views)
            nextDate = currDate
            nextView = None
            # move past other videos for this day
            while idx < len(files):
                _, nextView, nextDate = trailcamutils.splitVideoFilename(files[idx], self.app_config.prefix, self.app_config.views)
                if (nextDate > currDate) and (nextView == view):
                    break
                idx += 1
            # load the next video
            if (idx < len(files)) and (nextDate > currDate) and (nextView == view):
                self.openVideo(os.path.join(folder, files[idx]))
            else:
                QtWidgets.QMessageBox.information(self, "Next Video", "No more videos in this folder", QtWidgets.QMessageBox.StandardButton.Ok)
        else:
            view = os.path.split(seq)[1]
            site, date = os.path.split(folder)
            folders = trailcamutils.getSubfolders(site)
            idx = folders.index(folder) + 1
            if idx < len(folders):
                dateFolder = os.path.join(site, folders[idx])
                views = trailcamutils.getSubfolders(dateFolder, includePath=False)
                try:
                    idx = views.index(view)
                except:
                    idx = 0
                if idx < len(views):
                    self.openImageSequence(os.path.join(dateFolder, views[idx]))
                else:
                    QtWidgets.QMessageBox.information(self, "Next Sequence", "Next day appears to be empty", QtWidgets.QMessageBox.StandardButton.Ok)
            else:
                QtWidgets.QMessageBox.information(self, "Next Sequence", "No more sequences in this folder", QtWidgets.QMessageBox.StandardButton.Ok)


    def previousEvent(self):
        """
        Navigates from the current video frame to the previous frame that has an event in the annotation list.
        """
        current = self.getTimeLapseViewer().getCurrentFrame()
        eventFrames = self._annotations.eventFrames(not self.app_config.countOnly)
        # goto the first event frame before current frame
        i = 0
        for event in eventFrames:
            if current <= event:
                break  
            i = event  

        self.getTimeLapseViewer().gotoFrame(i)
        ann = self._annotTable.gotoEvent(i)
        if ann is not None:
            frame, behavior, id, kind = ann
            self.gotoEvent(frame, behavior, id, kind)        

    def readConfigActivities(self, section):
        """
        Reads a dictionary mapping activity names to specifications from the supplied section
        of the application config file.
        """
        answer = {}
        config = self.getConfig()
        if section in config:
            for key, value in config[section].items():
                # create a dictionary of the properties found in the value
                parts = value.split(',')
                properties = {}
                properties['color'] = parts[0].strip()
                properties['arity'] = parts[1].strip()
                # add to the activity dictionary
                answer[key] = properties
        return answer

    def readConfigList(self, section):
        """
        Reads a list of strings from the specified section of the application config file.
        These should be sections containing only keys, no values.
        """
        answer = []
        config = self.getConfig()
        if section in config:
            answer = list(config[section].keys())
        return answer          

    def readImageBoxes(self, filename):
        """
        Reads the object detection box information from the specified file.
        Returns a list of the detection boxes.
        """
        boxes = []
        with open(filename, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                yl = int(parts[0])
                xl = int(parts[1])
                yu = int(parts[2])
                xu = int(parts[3])
                color_R = int(parts[4])
                color_G = int(parts[5])
                color_B = int(parts[6])

                rect = QtCore.QRectF(QtCore.QPointF(xl, yl), QtCore.QPointF(xu, yu))
                color = QtGui.QColor(color_R, color_G, color_B)
                boxes.append((rect, color))
        return boxes

    def readVideoBoxes(self, filename):
        """
        Reads the object detection box information from the specified video.
        Returns a dictionary mapping frame index to list of boxes.
        """
        boxes = {}
        with open(filename, "r") as f:
            for aLine in f:
                parts = aLine.strip().split(",")
                frame = int(parts[0])
                yl = int(parts[1])
                xl = int(parts[2])
                yu = int(parts[3])
                xu = int(parts[4])
                color_R = int(parts[5])
                color_G = int(parts[6])
                color_B = int(parts[7])

                rect = QtCore.QRectF(QtCore.QPointF(xl, yl), QtCore.QPointF(xu, yu))
                color = QtGui.QColor(color_R, color_G, color_B)

                if frame not in boxes:
                    boxes[frame] = []
                boxes[frame].append((rect, color))
        return boxes
    
    def saveAnnotations(self):
        """
        Saves the annotations associated with the current image sequence.
        """
        filename = self._getAnnotationFilename()
        if filename is not None:
            self._annotations.writeToFile(filename)

    def showBoxes(self, val):
        """
        This method is called when the user changes the state of the 'Show Boxes' check box.
        """
        self.app_config.showOdBoxes = (val == 2)

    def tableClicked(self, row, col):
        """
        This method is called when the user clicks on a cell of the annotation table.
        """
        if self._annotTable.item(row, 0) is None:
            return
        # extract fields from the table row
        self._annotTable.selectRow(row)
        startFrame = int(self._annotTable.item(row, 0).text())
        behavior = self._annotTable.item(row, 2).text()
        individual = self._annotTable.item(row, 3).text()
        kind = self._annotTable.item(row, 4).text()
        if col == 1:
            endFrame = self._annotTable.item(row, 1).text()
            if endFrame != '':
                self.gotoEvent(int(endFrame)-1, behavior, individual, kind) 
        else:
            self.gotoEvent(startFrame-1, behavior, individual, kind)

    def writeFrameToTrainingDir(self):
        """
        Writes the current frame to the ML training folder.
        """
        idx = self.getCurrentFrame()
        seq = self.getTimeLapseViewer()._imageSequence
        if seq.isVideo():            
            # create a file name for the saved image
            date_time = seq.frameTime(idx)
            date = date_time.strftime("%Y%m%d")
            time = date_time.strftime("%H%M%S")
            site_ID, view, _ = trailcamutils.splitVideoFilename(seq._filename, self.app_config.prefix, self.app_config.views)
            filename = trailcamutils.createImageFilename(self.app_config.prefix, site_ID, date, time, ".jpg", self.app_config.views)
        else:
            filename = os.path.basename(seq.getImageFilename(idx))
        # save the image
        frame = self.tlviewer.frame(idx)
        cv2.imwrite(os.path.join(self.app_config.trainingFolder, filename), frame)



if __name__ == "__main__":
    # parse any command line arguments
    argp = argparse.ArgumentParser()
    argp.add_argument("-c", "--config", default=None, help="config file to use") 
    args = vars(argp.parse_args())

    # create the application object
    qapp = QtWidgets.QApplication(sys.argv)
    app = AnnotatorApp(args["config"])

    # install a handler to kill the app when ^-C is typed in command window
    app.setup_interrupt_handling()

    app.show()
    qapp.exec_()        