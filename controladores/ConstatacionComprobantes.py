# coding=utf-8
import os
from datetime import datetime

from fpdf import FPDF

from controladores.ControladorBase import ControladorBase
from controladores.PadronAfip import PadronAfip
from controladores.WSConstComp import WSConstComp
from libs.Utiles import FechaMysql, AbrirArchivo, imagen, LeerIni
from modelos.Tipocomprobantes import TipoComprobante
from vistas.ConstatacionComprobantes import ConstatacionComprobanteView


class ConstatacionComprobantesController(ControladorBase):
    cbte_modo = ''  # modalidad de emision: CAI, CAE, CAEA
    cuit_emisor = ''  # proveedor
    pto_vta = ''  # punto de venta habilitado en AFIP
    cbte_tipo = ''  # 1: factura A (ver tabla de parametros)
    cbte_nro = ''  # numero de factura
    cbte_fch = ''  # fecha en formato aaaammdd
    cod_autorizacion = '' # numero de CAI, CAE o CAEA
    imp_total = "0"  # importe total
    doc_tipo_receptor = ""  # CUIT (obligatorio Facturas A o M)
    doc_nro_receptor = ""  # numero de CUIT del cliente
    estado = 'A' #estado del comprobante
    obs = '' #observaciones

    def __init__(self):
        super(ConstatacionComprobantesController, self).__init__()
        self.view = ConstatacionComprobanteView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.cboComboTipo.currentIndexChanged.connect(self.onCboTipoIndexChanged)
        self.view.btnConsultar.clicked.connect(self.onClickConsultar)
        self.view.btnImprimir.clicked.connect(self.onClickImprimir)

    def onCboTipoIndexChanged(self):
        # habilitado = not str(self.view.cboComboTipo.text()).endswith('CAI')
        # self.view.textImpTotal.setEnabled(habilitado)
        # self.view.textTipoDocReceptor.setEnabled(habilitado)
        # self.view.textNroDoc.setEnabled(habilitado)
        pass

    def EstablecerOrden(self):
        self.view.cboComboTipo.proximoWidget = self.view.textCuit
        self.view.textCuit.proximoWidget = self.view.textCae
        self.view.textCae.proximoWidget = self.view.textFecha
        self.view.textTipoComp.proximoWidget = self.view.textFactura.lineEditPtoVta
        self.view.textFactura.lineEditPtoVta.proximoWidget = self.view.textFactura.lineEditNumero
        self.view.textFactura.lineEditNumero.proximoWidget = self.view.textImpTotal
        self.view.textImpTotal.proximoWidget = self.view.textTipoDocReceptor
        self.view.textTipoDocReceptor.proximoWidget = self.view.textNroDoc
        self.view.textNroDoc.proximoWidget = self.view.btnConsultar

    def onClickConsultar(self):
        WSCDC = WSConstComp()

        if str(self.view.cboComboTipo.text()).endswith('CAI'):
            self.cbte_modo = "CAI"  # modalidad de emision: CAI, CAE, CAEA
        elif str(self.view.cboComboTipo.text()).endswith('CAE'):
            self.cbte_modo = "CAE"  # modalidad de emision: CAI, CAE, CAEA
        else:
            self.cbte_modo = "CAEA"  # modalidad de emision: CAI, CAE, CAEA
        self.cuit_emisor = str(self.view.textCuit.text()).replace("-", "")  # proveedor
        self.pto_vta = str(self.view.textFactura.lineEditPtoVta.text())  # punto de venta habilitado en AFIP
        self.cbte_tipo = int(self.view.textTipoComp.text())  # 1: factura A (ver tabla de parametros)
        self.cbte_nro = str(self.view.textFactura.lineEditNumero.text())  # numero de factura
        self.cbte_fch = FechaMysql(self.view.textFecha.date().toPyDate())  # fecha en formato aaaammdd
        self.cod_autorizacion = str(self.view.textCae.text())  # numero de CAI, CAE o CAEA
        # if self.cbte_modo == 'CAI':
        #     self.imp_total = "0"  # importe total
        #     self.doc_tipo_receptor = ""  # CUIT (obligatorio Facturas A o M)
        #     self.doc_nro_receptor = ""  # numero de CUIT del cliente
        # else:
        self.imp_total = str(self.view.textImpTotal.text())  # importe total
        self.doc_tipo_receptor = str(self.view.textTipoDocReceptor.text())  # CUIT (obligatorio Facturas A o M)
        self.doc_nro_receptor = str(self.view.textNroDoc.text())  # numero de CUIT del cliente

        ok = WSCDC.Comprobar(cbte_modo=self.cbte_modo, cuit_emisor=self.cuit_emisor,
                             pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo,
                             cbte_nro=self.cbte_nro, cbte_fch=self.cbte_fch,
                             imp_total=self.imp_total, cod_autorizacion=self.cod_autorizacion,
                             doc_tipo_receptor=self.doc_tipo_receptor, doc_nro_receptor=self.doc_nro_receptor)

        if WSCDC.Resultado == "R":
            detalle = "Rechazado"
        elif WSCDC.Resultado == "A":
            detalle = "Aprobado"
        else:
            detalle = "Observado"
        self.estado = detalle
        self.obs = WSCDC.Obs.encode('utf-8')

        detalle += WSCDC.Obs
        if WSCDC.Resultado == "R":
            detalle = WSCDC.ErrMsg

        self.view.lblResultado.setText(detalle)
        self.view.btnImprimir.setEnabled(True)

    def onClickImprimir(self):
        pdf = PDFConstatatacion()
        pdf.estado = self.estado
        pdf.obs = self.obs
        pdf.cbte_modo = self.cbte_modo
        pdf.add_page()
        self.cbte_fch = self.view.textFecha.date().toPyDate().strftime("%d/%m/%Y")
        pdf.imprimedetalle(cbte_modo=self.cbte_modo, cuit_emisor=self.cuit_emisor,
                           pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo,
                           cbte_nro=self.cbte_nro, cbte_fch=self.cbte_fch,
                           imp_total=self.imp_total, cod_autorizacion=self.cod_autorizacion,
                           doc_tipo_receptor=self.doc_tipo_receptor, doc_nro_receptor=self.doc_nro_receptor)
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        filename = LeerIni('iniciosistema') + "tmp/constatacion{}.pdf".format(self.cuit_emisor)
        pdf.output(name=filename)
        AbrirArchivo(filename)

        padron = PadronAfip()
        cuit = self.cuit_emisor.replace("-", "")
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        filename = "tmp/constancia{}.pdf".format(cuit)
        padron.DescargarConstancia(cuit=cuit, filename=filename)

class PDFConstatatacion(FPDF):

    cbte_modo = 'CAE'
    estado = 'Aprobado'
    obs = ''

    def header(self):
        self.set_font('Arial', '', 8)
        # Calculate width of title and position
        title = datetime.now().date().strftime("%d/%m/%Y")
        self.set_xy(10, 0)
        #self.cell(w, 9, title, 1, 1, 'C', 1)
        self.text(10, 10, title)
        self.text(100, 10, 'Constatacion de comprobantes')
        self.image(imagen('afip_wscdc.png'), 25, 10, 80)
        self.line(0, 26, 240, 26)
        self.ln(1)
        self.set_font('Arial', '', 24)
        self.text(10, 40, u'Constatación de comprobantes con {}'.format(self.cbte_modo))
        self.set_font('Arial', '', 14)
        self.set_xy(0, 45)
        if self.estado.startswith('Aprobado'):
            self.multi_cell(0, 5, u'Los datos ingresados coinciden con una autorizacion otorgada por la AFIP - {}'.
                            format(self.obs))
        else:
            self.multi_cell(0, 5, '{} - {}'.format(self.estado, self.obs))

        self.line(0, self.get_y() + 5, 240, self.get_y() + 5)

    def imprimedetalle(self, *args, **kwargs):
        self.set_font('Arial', 'B', 12)
        self.set_xy(10, self.get_y() + 20)
        self.cell(80, 5, u'Número de CUIT:')
        self.set_font('Arial', '', 12)
        self.set_xy(80, self.get_y())
        self.cell(80, 5, kwargs['cuit_emisor'], 1)

        self.set_font('Arial', 'B', 12)
        self.set_xy(10, self.get_y() + 10)
        self.cell(80, 5, u'Número de {}:'.format(self.cbte_modo))
        self.set_font('Arial', '', 12)
        self.set_xy(80, self.get_y())
        self.cell(80, 5, kwargs['cod_autorizacion'], 1)

        self.set_font('Arial', 'B', 12)
        self.set_xy(10, self.get_y() + 10)
        self.cell(80, 5, u'Fecha de emisión:')
        self.set_font('Arial', '', 12)
        self.set_xy(80, self.get_y())
        self.cell(80, 5, kwargs['cbte_fch'], 1)

        self.set_font('Arial', 'B', 12)
        self.set_xy(10, self.get_y() + 10)
        self.cell(80, 5, u'Tipo de comprobante:')
        self.set_font('Arial', '', 12)
        self.set_xy(80, self.get_y())
        tipo = TipoComprobante.get_by_id(kwargs['cbte_tipo'])
        self.cell(80, 5, '{} - {}'.format(tipo.codigo, tipo.nombre), 1)

        self.set_font('Arial', 'B', 12)
        self.set_xy(10, self.get_y() + 10)
        yant = self.get_y()
        self.multi_cell(70, 5, u'Punto de Venta - Número de Comprobante:')
        self.set_font('Arial', '', 12)
        self.set_xy(80, yant)
        self.cell(80, 5, '{}-{}'.format(kwargs['pto_vta'], kwargs['cbte_nro']), 1)

        if self.cbte_modo.startswith('CAE'):
            self.set_font('Arial', 'B', 12)
            self.set_xy(10, self.get_y() + 15)
            yant = self.get_y()
            self.multi_cell(70, 5, u'Importe total de la operacion en la moneda origial del comprobante:')
            self.set_font('Arial', '', 12)
            self.set_xy(80, yant)
            self.cell(80, 5, kwargs['imp_total'], 1)

            self.set_font('Arial', 'B', 12)
            self.set_xy(10, self.get_y() + 15)
            yant = self.get_y()
            self.multi_cell(70, 5, u'Documento del receptor del comprobante:')
            self.set_font('Arial', '', 12)
            self.set_xy(80, yant)
            self.cell(80, 5, '{}-{}   {}'.format(kwargs['doc_tipo_receptor'], '',kwargs['doc_nro_receptor'] ), 1)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Text color in gray
        self.set_text_color(128)
        # Page number
        self.cell(0, 10, 'Pagina ' + str(self.page_no()), 0, 0, 'C')