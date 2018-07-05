# coding=utf-8
from vistas.VistaBase import VistaBase


class CtaCteView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("")