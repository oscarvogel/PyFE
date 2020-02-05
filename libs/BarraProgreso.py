# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
from PyQt5.QtWidgets import QProgressBar


class Avance(QProgressBar):

    def __init__(self, parent=None, *args, **kwargs):
        QProgressBar.__init__(self, parent)
        if 'inicial' in kwargs:
            self.actualizar(kwargs['inicial'])

    def actualizar(self, valor=0):
        self.setValue(valor)
