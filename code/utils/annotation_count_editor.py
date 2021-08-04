"""
A subclass of the AnnotationEditor for indicating how many objects are
present in a frame: one or more than one.
Mike Hilton, Eckerd College
"""

from .annotation_editor import AnnotationEditor
from .annotation import Annotation, AnnotationList
from PySide2 import QtCore, QtGui, QtWidgets

class CountEditor(AnnotationEditor):
    def __init__(self, clientObj, title, annotationListObj):
        """
        Class constructor.
        Inputs:
            clientObj           Client object (typically an application built on TLV_ApplicationWindow) to contain this editor
            title               string; title to be displayed for this editor
            annotationListObj   the AnnotationList object being edited
        """
        self._activityDict = {
            "1" : {'color': 'black', 'arity': 'paired'},
            "> 1" : {'color': 'green', 'arity': 'paired'}
        }
        self.countBehaviors = self._activityDict
        super().__init__(clientObj, title, 'count', self._activityDict, ['count'], annotationListObj)

    def getBehaviors(self):
        return self._activityDict 

    def countButtonClicked(self, _):
        """
        If an activity button is clicked and the current frame is inside an annotation for a different
        activity, end that annotation at the current frame - 1 and begin a new annotation with this
        activity.
        """
        # check if we are inside an annotation of the opposite type
        ids = self.selectedIDs()
        activities = self.checkedActivites()
        if activities[0] == '1':
            target = ['> 1']
        else:
            target = ['1']
        end = self._client.getCurrentFrame()
        indices = self._annotations.findSpanning(end+1, self._animalKind, ids, target)
        if len(indices) > 0:
            for index in indices:
                if self._annotations[index].getStartFrame() == end+1:
                    # delete the annotation
                    self._annotations.pop(index)
                else:
                    # set new end frame
                    self._annotations.setEndFrame(index, end, self._client.getFrameDateTime(end-1))
        # find the next annotation
        nextAnnot = self._annotations.findNextEvent(end+1, self._animalKind, ids, target)
        if nextAnnot is None:
            # start a new annotation
            self.beginAnnotation()
        else:
            nextAnnot = self._annotations[nextAnnot]
            if nextAnnot.behavior == activities[0]:
                # extend nextAnnot to the left
                nextAnnot.setStartFrame(end+1)
                nextAnnot.setStartTime(self._client.getFrameDateTime(end))
                self._annotations.modified.emit()
            else:
                # fill the allotted space                
                start = end
                end = nextAnnot.getStartFrame() - 1
                newAnnot = Annotation(start+1, end, activities[0], self._animalKind, 'count', 
                                                self._client.getFrameDateTime(start), 
                                                self._client.getFrameDateTime(end), 
                                                self._client.userName)
                self._annotations.add(newAnnot)





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
            idList.setSelectionMode(QtWidgets.QListWidget.MultiSelection)
            idList.setProperty('ids', row)
            layout.addWidget(idList)
            return idList

        def _createListBtn(layout, text, row):
            btn = QtWidgets.QPushButton(text)
            btn.setProperty('List', row)
            btn.setStyleSheet("max-width: 7em; min-width: 7em; min-height: 1em; max-height: 1em;")
            layout.addWidget(btn)
            return btn
        
        # the layout is two columns, each of which is a vertical layout
        mainLayout = QtWidgets.QGridLayout(self)
        self.setLayout(mainLayout)  
        self.setStyleSheet("max-height: 10em;")
        self.setContentsMargins(0,0,0,0)        
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)     

        # activity toggle buttons
        activityFrame = QtWidgets.QWidget()                       
        activityLayout = QtWidgets.QGridLayout(activityFrame)
        activityLayout.setAlignment(QtCore.Qt.AlignTop)        
        lbl = _createGridLabel('Animals Present')
        activityLayout.addWidget(lbl, 0, 0)
        activityBtns = QtWidgets.QWidget()
        activityBtnsLayout = QtWidgets.QVBoxLayout(activityBtns)
        self.activityBtnList = []
        activities = list(self._activityDict.keys())
        for i in range(len(activities)):
            btn = _createActivityBtn(activityBtnsLayout, activityBtns, self._animalKind, 
                                     activities[i], i+1, self._activityDict[activities[i]])  
            btn.clicked.connect(self.countButtonClicked)     
            self.activityBtnList.append(btn)   
        # select the first activity button
        self.activityBtnList[0].setChecked(True)        
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
        idFrame.setVisible(False) 

        # editing buttons
        btnFrame = QtWidgets.QWidget(self)
        mainLayout.addWidget(btnFrame, 0, 2)
        btnLayout = QtWidgets.QVBoxLayout(btnFrame)   
        btnLayout.setAlignment(QtCore.Qt.AlignTop)                
        lbl = _createGridLabel('Annotation')
        btnLayout.addWidget(lbl)
        self.beginBtn = _createListBtn(btnLayout, 'Begin', 1)
        self.beginBtn.clicked.connect(self.beginAnnotation)
        self.endBtn = _createListBtn(btnLayout, 'End', 2)
        self.endBtn.clicked.connect(self.endAnnotation)
        self.addBtn = _createListBtn(btnLayout, 'Add', 3)
        self.addBtn.clicked.connect(self.addAnnotation)
        self.addBtn.setVisible(False)
        delete = _createListBtn(btnLayout, 'Delete', 4)
        delete.clicked.connect(self.deleteAnnotation)  
            
    def selectedIDs(self):
        """
        Returns a list of pairs (item, text) for the animal IDs currently selected.
        """
        return [(self.idList.item(0), self.idList.item(0).text())]    