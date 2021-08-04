"""
Simple test for building a new application on top of the TLV_ApplicationWindow class.
Mike Hilton, Eckerd College
"""
from PySide2 import QtCore, QtGui, QtWidgets
import sys
from TlvAppWindow import TLV_ApplicationWindow

class TestApp(TLV_ApplicationWindow):
    def __init__(self):
        super().__init__()
        self.setAppTitle("Test App")
        self.setWindowTitle(self.getAppTitle())          
        self._addMyMenus()
        self._addMyWidgets()
        # test out all the available callback functions 
        self.setDrawCallback(self._drawCallback)
        self.setImageClickCallback(self._clickCallback)
        self.setFrameChangeCallback(self._frameCallback)

    def _addMyMenus(self):
        """
        Add a new menu to the app
        """
        bar = self.menuBar()
        appMenu = bar.addMenu("Test")
        appAction = appMenu.addAction("Action")
        appAction.triggered.connect(self._menuAction) 

    def _addMyWidgets(self):
        """
        Add a new widget to the app.
        """
        layout = self.getCentralLayout()
        # create a checkbox
        chk = QtWidgets.QCheckBox("This is a checkbox")
        layout.addWidget(chk)
        # add a label showing the current frame index
        self._frameLabel = QtWidgets.QLabel("Current Frame: ")
        layout.addWidget(self._frameLabel)
        # add a label showing the location of the latest mouse click
        self._mouseLabel = QtWidgets.QLabel("Most recent mouse click on image was at location: None")
        layout.addWidget(self._mouseLabel)

    def _clickCallback(self, point):
        """
        Callback function that updates the mouse click label.
        """
        self._mouseLabel.setText(f"Most recent mouse click on image was at location: ({point.x()}, {point.y()})")

    def _drawCallback(self, painter):
        """
        Callback function that is executed every time the time-lapse viewing widget's image changes.
        This function draws a red circle on the last location where the mouse was clicked on the image.
        """      
        cursor = self.imageClick()  
        if cursor is not None:
            painter.setPen(QtGui.QColor(255, 0, 0))
            painter.setBrush(QtGui.QColor(255, 0, 0))
            painter.drawEllipse(QtCore.QPoint(cursor.x(), cursor.y()), 10, 10)
   

    def _frameCallback(self, index):
        """
        Callback function that is executed every time the image frame changes.
        This function updates the frame index label.
        """
        self._frameLabel.setText(f"Current frame: {index}")

    def _menuAction(self):
        QtWidgets.QMessageBox.information(self, "Action", "The Action menu item was selected.", QtWidgets.QMessageBox.StandardButton.Ok)


if __name__ == "__main__":
    
    qapp = QtWidgets.QApplication(sys.argv)
    app = TestApp()

    # install a handler to kill the app when ^-C is typed in command window
    app.setup_interrupt_handling()

    app.show()
    qapp.exec_()