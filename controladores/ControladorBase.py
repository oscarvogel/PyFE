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

#Controlador base del cual derivan todos los controladores del sistema

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from vistas.VistaBase import VistaBase

class ControladorBase(object):

    view = None #vista asociada
    model = None #modelo asociado
    LanzarExcepciones = False #se usa para controlar los errores

    def __init__(self):
        self.view = VistaBase()

    def run(self):
        self.view.show()

    def conectarWidgets(self):
        pass

    def exec_(self):
        self.view.exec_()

    def CargaDatos(self):
        pass

    def EstablecerOrden(self):
        pass