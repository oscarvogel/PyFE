from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QMimeData, QByteArray
from PyQt5.QtGui import QIcon, QDrag
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

from libs.Utiles import imagen


class Lista(QListWidget):

    #emit signal
    keyPressed = QtCore.pyqtSignal(int)
    itemDropped = QtCore.pyqtSignal(list)
    itemMoved = QtCore.pyqtSignal(int, int, QListWidgetItem)  # Old index, new    index, item

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(False)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.drag_item = None
        self.drag_row = None

    def AgregaItem(self, item='', backgroundcolor=None, icon=None):

        if not isinstance(item, list):
            item = [item,]

        for x in item:
            item_widget = QListWidgetItem()
            item_widget.setText(x)
            if icon:
                item_widget.setIcon(QIcon(icon))
            self.addItem(item_widget)

    def keyPressEvent(self, event):
        super(Lista, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())

    def BorrarItemSeleccionado(self):
        # for item in self.selectedItems():
        #     self.takeItem(self.row(item))
        self.takeItem(self.currentRow())

    def ObtenerItem(self, fila):
        item = self.item(fila)
        return item.text() if item else None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
                icono = imagen('attach_file.png')
                self.AgregaItem(str(url.toLocalFile()), icon=icono)
            # self.emit(QtCore.SIGNAL("dropped"), links)
            self.itemDropped.emit(links)
        else:
            event.ignore()
