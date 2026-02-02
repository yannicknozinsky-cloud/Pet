from PyQt5 import QtWidgets
from desktop_pet import DesktopPet
import sys

app = QtWidgets.QApplication(sys.argv)
pet = DesktopPet()
sys.exit(app.exec_())
