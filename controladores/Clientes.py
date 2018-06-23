# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.Clientes import ClientesView


class ClientesController(ControladorBase):

    def __init__(self):
        super(ClientesController, self).__init__()
        self.view = ClientesView()
        #self.view.exec_()