# coding=utf-8
from PyQt5.QtWidgets import QInputDialog

from controladores.ControladorBase import ControladorBase
from controladores.Facturas import FacturaController
from libs import Ventanas
from libs.Utiles import inicializar_y_capturar_excepciones, LeerIni, envia_correo
from modelos.Cabfact import Cabfact
from modelos.Emailcliente import EmailCliente
from modelos.ParametrosSistema import ParamSist
from vistas.ReImprimeFactura import ReImprimeFacturaView


class ReImprimeFacturaController(ControladorBase):

    def __init__(self):
        super(ReImprimeFacturaController, self).__init__()
        self.view = ReImprimeFacturaView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaFacturasCliente)
        self.view.btnImprimir.clicked.connect(self.ImprimirFactura)
        self.view.envioCorreo.clicked.connect(self.EnviarPorCorreo)

    def CargaFacturasCliente(self):
        self.view.gridDatos.setRowCount(0)
        if not self.view.controles['cliente'].text():
            return
        cab = Cabfact().select().where(Cabfact.fecha >= self.view.controles['fecha'].date().toPyDate(),
                                       Cabfact.cliente == self.view.controles['cliente'].text())
        for c in cab:
            if c.tipocomp.exporta:
                item = [
                    c.fecha, c.numero, c.total, c.idcabfact
                ]
                self.view.gridDatos.AgregaItem(items=item)

    def ImprimirFactura(self):
        if self.view.gridDatos.currentRow() != -1:
            FacturaController().ImprimeFactura(self.view.gridDatos.ObtenerItem(
                fila=self.view.gridDatos.currentRow(), col='idcabecera'))

    @inicializar_y_capturar_excepciones
    def EnviarPorCorreo(self, *args, **kwargs):
        if self.view.gridDatos.currentRow() != -1:
            factura = FacturaController()
            factura.ImprimeFactura(self.view.gridDatos.ObtenerItem(
                fila=self.view.gridDatos.currentRow(), col='idcabecera'),
            mostrar=False)
            emaicliente = EmailCliente.select().where(EmailCliente.idcliente == self.view.controles['cliente'].text())
            items = []
            for e in emaicliente:
                items.append(e.email)
            if items:
                text, ok = QInputDialog.getItem(self.view, 'Sistema', 'Ingrese el mail destinatario:', items)
            else:
                text, ok = QInputDialog.getText(self.view, 'Sistema', 'Ingrese el mail destinatario:')
            if ok:
                destinatario = str(text).strip()
                mensaje = "Enviado desde mi Software de Gestion desarrollado por http://www.servinlgsm.com.ar \n" \
                          "No responder este email"
                archivo = factura.facturaGenerada
                motivo = "Se envia comprobante electronico de {}".format(LeerIni(clave='empresa', key='FACTURA'))
                servidor = ParamSist.ObtenerParametro("SERVER_SMTP")
                clave = ParamSist.ObtenerParametro("CLAVE_SMTP")
                usuario = ParamSist.ObtenerParametro("USUARIO_SMTP")
                puerto = ParamSist.ObtenerParametro("PUERTO_SMTP") or 587
                responder=ParamSist.ObtenerParametro("RESPONDER")
                ok, err_msg = envia_correo(from_address=responder, to_address=destinatario, message=mensaje, subject=motivo,
                             password_email=clave, smtp_port=puerto, smtp_server=servidor, files=archivo)
                if not ok:
                    Ventanas.showAlert("Sistema", "Ha ocurrido un error al enviar el correo\n{}".format(err_msg))
                else:
                    Ventanas.showAlert("Sistema", "Comprobante electronico enviado correctamente")

