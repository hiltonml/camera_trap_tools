"""
Timeline Annotation Classes
Mike Hilton and Mark Yamane, Eckerd College

The Annotation class creates objects for easier indexing and printing of annotations
connected to a timeline.

The AnnotationList class implements a collection of Annotation objects.  This collection
is "Qt aware", being a QtCore.QObject and emits a QtSignal whenever it is modified.
"""

from PySide2 import QtCore
from datetime import datetime

class Annotation(object):
    def __init__(self, startFrame, endFrame, behavior, kind, individual, startTime, endTime, user):
        self.startFrame = startFrame        # starting frame index 
        self.endFrame = endFrame            # ending frame index
        self.behavior = str(behavior)       # name of the behavior being annotated
        self.kind = kind                    # what kind of animal is this individual
        self.individual = str(individual)   # ID of individual being annotated
        self.startTime = startTime          # time string associated with start frame, in YYYYMMDD-hhmmss format
        self.endTime = endTime              # time string associated with end frame, in YYYYMMDD-hhmmss format
        self.user = user                    # name of user creating this annotation

    # getters and setters
    def getBehavior(self):
        return self.behavior

    def setBehavior(self, behavior):
        self.behavior = behavior

    def getEndFrame(self):
        return self.endFrame

    def setEndFrame(self, endFrame):
        self.endFrame = endFrame

    def getEndTime(self):
        return self.endTime

    def setEndTime(self, endTime):
        self.endTime = endTime

    def getIndividual(self):
        return self.individual

    def setIndividual(self, individual):
        self.individual = individual

    def getKind(self):
        return self.kind

    def setKind(self, kind):
        self.kind = kind

    def getStartFrame(self):
        return self.startFrame

    def setStartFrame(self, startFrame):
        self.startFrame = startFrame

    def getStartTime(self):
        return self.startTime

    def setStartTime(self, startTime):
        self.startTime = startTime

    def getUser(self):
        return self.user

    def setUser(self, user):
        self.user = user

    # methods
    def asList(self):
        """
        Returns a list of self's instance variable values, as strings.
        """
        if self.startTime is None:  
            startTime = ""
        else:
            startTime = self.startTime.strftime("%Y%m%d-%H%M%S")
        if self.endTime is None: 
            self.endTime = ""
        else:
            endTime = self.endTime.strftime("%Y%m%d-%H%M%S")
        return [str(self.startFrame), str(self.endFrame), self.behavior, self.kind, self.individual, 
                startTime, endTime, self.user]

    def __iter__(self):
        """
        Iterator yielding each instance attribute value
        """
        return iter(self.asList())
   
    def __eq__(self, other):
        if self is other:
            return True
        elif type(self) is not type(other):
            return False
        else:
            return (
                (self.startFrame == other.startFrame) and
                (self.endFrame == other.endFrame) and
                (self.behavior == other.behavior) and
                (self.kind == other.kind) and
                (self.individual == other.individual) 
            )                

    def __neq__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if type(self) is not type(other):
            raise TypeError(f"Cannot compare objects of types {type(self).__name__} and {type(other).__name__}")
        elif self.startFrame is None or other.startFrame is None:
            if self.startTime is not None and other.startTime is not None:
                return self.startTime < other.startTime
            return True
        elif self.startFrame < other.startFrame:
            return True
        elif self.startFrame > other.startFrame:
            return False
        else:
            endS = self.startFrame if self.endFrame is None else self.endFrame
            endO = other.startFrame if other.endFrame is None else other.endFrame
            return endS < endO

    def __le__(self, other):
        if type(self) is not type(other):
            raise TypeError(f"Cannot compare objects of types {type(self).__name__} and {type(other).__name__}")
        elif self.startFrame < other.startFrame:
            return True
        elif self.startFrame > other.startFrame:
            return False
        else:
            endS = self.startFrame if self.endFrame is None else self.endFrame
            endO = other.startFrame if other.endFrame is None else other.endFrame
            return endS <= endO
    
    def __gt__(self, other):
        if type(self) is not type(other):
            raise TypeError(f"Cannot compare objects of types {type(self).__name__} and {type(other).__name__}")
        elif self.startFrame > other.startFrame:
            return True
        elif self.startFrame < other.startFrame:
            return False
        else:
            endS = self.startFrame if self.endFrame is None else self.endFrame
            endO = other.startFrame if other.endFrame is None else other.endFrame
            return endS > endO

    def __ge__(self, other):
        if type(self) is not type(other):
            raise TypeError(f"Cannot compare objects of types {type(self).__name__} and {type(other).__name__}")
        elif self.startFrame > other.startFrame:
            return True
        elif self.startFrame < other.startFrame:
            return False
        else:
            endS = self.startFrame if self.endFrame is None else self.endFrame
            endO = other.startFrame if other.endFrame is None else other.endFrame
            return endS >= endO

    def fromString(s):
        """
        Factory method for creating an Annotation object from a string representation.
        """
        parts = s.strip().split(",")
        if len(parts) == 8:
            # this is an old format file, and we should remove the first two items
            parts.pop(0)
            parts.pop(0)

        if parts[4].strip() == "None":
            endTime = None
        else:
            endTime = datetime.strptime(parts[4].strip(), '%Y%m%d-%H%M%S')

        return Annotation(None, None,
                          parts[0].strip(), parts[1].strip(), parts[2].strip(), 
                          datetime.strptime(parts[3].strip(), '%Y%m%d-%H%M%S'), endTime, parts[5].strip()
                          )

    def __repr__(self):
        return "<Annotation " + ", ".join(self.asList()) + " >"

    def __str__(self):
        return ", ".join(self.asList())



class AnnotationList(QtCore.QObject):
    modified = QtCore.Signal()

    def __init__(self):
        super().__init__()        
        self._annotations = []          # concrete implementation of collection
        self._debug = False              # if True, debugging statements are printed by various methods
        self._suppressSignals = False   # if True, modified signals not emitted

    def add(self, annotation):
        """
        Adds annotation to self, if it is not already in self.  The annotation list
        is always kept sorted by start frame.
        """
        if annotation not in self._annotations:
            # find the location where the new annotation belongs
            if len(self._annotations) == 0:
                self._annotations.append(annotation)
            else:
                inserted = False
                for i in range(len(self._annotations)):
                    if annotation < self._annotations[i]:
                        self._annotations.insert(i, annotation)
                        inserted = True
                        break
                if not inserted:
                    self._annotations.append(annotation)                

            if self._debug:
                print(annotation,'added')
            if not self._suppressSignals:
                self.modified.emit()
        elif self._debug:
            print(annotation, 'already present')

    def clear(self):
        self._annotations.clear()
        if self._debug:
            print('clear annotations')   
        if not self._suppressSignals:                 
            self.modified.emit()

    def eventFrames(self, excludeAI=False):
        """
        Returns a sorted list of the start and end frames in self.
        """
        frames = []
        for annot in self:
            if excludeAI and annot.kind == "AI_count":
                continue
            if annot.startFrame not in frames:
                frames.append(annot.startFrame-1)
            if (annot.endFrame is not None) and (annot.endFrame not in frames):
                frames.append(annot.endFrame-1)
        frames.sort()
        return frames

    def findNextEvent(self, timept, kind, ids, activities):
        """
        Returns the index of the next event that starts after timept, it any.
        """
        txtIds = list(map(lambda x: x[1], ids))
        for i in range(len(self._annotations)):
            if ((timept < self[i].startFrame) and
                (self[i].kind == kind) and
                (self[i].individual in txtIds) and
                (self[i].behavior in activities)):            
                return i
        return None

    def findSpanning(self, timept, kind, ids, activities):
        """
        Returns a list of indices for annotations that span the specified time point
        and have the right kind, ID, and activity.
        Inputs:
            timept          int; video frame index
            kind            string; category of animal
            ids             list of pairs (item, textId); id info for individuals to find
            activities      list of string; activities to find
        """ 
        answer = []
        txtIds = list(map(lambda x: x[1], ids))
        if (len(ids) > 0) and (len(activities) > 0):
            for i, item in enumerate(self._annotations):
                if ((item.startFrame <= timept) and 
                    (item.kind == kind) and
                    (item.individual in txtIds) and
                    (item.behavior in activities)
                    ):
                    if (item.endFrame is None):
                        if (item.startFrame == timept):
                            answer.append(i)
                    elif (timept <= item.endFrame):
                        answer.append(i)                            
        return answer

    def findSpanningEvent(self, timept, id=None, activity=None, tolerance=0):
        """
        Returns the annotation that spans the specified time point
        for the specified individual and activity.  If no such annotation
        is found, None is returned.
        """ 
        for _, item in enumerate(self._annotations):
            if ((item.startFrame - tolerance <= timept) and 
                (id is None or (item.individual == id)) and
                (activity is None or (item.behavior == activity))
                ):
                if (item.endFrame is None):
                    if (timept <= item.startFrame + tolerance):
                        return item
                elif (timept <= item.endFrame + tolerance):
                    return item
        return None

    def pop(self, index):
        """
        Removes the specified item from the annotation list.
        Returns the item.
        """
        item = self._annotations[index]
        self._annotations.pop(index)
        if self._debug: 
            print(item, 'pop')
        if not self._suppressSignals:
            self.modified.emit()
    
    def print(self, header=None):
        """
        Prints self to console, one Annotation per line.
        """
        if header is not None:
            print(header)
        for item in self._annotations:
            print(item)

    def readFromFile(self, filename, imageSequence):
        """
        Reads the annotations in the specified file, and adds them to
        the existing annotations.  While reading, the 'modified' signal
        is suppressed, and a single signal is emitted when reading has
        completed.
        """
        with open(filename, "r") as inFile:
            self._suppressSignals = True            
            for aLine in inFile:
                if len(aLine.strip()) > 0:
                    annot = Annotation.fromString(aLine)
                    if imageSequence is not None:
                        annot.setStartFrame(imageSequence.frameAtTime(annot.startTime)+1)
                        if annot.endTime is not None:
                            annot.setEndFrame(imageSequence.frameAtTime(annot.endTime)+1)
                    self.add(annot)
        self._suppressSignals = False
        self.modified.emit()

    def setEndFrame(self, index, frame, frameTime):
        """
        Sets the end frame for the annotation specified by index.
        """
        self._annotations[index].endFrame = frame
        self._annotations[index].endTime = frameTime
        self._annotations.sort()
        if self._debug:        
            print(self._annotations[index], 'setEndFrame')
        if not self._suppressSignals:
            self.modified.emit()

    def setStartFrame(self, index, frame, frameTime):
        """
        Sets the start frame for the annotation specified by index.
        """
        self._annotations[index].startFrame = frame
        self._annotations[index].startTime = frameTime       
        self._annotations.sort()
        if self._debug:        
            print(self._annotations[index], 'setStartFrame')
        if not self._suppressSignals:
            self.modified.emit()                        

    def writeToFile(self, filename):
        """
        Writes self to a text file, one annotation per line.
        """
        with open(filename, "w") as outFile:
            for item in self:
                startTime = item.startTime.strftime("%Y%m%d-%H%M%S")
                if item.endTime is None:
                    endTime = "None"
                else:
                    endTime = item.endTime.strftime("%Y%m%d-%H%M%S")
                outFile.write(f"{item.behavior}, {item.kind}, {item.individual}, {startTime}, {endTime}, {item.user}\n")
    
    def __getitem__(self, index):
        return self._annotations[index]

    def __iter__(self):
        return iter(self._annotations)

    def __len__(self):
        return len(self._annotations)

    def __setitem__(self, index, newItem):
        self._annotations[index] = newItem
        if not self._suppressSignals:
            self.modified.emit()

    def __str__(self):
        result = ""
        for indiv in self._annotations:
            result += str(indiv) + "\n"
        return result        