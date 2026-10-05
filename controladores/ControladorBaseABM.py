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

#Controlador base del cual derivan todos los abm del sistema
from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import inicializar_y_capturar_excepciones
from vistas.ABM import ABM

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"


class ControladorBaseABM(ControladorBase):

    campoclave = None #campo clave para actualizar la tabla, tiene que ser caracter

    # La vista se construye con esta clase, y el subclase la cambia por la
    # suya.
    #
    # Antes el `__init__` de aca hacia `self.view = ABM()` y cada subclase la
    # reemplazaba despues con la suya: se construian DOS ventanas por
    # apertura, y la primera se descartaba al tiro. No rompia la pantalla,
    # pero la descartada era un `ABM` sin columnas, y ahi se caia
    # `Grillas._reparte_anchos` con `anchos[-1]` sobre una lista vacia. Ese
    # IndexError salia en la consola cada vez que se abria Conditions de IVA
    # o Categorias de monotributo, con la ventana funcionando y el operador
    # pensando que se habia roto algo.
    #
    # `_reparte_anchos` tambien se tapo para que una grilla sin columnas no
    # reviente nunca, pero aca no se construye la ventana que no sirve.
    vistaClase = ABM

    def __init__(self):
        super().__init__()
        self.view = self.vistaClase()
        # self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)
        self.view.tableView.doubleClicked.connect(self.onDoubleClikedTableWidget)

    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if not self.model:
            Ventanas.showAlert("Sistema", "Debes establecer un modelo a actualizar")
            return
        if self.campoclave is None:
            Ventanas.showAlert("Sistema", "Debes establecer un campo clave a actualizar")
            return

        if self.view.tipo == 'M':
            dato = self.model.get_by_id(self.view.controles[self.campoclave].text())
        else:
            dato = self.model()

        for control in self.view.controles:
            dato.__data__[control] = self.view.controles[control].text()
        dato.save(force_insert=self.view.tipo == 'A')
        self.view.btnAceptarClicked()

    def onDoubleClikedTableWidget(self, index):
        if self.view.tableView.currentRow() == -1:
            return
        self.view.btnEditar.click()