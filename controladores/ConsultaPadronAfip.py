# coding=utf-8
import os

from controladores.ControladorBase import ControladorBase
from controladores.PadronAfip import PadronAfip
from libs import Ventanas
from libs.Utiles import LeerIni
from vistas.ConsultaPadronAFIP import ConsultaPadronAFIPView

class ConsultaPadronAfipController(ControladorBase):

    def __init__(self):
        super(ConsultaPadronAfipController, self).__init__()
        self.view = ConsultaPadronAFIPView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnConsulta.clicked.connect(self.onClickConsulta)
        self.view.btnImprimir.clicked.connect(self.onClickImprimir)

    def onClickConsulta(self):
        padron = PadronAfip()
        ok = padron.ConsultarPersona(cuit=str(self.view.textCUIT.text()).replace("-", ""))
        self.view.gridDatos.setRowCount(0)
        if padron.errores:
            error = padron.LeerError()
            item = ["Error", error]
            self.view.gridDatos.AgregaItem(item)
            Ventanas.showAlert(LeerIni("nombre_sistema"), "Error al leer informacion en la AFIP")
        else:
            item = ["Denominacion", padron.denominacion]
            self.view.gridDatos.AgregaItem(item)
            item = ["Tipo", "{} {} {}".format(padron.tipo_persona, padron.tipo_doc, padron.dni)]
            self.view.gridDatos.AgregaItem(item)
            item = ["Estado", padron.estado]
            self.view.gridDatos.AgregaItem(item)
            item = ["Direccion", padron.direccion]
            self.view.gridDatos.AgregaItem(item)
            item = ["Localidad", padron.localidad]
            self.view.gridDatos.AgregaItem(item)
            item = ["Provincia", padron.provincia]
            self.view.gridDatos.AgregaItem(item)
            item = ["Codigo Postal", padron.cod_postal]
            self.view.gridDatos.AgregaItem(item)

    def onClickImprimir(self):
        padron = PadronAfip()
        cuit = str(self.view.textCUIT.text()).replace("-", "")
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        filename = "tmp/constancia{}.pdf".format(cuit)
        padron.DescargarConstancia(cuit=cuit, filename=filename)
