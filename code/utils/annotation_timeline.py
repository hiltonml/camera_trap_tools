"""
Annotations timeline display
Mike Hilton and Mark Yamane, Eckerd College
"""

# standard Python modules
import math

# 3rd party modules
from PySide2 import QtCore, QtGui, QtWidgets


class TimeLineDisplay(QtWidgets.QAbstractScrollArea):
    def __init__(self, app, timeLapseViewerObject, annotationListObj):
        super().__init__()     
        # initialize instance variables
        self._annotations = annotationListObj           # AnnotationList object begin graphed
        self._canvas = None                             # widget that draws the timelines
        self.app = app                                  # application object containing this widget                            
        self.IDs = []                                   # sorted list of unique individuals
        self.indivDict = {}                             # dictionary mapping individuals to list of Annotations
        self.timeLapseViewer = timeLapseViewerObject    # timeLapseViewer object this time line is slaved to        
        # perform initialization actions
        self._createWidgets()
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)  

    def annotationsModified(self):
        """
        This method is called when the contents of the AnnotationList have been
        modified in some way.
        """
        # update the data structures derived from the AnnotationList
        self.indivDict = self.splitAnnotations(self._annotations)
        self.IDs = sorted(list(self.indivDict.keys()))
        # calculate the vertical space needed to display each individual
        heightNeeded = self._canvas.calculateBlockHeights()
        # update the vertical scroll bar, which scrolls by individuals
        if heightNeeded <= self._canvas.height():
            self.verticalScrollBar().setMaximum(-1)
        else:
            self.verticalScrollBar().setMinimum(0)
            self.verticalScrollBar().setMaximum(len(self.IDs))
        # update the canvas        
        self._canvas.update()

    def _createWidgets(self):
        # set up the canvas
        self._canvas = TimeLineCanvas(self)
        # set up the scroll area
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)    
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.verticalScrollBar().setMinimum(0)
        self.verticalScrollBar().setMaximum(-1)        
        self.verticalScrollBar().setPageStep(1)
        self.verticalScrollBar().setSingleStep(1)
        self.setViewport(self._canvas)

    def mouseReleaseEvent(self, event):
        self._canvas.mouseReleaseEvent(event)

    def paintEvent(self, event):
        if self.timeLapseViewer.getFilename() is not None:
            self._canvas.paintEvent(event)

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    def sizeHint(self):
        return self._canvas.sizeHint()
     
    def splitAnnotations(self, annotations):
        """
        Creates a multilevel dictionary organizing the annotations.  
        The first level is a dictionary mapping individuals; 
        the second level is a dictionary mapping behaviors to a list of annotations for that individual. 
        """
        indivDict = {}
        # first, map the individuals to list of annotations
        for item in annotations:
            if item.individual not in indivDict:
                indivDict[item.individual] = []
            indivDict[item.individual].append(item)
        # second, map the list of annotations using their behaviors
        dict = {}
        for id, annots in indivDict.items():
            behaviors = {}
            for item in annots:
                if item.behavior not in behaviors:
                    behaviors[item.behavior] = []
                behaviors[item.behavior].append(item)   
            dict[id] = behaviors             
        return dict    


class TimeLineCanvas(QtWidgets.QWidget):
    """
    This is the widget where timelines are actually drawn.
    """
    def __init__(self, parentTimeLine):
        super().__init__(parentTimeLine)
        # initialize instance variables
        self.blockHeights = {}              # dictionary mapping animal ID to block height (in pixels)
        self.currentTimelines = {}          # dictionary mapping the y start coordinates to animal ID of drawn timelines
        self._font = QtGui.QFont("Arial", 8) # font used to display ID text
        self._fontHeight = None             # capHeight of font 
        self._leftEdge = 10                 # left edge of timelines; should line up with left edge of video frame slider
        self._lineHeight = 4                # height of each timeline, in pixels
        self._lineSpacing = 2               # height of space between timelines, in pixels
        self._parent = parentTimeLine       # the TimeLineDisplay object this widget is a part of
        self.visibleTimelines = 10          # the number of timelines that should be visible 
        self._timelineHeight = self._lineSpacing + self._lineHeight     # total height of a timeline
        # initialization actions
        # self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)  
        self._textHeight = QtGui.QFontMetrics(self._font).capHeight()

    def calculateBlockHeights(self):
        """
        Calculates the height of each timeline block (i.e., the region of the timeline display
        associated with an individual).
        Returns the total height needed for all blocks.  
        As a side effect, sets the self.blockHeights variable.
        """
        self.blockHeights.clear()
        total = 0
        for id in self._parent.IDs:
            behaviors = self._parent.indivDict[id]
            # compute height of block
            animalHeight = len(behaviors) * self._timelineHeight - self._lineSpacing
            if animalHeight < self._textHeight:
                animalHeight = self._textHeight
            # add in spacing around block
            animalHeight += 2 * self._timelineHeight

            self.blockHeights[id] = animalHeight
            total += animalHeight
        return total

    def mouseReleaseEvent(self, event):
        """
        Looks for a timeline event under the mouse location, and if found, 
        tells the annotatorApp to go to that event.
        """
        y = event.pos().y()
        x = event.pos().x()
        # compensate for the fact that mouse click is in parent widget's coordinate space
        y -= self.pos().y()
        x -= self.pos().x()
        # determine if click was on a timeline
        for key in self.currentTimelines.keys():
            if (key <= y) and (y <= key + self._lineHeight):
                # mouse click was on a timeline
                # translate from X pixel location to video frame index
                pixelsPerFrame = self._parent.timeLapseViewer.getFrameSliderWidth() / self._parent.timeLapseViewer.getFrameCount()
                framesPerPixel = math.ceil(1.0 / pixelsPerFrame)
                frame = int((x - self._leftEdge) / pixelsPerFrame)
                # search for the event spanning the frame
                id, behavior = self.currentTimelines[key]                
                event = self._parent._annotations.findSpanningEvent(frame, id, behavior, framesPerPixel)
                if event is not None:
                    self._parent.app.gotoEvent(event.startFrame-1, event.behavior, event.individual, event.kind)
                    self._parent.app._annotTable.selectMatchingRow(event.startFrame-1, event.behavior, event.individual, event.kind)
                    break

    def paintEvent(self, event):
        # the timeline is the same width as the video frame slider, so they have the
        # same horizontal scaling
        tlWidth = self._parent.timeLapseViewer.getFrameSliderWidth()
        lastFrame = self._parent.timeLapseViewer.getFrameCount()
        # number of pixels per video frame; use this to scale annotation widths
        pixelsPerFrame = tlWidth / lastFrame
        # any text (such as animal IDs) should be placed to right of timeline
        idStart = self._leftEdge + tlWidth + 3     
        # reset the currentTimelines dictionary
        self.currentTimelines.clear()   

        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setFont(self._font)

        # grey pen for timeline background
        penBackground = QtGui.QPen(QtGui.QColor(200,200,200))
        penBackground.setWidth(1)
        brushBackground = QtGui.QBrush(QtGui.QColor(200,200,200))

        # get index of starting individual to graph
        i = self._parent.verticalScrollBar().value()
        if (i == -1):
            i = 0

        countOfIndividualsDisplayed = 0
        y = 0
        while ((countOfIndividualsDisplayed == 0) or (y < self.height())) and (i < len(self._parent.IDs)):
            individual = self._parent.IDs[i]
            if ((self._parent.app.app_config.countOnly and ((individual == "AI_count") or (individual == "count"))) or 
                (self._parent.app.app_config.showAnimalDetection and (individual == "AI_count")) or
                # AI_count and human are special individuals that should not be displayed unless countOnly or showAnimalDetection is True 
                ((not self._parent.app.app_config.countOnly) and (individual != "AI_count"))):  

                # stop drawing if the entire block for this individual cannot be drawn in widget 
                if (y + self.blockHeights[individual]) > self.height():
                    break

                # display the block for the individual
                countOfIndividualsDisplayed += 1  
                behaviors = self._parent.indivDict[individual]

                y += self._timelineHeight
                # center the ID vertically wrt animal's timelines
                animalHeight = len(behaviors) * self._timelineHeight - self._lineSpacing
                if animalHeight < self._textHeight:
                    yText = y + self._textHeight
                    y += (self._textHeight - animalHeight) // 2
                else:
                    yText = y + (animalHeight + self._textHeight) // 2
                qp.setPen(QtCore.Qt.black)                
                qp.drawText(idStart, yText, " " + individual.upper()) 

                # draw timelines for each behavior 
                keys = sorted(list(behaviors.keys()))
                b = 0
                while (b < len(keys)) and (y < self.height()):
                    # add entry to self.currentTimelines dictionary
                    self.currentTimelines[y] = (individual, keys[b])

                    # draw background of timeline
                    qp.setPen(penBackground)
                    qp.setBrush(brushBackground)
                    qp.drawRect(self._leftEdge, y, tlWidth, self._lineHeight)
    
                    # draw the annotations
                    for index, annot in enumerate(behaviors[keys[b]]):
                        if index == 0:
                            # create a pen of the right color for this behavior
                            if annot.kind == 'focal':
                                if annot.behavior in self._parent.app.focalBehaviors:
                                    color = self._parent.app.focalBehaviors[annot.behavior]['color']
                                else:
                                    color = "white"
                            elif annot.kind == 'commensal':
                                if annot.behavior in self._parent.app.commensalBehaviors:
                                    color = self._parent.app.commensalBehaviors[annot.behavior]['color']
                                else:
                                    color = "white"
                            elif annot.kind == "count":
                                if annot.behavior in self._parent.app.countBehaviors:
                                    color = self._parent.app.countBehaviors[annot.behavior]['color']
                                else:
                                    color = "white"     
                            elif annot.kind == "AI_count":
                                if annot.behavior in self._parent.app.countBehaviors:
                                    color = self._parent.app.countBehaviors[annot.behavior]['color']
                                else:
                                    color = "white"                                                        
                            annotPen = QtGui.QPen(QtGui.QColor(color))
                            annotPen.setWidth(1)
                            qp.setPen(annotPen)  
                            qp.setBrush(QtGui.QBrush(QtGui.QColor(color)))

                        xStart = self._leftEdge + annot.startFrame * pixelsPerFrame
                        if annot.endFrame is not None:
                            # draw a line segment 
                            qp.drawRect(xStart, y, (annot.endFrame - annot.startFrame) * pixelsPerFrame, self._lineHeight)                   
                        else:
                            # draw a circle
                            qp.drawEllipse(xStart, y, self._lineHeight, self._lineHeight)                          
                    b += 1
                    y += self._timelineHeight

                # ensure there is enough room for ID text
                if y < yText:
                    y = yText
                # create space between individuals
                y += self._timelineHeight

            i += 1
        qp.end()

        # adjust the vertical scroll bar to reflect the number
        # of individuals being displayed.
        self._parent.verticalScrollBar().setPageStep(countOfIndividualsDisplayed)
        self._parent.verticalScrollBar().setMaximum(len(self._parent.IDs)-countOfIndividualsDisplayed)

    def sizeHint(self):
        return QtCore.QSize(self._parent.timeLapseViewer.image.width(), 
                            (self._lineHeight + self._lineSpacing) * self.visibleTimelines + 2 * self._lineSpacing)   

    def update(self):
        self.repaint()



            
