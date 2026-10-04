# coding=utf-8
import os


from controladores.ControladorBase import ControladorBase
from controladores.EnvioEmail import EnvioEmailController
from controladores.Facturas import FacturaController
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.Emailcliente import EmailCliente
from modelos.Tipocomprobantes import TipoComprobante
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
        self.view.btnCargar.clicked.connect(self.CargaFacturasCliente)

    def CargaFacturasCliente(self):
        self.view.gridDatos.setRowCount(0)
        condiciones = [Cabfact.fecha >= self.view.controles['fecha'].date().toPyDate()]
        cliente = self.view.controles['cliente'].text().strip()
        if cliente:
            condiciones.append(Cabfact.cliente == cliente)
        cab = Cabfact().select(Cabfact, TipoComprobante, Cliente)\
            .join(TipoComprobante, on=(Cabfact.tipocomp == TipoComprobante.codigo))\
            .join(Cliente, on=(Cabfact.cliente == Cliente.idcliente))\
            .where(*condiciones).order_by(Cabfact.fecha.desc())
        for c in cab:
            if c.tipocomp.exporta:
                item = [
                    c.fecha, c.cliente.nombre, c.numero, c.total,
                    c.idcabfact, c.cliente.idcliente
                ]
                self.view.gridDatos.AgregaItem(items=item)

    def ImprimirFactura(self):
        if self.view.gridDatos.currentRow() != -1:
            FacturaController().ImprimeFactura(self.view.gridDatos.ObtenerItem(
                fila=self.view.gridDatos.currentRow(), col='idcabecera'))

    @inicializar_y_capturar_excepciones
    def EnviarPorCorreo(self, *args, **kwargs):
        fila = self.view.gridDatos.currentRow()
        if fila == -1:
            return
        # El destinatario sale de la fila elegida y no del campo de arriba: la
        # pantalla lista las comprobantes de todos los clientes del periodo y
        # ese campo puede estar vacio, en cuyo caso antes no encontraba ni los
        # mail ni el cliente del comprobante.
        idcliente = self.view.gridDatos.ObtenerItem(fila=fila, col='idcliente')
        if not idcliente:
            return
        factura = FacturaController()
        factura.ImprimeFactura(self.view.gridDatos.ObtenerItem(
            fila=fila, col='idcabecera'),
        mostrar=False)
        emaicliente = EmailCliente.select().where(EmailCliente.idcliente == idcliente)
        controlador = EnvioEmailController()
        controlador.adjuntos = []
        # controlador.archivo_firma = "prueba.html"
        controlador.adjuntos = factura.facturaGenerada
        controlador.ActualizaListaAdjuntos()
        controlador.cliente = idcliente
        controlador.view.textAsunto.setText(
            f'Envio comprobante {os.path.basename(factura.facturaGenerada)}'
        )
        controlador.view.textPara.setText(
            ','.join(e.email for e in emaicliente)
        )
        controlador.exec_()
            # emaicliente = EmailCliente.select().where(EmailCliente.idcliente == self.view.controles['cliente'].text())
            # items = []
            # for e in emaicliente:
            #     items.append(e.email)
            # if items:
            #     text, ok = QInputDialog.getItem(self.view, 'Sistema', 'Ingrese el mail destinatario:', items)
            # else:
            #     text, ok = QInputDialog.getText(self.view, 'Sistema', 'Ingrese el mail destinatario:')
            # if ok:
            #     destinatario = str(text).strip()
            #     mensaje = "Enviado desde {}. {}\nNo responder este email".format(
            #               Constantes.NOMBRE_PRODUCTO, Constantes.CREDITO_SOFTWARE)
            #     archivo = factura.facturaGenerada
            #     motivo = "Se envia comprobante electronico de {}".format(LeerIni(clave='empresa', key='FACTURA'))
            #     servidor = ParamSist.ObtenerParametro("SERVER_SMTP")
            #     clave = ParamSist.ObtenerParametro("CLAVE_SMTP")
            #     usuario = ParamSist.ObtenerParametro("USUARIO_SMTP")
            #     puerto = ParamSist.ObtenerParametro("PUERTO_SMTP") or 587
            #     responder=ParamSist.ObtenerParametro("RESPONDER")
            #     ok, err_msg = envia_correo(from_address=responder, to_address=destinatario, message=mensaje, subject=motivo,
            #                  password_email=clave, smtp_port=puerto, smtp_server=servidor, files=archivo)
            #     if not ok:
            #         Ventanas.showAlert("Sistema", "Ha ocurrido un error al enviar el correo\n{}".format(err_msg))
            #     else:
            #         Ventanas.showAlert("Sistema", "Comprobante electrónico enviado correctamente")

