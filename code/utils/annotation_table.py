"""
Table view of annotations
Mike Hilton and Mark Yamane, Eckerd College
"""

from PySide2 import QtWidgets
from PySide2.QtWidgets import QTableWidget


class AnnotationTable(QTableWidget):
    def __init__(self, parent, annotations):
        super().__init__(parent)
        # initialize instance variables
        self._annotations = annotations
        self._client = parent
        self._filling = False               # used to suppress itemChanged action
        # add header row to table
        self.setColumnCount(5)
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(['Start', 'End', 'Behavior', 'ID', 'Kind'])
        self.hideColumn(4)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.resizeColumnsToContents()
        self.itemChanged.connect(self.itemChangedHandler)

    def fillTable(self):
        """
        Clears the table and then fills it with data from self._annotations
        """
        self._filling = True
        self.clear()
        self.setHorizontalHeaderLabels(['Start', 'End', 'Behavior', 'ID', 'Kind'])
        self.setSortingEnabled(False)
        self.setRowCount(len(self._annotations))
        i = 0
        for annotation in self._annotations:   
            if ((self._client.app_config.countOnly and (annotation.getIndividual() == "count")) or 
                ((not self._client.app_config.countOnly) and (annotation.getIndividual() != "AI_count") and (annotation.getIndividual() != "count")) or
                (annotation.getBehavior() in self._client.focalBehaviors) or
                (annotation.getBehavior() in self._client.commensalBehaviors)):               
                self.insertRow(i)
                self.setItem(i, 0, QtWidgets.QTableWidgetItem(str(annotation.startFrame)))
                end = "" if annotation.endFrame is None else str(annotation.endFrame)
                self.setItem(i, 1, QtWidgets.QTableWidgetItem(end))
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(annotation.behavior))            
                self.setItem(i, 3, QtWidgets.QTableWidgetItem(annotation.individual))
                self.setItem(i, 4, QtWidgets.QTableWidgetItem(annotation.kind))
                self.scrollToItem(self.item(i,0))
                i += 1
        self.setRowCount(i)                
        self.resizeColumnsToContents()
        self.setSortingEnabled(True)
        self.horizontalHeader().setVisible(True)
        self._filling = False

    def gotoEvent(self, frame):
        """
        Selects the first row containing either a start or end value matching the 
        specified frame.
        Returns:
            The tuple (frame, behavior, id, kind) of the matching row, or None if
            there is not matching row.
        """
        target = str(frame+1)
        for i in range(self.rowCount()):
            if self.item(i, 0) is not None:
                # extract fields from the table row
                startFrame = self.item(i, 0).text()
                endFrame = self.item(i, 1).text()
                if (target == startFrame) or (target == endFrame):
                    self.scrollToItem(self.item(i, 0))
                    self.selectRow(i)
                    return (frame, self.item(i, 2).text(), self.item(i, 3).text(), self.item(i, 4).text())
        return None

    def itemChangedHandler(self, item):
        """
        This method is run when an item is changed.  If the new value is legal,
        the annotation is modified to contain the new item.
        """
        if self._filling:
            return

        col = item.column()
        annot = self._annotations[item.row()]
        txt = item.text()

        if (col == 0):
            # start frame
            if (txt != str(annot.startFrame)):
                if not str.isdigit(txt):
                    item.setText(str(annot.startFrame))
                    return
                else:
                    annot.startFrame = int(txt)
                    annot.startTime = self._client.getFrameDateTime(annot.startFrame)
            else:
                return

        elif (col == 1):
            # end frame
            if (txt == ""):
                if annot.endFrame is None:
                    return
                else:
                    annot.endFrame = None
                    annot.endTime = self._client.getFrameDateTime(annot.endFrame)
            elif (txt != str(annot.endFrame)):
                if not str.isdigit(txt):
                    if annot.endFrame is None:
                        item.setText("")  
                    else:                  
                        item.setText(str(annot.endFrame))
                    return
                else:
                    n = int(txt)
                    if (n >= annot.startFrame) and (n <= self._client.getFrameCount()+1):
                        annot.endFrame = int(txt)
                        annot.endTime = self._client.getFrameDateTime(annot.endFrame)
                    else:
                        if annot.endFrame is None:
                            item.setText("")  
                        else:                  
                            item.setText(str(annot.endFrame))
                        return
            else:
                return

        elif (col == 2):
            # activity / behavior
            item.setText(annot.behavior)
            return

        elif (col == 3):
            # individual
            if txt != annot.individual:
                annot.individual = txt
            else:
                return

        self._annotations.modified.emit()




    def selectMatchingRow(self, frame, behavior, id, kind):
        """
        Selects the first row matching all of the provided data.
        Returns:
            The row index if a matching row is found; None, otherwise.
        """
        target = str(frame+1)
        for i in range(self.rowCount()):
            if self.item(i, 0) is not None:
                # extract fields from the table row
                startFrame = self.item(i, 0).text()
                endFrame = self.item(i, 1).text()
                if (((target == startFrame) or (target == endFrame)) and
                    (self.item(i, 2).text() == behavior) and
                    (self.item(i, 3).text() == id) and 
                    (self.item(i, 4).text() == kind)):
                    self.scrollToItem(self.item(i, 0))
                    self.selectRow(i)
                    return i
        return None