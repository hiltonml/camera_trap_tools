"""
Pyside2 widget for editing an AnnotationList object
Mike Hilton and Mark Yamane, Eckerd College

An AnnotationEditor contains three columns:
- toggle buttons representing activities
- a multiselect list containing IDs of animals
- Start, Stop, and Delete buttons
"""

from PySide2 import QtCore, QtGui, QtWidgets
from .annotation import Annotation, AnnotationList

class AnnotationEditor(QtWidgets.QGroupBox):
    def __init__(self, clientObj, title, animalKind, activityDict, ids, annotationListObj):
        """
        Class constructor.
        Inputs:
            clientObj           Client object (typically an application built on TLV_ApplicationWindow) to contain this editor
            title               string; title to be displayed for this editor
            animalKind          string; category name to be used in annotation objects
            activityDict        dictionary[string]->dict[string]; maps activity names to properties dictionary
            ids                 list[string]; unique identifiers for each animal
            annotationListObj   the AnnotationList object being edited
        """
        super().__init__(title)
        # initialize instance variables
        self._activityDict = activityDict       # dictionary mapping the names of activities to property dictionary
        self._animalKind  = animalKind          # the kind of animal this widget is for        
        self._annotations = annotationListObj   # the AnnotationList object being edited
        self._client = clientObj                # client application containing this editor
        self._ids = ids                         # list of strings; IDs of animals
        # initialization actions
        self._createWidgets()


    def activityButtonClicked(self, btnId):
        """
        This method is called whenever an activity button is clicked by the user.
        The editing command buttons are enabled according on whether the activity 
        is single or paired.
        """
        for button in self.activityBtnGroup.buttons():
            if button is self.activityBtnGroup.button(btnId):
                if self._activityDict[button.text()]['arity'] == "single":
                    # show the Add button
                    self.addBtn.setVisible(True)
                    self.beginBtn.setVisible(False)
                    self.endBtn.setVisible(False)
                    if hasattr(self, "spanBtn"):
                        self.spanBtn.setVisible(False)
                else:
                    # show the Begin, End, and Span buttons
                    self.addBtn.setVisible(False)
                    self.beginBtn.setVisible(True)
                    self.endBtn.setVisible(True)
                    if hasattr(self, "spanBtn"):
                        self.spanBtn.setVisible(True)

    def addAnnotation(self):
        """
        Adds a new annotation at the current frame.
        """
        ids = self.selectedIDs()
        activities = self.checkedActivites()  
        frame = self._client.getCurrentFrame()+1
        dateTime = self._client.getFrameDateTime(frame-1)
        for activity in activities:
            for _, id in ids:
                self._annotations.add(Annotation(frame, None, activity, self._animalKind, id, dateTime, None, self._client.userName))    
        self.moveIDsToTopOfList(ids)

    def beginAnnotation(self):
        """
        Sets the start frame of any annotation that spans the current frame, for each selected 
        individual and activity.  If no such annotations exist, new annotations are created
        that start at the current frame and end at the last frame.
        """
        ids = self.selectedIDs()
        activities = self.checkedActivites()
        start = self._client.getCurrentFrame()+1
        # look for annotations that already exist, and trim the start at the current frame
        indices = self._annotations.findSpanning(start, self._animalKind, ids, activities)
        if len(indices) > 0:
            for index in indices:
                self._annotations.setStartFrame(index, start, self._client.getFrameDateTime(start-1))
        else:
            # no spanning annotation exists, so look at the immediately following events
            following = self._annotations.findNextEvent(start, self._animalKind, ids, activities)
            if following is None:
                following = len(self._annotations)
            for activity in activities:
                for _, id in ids:
                    # look for the first following annotation for this activity, id
                    found = False
                    for i in range(following, len(self._annotations)):
                        annot = self._annotations[i]
                        if ((annot.getKind() == self._animalKind) and 
                            (annot.getIndividual() == id) and
                            (annot.getBehavior() == activity)):
                            annot.setStartFrame(start)
                            annot.setStartTime(self._client.getFrameDateTime(start-1))
                            self._annotations.modified.emit()
                            found = True
                            break
                    if not found:
                        # no following annotation exists, so create a new annotation with a endFrame of FrameCount
                        end = self._client.getFrameCount()                    
                        newAnnot = Annotation(start, end, activity, self._animalKind, id, 
                                                self._client.getFrameDateTime(start-1), 
                                                self._client.getFrameDateTime(end-1), 
                                                self._client.userName)
                        self._annotations.add(newAnnot)
        self.moveIDsToTopOfList(ids)


    def checkedActivites(self):
        """
        Returns a list of the activities with checked buttons.
        """
        answer = []
        for btn in self.activityBtnList:
            if btn.isChecked():
                answer.append(btn.text())
        return answer

    def clearSelections(self):
        """
        Clears any controls that are currently selected in the editor.
        """
        btn = self.activityBtnGroup.checkedButton()
        if btn is not None:
            btn.setChecked(False)
        self.idList.clearSelection()

    def _createWidgets(self):
        """
        Creates the components that make up the annotation widget.
        """       
        def _createActivityBtn(layout, parent, kind, activity, row, properties):
            btn = QtWidgets.QPushButton(activity)
            btn.setCheckable(True)
            btn.setProperty(kind, row)
            btn.setStyleSheet("max-width: 7em; min-width: 7em; min-height: 1em; max-height: 1em; color: " + properties['color'] + ";")
            btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)  
            layout.addWidget(btn)
            return btn

        def _createGridLabel(text):
            label = QtWidgets.QLabel()
            label.setText(text)
            label.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
            label.setStyleSheet("max-width: 7em; min-width: 2em; min-height: 1em;")     
            return label

        def _createIDList(layout, row):
            idList = QtWidgets.QListWidget()
            idList.setSelectionMode(QtWidgets.QListWidget.SingleSelection)
            idList.setProperty('ids', row)
            layout.addWidget(idList)
            return idList

        def _createListBtn(layout, text, row):
            btn = QtWidgets.QPushButton(text)
            btn.setProperty('List', row)
            btn.setStyleSheet("max-width: 7em; min-width: 7em; min-height: 1em; max-height: 1em;")
            layout.addWidget(btn)
            return btn
        
        # the layout is three columns, each of which is a vertical layout
        mainLayout = QtWidgets.QGridLayout(self)
        self.setLayout(mainLayout)  
        self.setStyleSheet("max-height: 10em;")
        self.setContentsMargins(0,0,0,0)        
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)     

        # activity toggle buttons
        activityFrame = QtWidgets.QWidget()                       
        activityLayout = QtWidgets.QGridLayout(activityFrame)
        activityLayout.setAlignment(QtCore.Qt.AlignTop)        
        lbl = _createGridLabel('Activity')
        activityLayout.addWidget(lbl, 0, 0)
        activityBtns = QtWidgets.QWidget()
        activityBtnsLayout = QtWidgets.QVBoxLayout(activityBtns)
        activities = list(self._activityDict.keys())
        self.activityBtnList = []
        for i in range(len(activities)):
            btn = _createActivityBtn(activityBtnsLayout, activityBtns, self._animalKind, 
                                     activities[i], i+1, self._activityDict[activities[i]])       
            self.activityBtnList.append(btn)            
        ## scroll widget
        self.activityScroller = QtWidgets.QScrollArea()
        self.activityScroller.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)    
        self.activityScroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.activityScroller.setWidgetResizable(False)
        self.activityScroller.setWidget(activityBtns)  
        activityLayout.addWidget(self.activityScroller, 1, 0)              
        mainLayout.addWidget(activityFrame, 0, 0) 
        ## create a QButtonGroup to make the activity buttons mutually exclusive
        self.activityBtnGroup = QtWidgets.QButtonGroup(self)
        for btn in self.activityBtnList:
            self.activityBtnGroup.addButton(btn)
        self.activityBtnGroup.buttonClicked[int].connect(self.activityButtonClicked)

        # animal ID list
        idFrame = QtWidgets.QWidget()
        mainLayout.addWidget(idFrame, 0, 1)         
        idLayout = QtWidgets.QVBoxLayout(idFrame)  
        idLayout.setAlignment(QtCore.Qt.AlignTop)          
        lbl = _createGridLabel('ID')
        idLayout.addWidget(lbl)
        self.idList = _createIDList(idLayout, 1)       
        for id in self._ids:
            self.idList.addItem(id) 
        self.idList.setStyleSheet("max-width: 5em;")                      

        # editing buttons
        btnFrame = QtWidgets.QWidget(self)
        mainLayout.addWidget(btnFrame, 0, 2)
        btnLayout = QtWidgets.QVBoxLayout(btnFrame)   
        btnLayout.setAlignment(QtCore.Qt.AlignTop)                
        lbl = _createGridLabel('Annotation')
        btnLayout.addWidget(lbl)
        self.beginBtn = _createListBtn(btnLayout, 'Begin', 1)
        self.beginBtn.clicked.connect(self.beginAnnotation)
        self.beginBtn.setVisible(False)
        self.endBtn = _createListBtn(btnLayout, 'End', 2)
        self.endBtn.clicked.connect(self.endAnnotation)
        self.endBtn.setVisible(False)        
        self.addBtn = _createListBtn(btnLayout, 'Add', 3)
        self.addBtn.clicked.connect(self.addAnnotation)
        self.addBtn.setVisible(False)        
        self.spanBtn = _createListBtn(btnLayout, 'Span', 3)
        self.spanBtn.clicked.connect(self.spanAnnotation)  
        self.spanBtn.setVisible(False)              
        delete = _createListBtn(btnLayout, 'Delete', 4)
        delete.clicked.connect(self.deleteAnnotation) 
          

    def deleteAnnotation(self):
        """
        Deletes any annotation that spans the current frame, for each selected 
        individual and activity.
        """
        ids = self.selectedIDs()
        activities = self.checkedActivites()
        indices = self._annotations.findSpanning(self._client.getCurrentFrame()+1, self._animalKind, ids, activities)
        indices.sort(reverse=True)
        for index in indices:
            self._annotations.pop(index)

    def endAnnotation(self):
        """
        Sets the end frame of any annotation that spans the current frame, for each selected 
        individual and activity.  If no such annotations exist, new annotations are created
        with a start frame of zero and ending at the current frame.
        """
        ids = self.selectedIDs()
        activities = self.checkedActivites()
        end = self._client.getCurrentFrame() + 1
        # look for annotations that already exist, and trim the end to the current frame
        indices = self._annotations.findSpanning(end, self._animalKind, ids, activities)
        if len(indices) > 0:
            for index in indices:
                self._annotations.setEndFrame(index, end, self._client.getFrameDateTime(end-1))
        else:
            # no spanning annotation exists, so look at the immediately preceeding events
            preceeding = self._annotations.findNextEvent(end, self._animalKind, ids, activities) 
            if preceeding is None:
                preceeding = len(self._annotations) - 1
            else:
                preceeding -= 1
            for activity in activities:
                for _, id in ids:
                    # look for the first preceeding annotation for this activity, id
                    found = False
                    for i in range(preceeding, -1, -1):
                        annot = self._annotations[i]
                        if ((annot.getKind() == self._animalKind) and 
                            (annot.getIndividual() == id) and
                            (annot.getBehavior() == activity)):
                            annot.setEndFrame(end)
                            annot.setEndTime(self._client.getFrameDateTime(end-1))
                            self._annotations.modified.emit()
                            found = True
                            break
                    if not found:
                        # no preceeding annotation exists, so create a new annotation with a startFrame of 0
                        self._annotations.add(Annotation(1, end, activity, self._animalKind, id, 
                                                        self._client.getFrameDateTime(0), 
                                                        self._client.getFrameDateTime(end-1), 
                                                        self._client.userName)
                                                        )

        self.moveIDsToTopOfList(ids)


    def moveIDsToTopOfList(self, ids):
        """Moves the IDs to the top of the ID List widget"""
        # first, remove the ids
        for item, _ in ids:
            idx = self.idList.indexFromItem(item).row()           
            self.idList.takeItem(idx)      
        # now innert them at the beginning of the list
        ids.reverse()
        for item, _ in ids:
            self.idList.insertItem(0, item)
        # select the ids
        for item, _ in ids:
            item.setSelected(True)


    def reset(self):
        """
        Resets the editor to a clean state.
        """
        self._annotations.clear()
        self.idList.clearSelection()
        for item in self.activityBtnList:
            item.setChecked(False)

    def selectBehavior(self, behaviorText):
        """
        Selects the behavior button with text matching behaviorText.
        """
        for btn in self.activityBtnList:
            if btn.text() == behaviorText:
                btn.setChecked(True)
                btn.click()
                self.activityScroller.ensureWidgetVisible(btn)
       
    def selectID(self, id):
        """
        Clears any currently selected IDs and selects the specified ID.
        """
        self.idList.clearSelection()
        items = self.idList.findItems(id, QtCore.Qt.MatchExactly)
        if len(items) > 0:
            for item in items:
                self.idList.scrollToItem(item)
                item.setSelected(True)
        
    def selectedIDs(self):
        """
        Returns a list of pairs (item, text) for the animal IDs currently selected.
        """
        answer = []
        for id in self.idList.selectedItems():
            answer.append((id, id.text()))
        return answer

    def spanAnnotation(self):
        """
        Adds new annotations located at the segment that spans the current count frame.
        """
        ids = self.selectedIDs()
        activities = self.checkedActivites()  
        frame = self._client.getCurrentFrame()+1        
        event = self._annotations.findSpanningEvent(frame, "count", None)

        if event is not None:
            for activity in activities:
                for _, id in ids:
                    self._annotations.add(Annotation(
                        event.getStartFrame(), event.getEndFrame(), activity, self._animalKind, id, 
                        event.getStartTime(), event.getEndTime(), self._client.userName
                        ))   
            self.moveIDsToTopOfList(ids)


if __name__ == "__main__":
    import sys


    class Annotation_TestWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self._main = QtWidgets.QWidget()                # the central widget for this app
            self.setWindowTitle("Annotation Tester")          
            self.setCentralWidget(self._main)
            self.annotations = AnnotationList()

            # create the main body of the app
            self.mainLayout = QtWidgets.QVBoxLayout(self._main)

            activities = { 
                "Basking":["blue","paired"], 
                "Walkabout":["green","paired"], 
                "Enter":["red","single"],
                "Exit":["orange", "single"]}
            ids = ['tort1', 'tort2', 'tort3']     
            self.annotator = AnnotationEditor(self, 'Tortoise', 'tortoise', activities, ids, self.annotations) 
            self.mainLayout.addWidget(self.annotator)   

    qapp = QtWidgets.QApplication(sys.argv)
    app = Annotation_TestWindow()
    app.show()
    qapp.exec_()          