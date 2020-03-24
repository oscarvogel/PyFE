from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QListWidget, QListWidgetItem


class Lista(QListWidget):

    def __init__(self):
        super().__init__()

    def AgregaItem(self, item='', backgroundcolor=None, icon=None):

        if not isinstance(item, list):
            item = [item,]

        for x in item:
            item_widget = QListWidgetItem()
            item_widget.setText(x)
            if icon:
                item_widget.setIcon(QIcon(icon))
            self.addItem(item_widget)
