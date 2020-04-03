# coding=utf-8
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QCheckBox

from libs.Utiles import LeerIni


class CheckBox(QCheckBox):

    def __init__(self, parent=None, *args, **kwargs):
        #QCheckBox.__init__(parent)
        QCheckBox.__init__(self, *args)
        font = QFont()
        font.setPointSizeF(12)
        self.setFont(font)
        if 'texto' in kwargs:
            self.setText(kwargs['texto'])
        if 'checked' in kwargs:
            self.setChecked(kwargs['checked'])

    def text(self):
        if LeerIni('base') == 'mysql':
            if self.isChecked():
                return b'\01'
            else:
                return b'\00'
        else:
            if self.isChecked():
                return True
            else:
                return False
