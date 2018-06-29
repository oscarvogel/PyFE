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

#Vista base del cual derivan todos las vistas del sistema

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from libs.Formulario import Formulario
from libs.Utiles import icono_sistema


class VistaBase(Formulario):

    LanzarExcepciones = False

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self)
        self.setWindowIcon(icono_sistema())

    def initUi(self):
        pass

    def cerrarformulario(self):
        self.close()

    def ConectarWidgets(self):
        pass