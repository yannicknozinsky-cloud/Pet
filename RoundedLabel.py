
from PyQt5 import QtCore, QtGui, QtWidgets
class RoundedLabel(QtWidgets.QWidget):
    def __init__(self, text, width=200, colour="black", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.text = text
        self.width_fixed = width

        # Label für den Text
        self.label = QtWidgets.QLabel(self)
        self.label.setText(self.text)
        self.label.setStyleSheet("color: "+colour+";")
        self.label.setWordWrap(True)
        self.label.setFixedWidth(self.width_fixed)
        self.label.adjustSize()

        # Größe des Widgets an Label anpassen plus Padding
        self.setFixedSize(self.label.width() + 20, self.label.height() + 20)
        self.label.move(10, 10)

    def paintEvent(self, event):
        # Hier zeichnen wir die weiße Fläche mit abgerundeten Ecken
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        color = QtGui.QColor(255, 255, 255, 255)  # komplett weiß
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 15, 15)  # Radius 15px
