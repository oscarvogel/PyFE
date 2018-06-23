# coding=utf-8
from PyQt4.QtGui import QCheckBox, QFont


class CheckBox(QCheckBox):

    def __init__(self, parent=None, *args, **kwargs):
        #QCheckBox.__init__(parent)
        QCheckBox.__init__(self, *args)
        font = QFont()
        font.setPointSizeF(12)
        self.setFont(font)
        if 'texto' in kwargs:
            self.setText(kwargs['texto'])

    def text(self):
        if self.isChecked():
            return b'\01'
        else:
            return b'\00'
