# coding=utf-8
from controladores.ControladorBase import ControladorBase
from controladores.Emailcliente import EmailClienteController
from vistas.Clientes import ClientesView


class ClientesController(ControladorBase):

    def __init__(self):
        super(ClientesController, self).__init__()
        self.view = ClientesView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnEmail.clicked.connect(self.CargaEmailCliente)
        self.view.controles['dni'].editingFinished.connect(self.onDNIEditingFinished)

    def CargaEmailCliente(self):
        controllerEmail = EmailClienteController()
        controllerEmail.idcliente = self.view.tableView.ObtenerItem(
            fila=self.view.tableView.currentRow(), col=0
        )
        controllerEmail.CargaEmail()
        controllerEmail.exec_()

    def onDNIEditingFinished(self):
        if not self.view.controles['dni'].text():
            self.view.controles['dni'].setText('0')
        if not self.view.controles['tipodocu'].text():
            self.view.controles['tipodocu'].setText('0')