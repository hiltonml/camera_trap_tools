"""
Label subclass that always displays its image with the proper aspect ratio
Mike Hilton, Eckerd College


setClickCallback(self, function) can be used to assign a callback function 
that runs when a mouse release event occurs.  The function should take a single
argument of type QPoint indicating the mouse location.

setDrawFunction(self, function) can be used to assign a callback function for
drawing on the label when a paint event occurs.  The function should take a 
single argument of type QPainter.

"""

from PySide2 import QtCore, QtGui, QtWidgets

class ScaledLabel(QtWidgets.QLabel):
    """Resizable Label class that always displays its image with the proper aspect ratio"""
    def __init__(self):
        super().__init__()
        self._clickCallback = None  # an optional client function called after mouse clicks on the pixmap
        self._drawFunction = None   # an optional client function to draw objects on the pixmap
        self._imageClick = None     # location (in image coordinates) of the most recent mouse click on the image
        self._pixmap = None         # pixmap displayed on label
        self._pixmapRect = None     # rectangle pixmap is displayed in
        self._scaleX = None         # X-dimension scaling of pixmap
        self._scaleY = None         # Y-dimension scaling of pixmap

    def clearImageClick(self):
        """Sets the image click point to None"""
        self._imageClick = None
        self.repaint()

    def getImageClick(self):
        """Returns the point of the most recent mouse click on the image, in image coordinates"""
        return self._imageClick
        
    def setClickCallback(self, function):
        """Sets the client callback function for the click event on the image"""
        self._clickCallback = function

    def setDrawFunction(self, function):
        """Sets the function for drawing on the label.  The function must take 1 argument,
        the painter to be used for drawing
        """
        self._drawFunction = function

    def setPixmap(self, pix):
        self._pixmap = pix
        self.repaint()

    def paintEvent(self, event):
        if self._pixmap is not None:
            if self._drawFunction is not None:
                # draw on a copy of the pixmap 
                pm = self._pixmap.copy() 
                pixPainter = QtGui.QPainter(pm)              
                func = self._drawFunction
                func(pixPainter)
                pixPainter.end()
            else:
                pm = self._pixmap
            # draw a scaled version of pixmap onto the label
            size = self.size()
            painter = QtGui.QPainter(self)
            point = QtCore.QPoint(0,0)
            scaledPix = pm.scaled(size, QtCore.Qt.KeepAspectRatio, transformMode = QtCore.Qt.SmoothTransformation)
            point.setX((size.width() - scaledPix.width())/2)
            point.setY((size.height() - scaledPix.height())/2)
            painter.drawPixmap(point, scaledPix)  
            # information needed by mouseReleaseEvents()
            self._pixmapRect = QtCore.QRect(point.x(), point.y(), scaledPix.width(), scaledPix.height())
            self._scaleX = pm.width() / scaledPix.width()
            self._scaleY = pm.height() / scaledPix.height()


    def mouseReleaseEvent(self, event):
        """If the mouse click was on the image, records the click location in image coordinates"""
        if self._pixmapRect is not None and self._pixmapRect.contains(event.pos()): 
            self._imageClick = QtCore.QPoint(
                (event.pos().x() - self._pixmapRect.left()) * self._scaleX,
                (event.pos().y() - self._pixmapRect.top()) * self._scaleY
                )
            if self._clickCallback is not None:
                func = self._clickCallback
                func(self._imageClick)
            self.repaint()              

