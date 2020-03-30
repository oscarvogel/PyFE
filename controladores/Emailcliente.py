# coding=utf-8
from controladores.ControladorBase import ControladorBase
from modelos.Emailcliente import EmailCliente
from vistas.Emailcliente import EmailClienteView


class EmailClienteController(ControladorBase):

    model = EmailCliente()
    idcliente = 1
    def __init__(self):
        super(EmailClienteController, self).__init__()
        self.view = EmailClienteView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnAgregar.clicked.connect(self.AgregarEmail)
        self.view.btnGraba.clicked.connect(self.GrabaEmailCliente)
        self.view.btnBorrar.clicked.connect(self.BorraEmailCliente)

    def CargaEmail(self):
        self.view.gridEmail.setRowCount(0)
        data = self.model.select().where(EmailCliente.idcliente == self.idcliente)
        for d in data:
            item = [
                d.email, d.idemailcliente
            ]
            self.view.gridEmail.AgregaItem(items=item)

    def AgregarEmail(self):
        self.view.gridEmail.setRowCount(
            self.view.gridEmail.rowCount() + 1
        )

    def GrabaEmailCliente(self):
        for x in range(self.view.gridEmail.rowCount()):
            email = self.view.gridEmail.ObtenerItem(fila=x, col='EMail')
            id = self.view.gridEmail.ObtenerItemNumerico(fila=x, col='idemailcliente')

            if id:
                emailcliente = EmailCliente.get_by_id(id)
            else:
                emailcliente = EmailCliente()
                emailcliente.idcliente = self.idcliente
            emailcliente.email = email
            emailcliente.save()
        self.view.Cerrar()

    def BorraEmailCliente(self):
        id = self.view.gridEmail.ObtenerItem(
            fila=self.view.gridEmail.currentRow(),
            col='idemailcliente')
        EmailCliente().delete().where(EmailCliente.idemailcliente == id).execute()
        self.CargaEmail()