# coding=utf-8

import os
from controladores.ControladorBase import ControladorBase
from controladores.PadronAfip import PadronAfip
from libs import Ventanas
from libs.Utiles import LeerIni
from modelos.Clientes import Cliente
from modelos.Localidades import Localidad
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
        self.view.btnAgregaCliente.clicked.connect(self.onClickAgregaCliente)

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
            item = ["Monotributo", padron.monotributo, padron.actividad_monotributo]
            self.view.gridDatos.AgregaItem(item)
            item = ["categoriaMonotributo", padron.actividad_monotributo]
            self.view.gridDatos.AgregaItem(item)
            item = ["imp_iva", padron.imp_iva]
            self.view.gridDatos.AgregaItem(item)
            item = ["Empleador", padron.empleador]
            self.view.gridDatos.AgregaItem(item)
            # item = ["Impuestos", padron.impuestos]
            # self.view.gridDatos.AgregaItem(item)
            # item = ["Ganancias", padron.imuestos]
            # self.view.gridDatos.AgregaItem(item)
            # item = ["Actividades", padron.actividades]
            # self.view.gridDatos.AgregaItem(item)

    def onClickImprimir(self):
        padron = PadronAfip()
        cuit = str(self.view.textCUIT.text()).replace("-", "")
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        filename = "tmp/constancia{}.pdf".format(cuit)
        padron.DescargarConstancia(cuit=cuit, filename=filename)

    def onClickAgregaCliente(self):
        padron = PadronAfip()
        ok = padron.ConsultarPersona(cuit=str(self.view.textCUIT.text()).replace("-", ""))
        if padron.errores:
            Ventanas.showAlert(LeerIni("nombre_sistema"), "Error al leer informacion en la AFIP")
        else:
            cliente = Cliente()
            cliente.nombre = padron.denominacion[:30]
            cliente.domicilio = padron.direccion[:30]
            try:
                localidad = Localidad().select().where(Localidad.nombre.contains(padron.localidad)).get()
            except Localidad.DoesNotExist:
                localidad = Localidad().get_by_id(1)
            cliente.localidad = localidad
            cliente.cuit = padron.cuit
            cliente.dni = padron.dni
            cliente.tipodocu = 80 if padron.tipo_doc == 80 else 0
            S = 2
            N = 1
            EX = 4
            if padron.imp_iva == "S":
                cliente.tiporesp = 2
                print("inscripto")
            elif padron.imp_iva == "EX":
                cliente.tiporesp = 4
                print("exento")
            elif padron.imp_iva == "N":
                cliente.tiporesp = 1
                print("mono")

            cliente.formapago = 1
            cliente.percepcion = 1
            cliente.save()
            Ventanas.showAlert(LeerIni("nombre_sistema"), "Verifique si los datos cargados son los correctos")