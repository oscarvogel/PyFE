import os
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from peewee import DoesNotExist

from controladores.ControladorBase import ControladorBase
from controladores.PadronAfip import PadronAfip
from libs import Ventanas
from libs.Utiles import openFileNameDialog, total_lineas_archivo, inicializar_y_capturar_excepciones
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.Detfact import Detfact
from modelos.Localidades import Localidad
from vistas.ImportacionAFIP import ImportaAFIPView


class ImportaAFIPController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ImportaAFIPView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnArchivo.clicked.connect(lambda : self.onClickBtnSeleccionaArchivo(self.view.textArchivo))
        self.view.btnArchivo_det.clicked.connect(lambda : self.onClickBtnSeleccionaArchivo(self.view.textArchivo_det))
        self.view.btnImportar.clicked.connect(self.onClickBtnImportar)

    def onClickBtnSeleccionaArchivo(self, control):
        archivo = openFileNameDialog(files="Archivos de Texto (*.txt)")
        if archivo:
            control.setText(archivo)

    @inicializar_y_capturar_excepciones
    def onClickBtnImportar(self, *args, **kwargs):
        if not os.path.isfile(self.view.textArchivo.text()) or \
            not os.path.isfile(self.view.textArchivo_det.text()):
            Ventanas.showAlert("Sistema", "Archivos no validos o no encontrados")
            return

        if self.view.checkBorra.isChecked():
            self.BorraComprobantes()

        archivo = open(self.view.textArchivo.text(), "r")
        total = total_lineas_archivo(self.view.textArchivo.text())
        avance = 1
        for linea in archivo:
            avance += 1
            QApplication.processEvents()
            self.view.avance.actualizar(avance / total * 100)
            fecha_cbte = datetime.strptime(linea[0:8], "%Y%m%d").date()
            if self.view.textDesdeFecha.toPyDate() <= fecha_cbte <= self.view.textHastaFecha.toPyDate():
                tipo_doc = linea[56:58]
                nro_doc = linea[59:78][-11:]
                nombre = linea[78:108]
                pto_vta = linea[11:16]
                nro_comp = linea[17:36]
                tipo_comp = linea[8:11]
                cliente = self.VerificaCliente(tipo_doc, nro_doc, nombre)
                cabecera = self.VerificaFactura(tipo_comp, pto_vta, nro_comp)
                cabecera.tipocomp = tipo_comp
                cabecera.cliente = cliente.idcliente
                cabecera.fecha = fecha_cbte
                cabecera.numero = '{}{}'.format(pto_vta[-4:], nro_comp[-8:])
                if tipo_comp in ['011', '012', '013']: #comprobantes sin iva
                    cabecera.neto = float(linea[109:123]) / 100
                    cabecera.iva = 0
                    cabecera.netoa = 0
                    cabecera.netob = 0
                    cabecera.descuento = 0
                    cabecera.recargo = 0
                    cabecera.total = cabecera.neto
                    cabecera.saldo = 0

                cabecera.tipoiva = cliente.tiporesp.idtiporesp
                cabecera.formapago = 1
                cabecera.cuotapago = 0
                cabecera.percepciondgr = float(linea[184:198]) / 100
                cabecera.nombre = nombre
                cabecera.domicilio = ""
                cabecera.obs = ""
                cabecera.save()
        archivo.close()

        archivo = open(self.view.textArchivo_det.text(), "r")
        total = total_lineas_archivo(self.view.textArchivo_det.text())
        avance = 1
        for linea in archivo:
            avance += 1
            QApplication.processEvents()
            self.view.avance.actualizar(avance / total * 100)
            try:
                cabecera = Cabfact.get(
                    Cabfact.tipocomp == linea[0:3],
                    Cabfact.numero == '{}{}'.format(linea[4:8], linea[20:28]
                ))
                try:
                    detalle = Detfact.get(
                        Detfact.idcabfact == cabecera.idcabfact,
                        Detfact.idarticulo == 1
                    )
                except DoesNotExist:
                    detalle = Detfact()
                articulo = Articulo.get_by_id(1)
                detalle.idcabfact = cabecera.idcabfact
                detalle.idarticulo = articulo.idarticulo
                detalle.cantidad = 1
                detalle.unidad = 'UN'
                detalle.costo = 0
                detalle.precio = cabecera.neto
                detalle.tipoiva = articulo.tipoiva.codigo
                detalle.montoiva = cabecera.total / (articulo.tipoiva.iva / 100 + 1) * articulo.tipoiva.iva / 100
                detalle.montodgr = cabecera.percepciondgr
                detalle.montomuni = 0
                detalle.detalle = articulo.nombre
                detalle.descuento = 0
                detalle.save()
            except DoesNotExist:
                pass


    def BorraComprobantes(self):
        cabecera = Cabfact.select().where(
            Cabfact.fecha.between(
                lo=self.view.textDesdeFecha.toPyDate(),
                hi=self.view.textHastaFecha.toPyDate()
            )
        )
        total = len(cabecera)
        avance = 0
        for cab in cabecera:
            avance += 1
            QApplication.processEvents()
            self.view.avance.actualizar(avance / total * 100)
            cab.delete_instance(recursive=True)

    def VerificaCliente(self, tipo_doc, nro_doc, nombre):
        if self.view.consultaAFIP.isChecked():
            padron = PadronAfip()
            ok = padron.ConsultarPersona(cuit=str(nro_doc).replace("-", ""))
        try:
            if tipo_doc == "80":
                cliente = Cliente.get(
                    Cliente.tipodocu == tipo_doc,
                    Cliente.cuit == nro_doc
                )
            else:
                cliente = Cliente.get(
                    Cliente.tipodocu == tipo_doc,
                    Cliente.dni == nro_doc
                )
        except DoesNotExist:
            cliente = Cliente()
            cliente.formapago = 1
            cliente.percepcion = 1
        if self.view.consultaAFIP.isChecked():
            cliente.nombre = padron.denominacion[:Cliente.nombre.max_length]
            cliente.domicilio = padron.direccion[:Cliente.nombre.max_length]
            try:
                localidad = Localidad().select().where(Localidad.nombre.contains(padron.localidad)).get()
            except Localidad.DoesNotExist:
                localidad = Localidad().get_by_id(1)
            cliente.localidad = localidad
            cliente.cuit = padron.cuit if padron.cuit else ''
            cliente.dni = padron.dni if padron.dni else 0
            cliente.tipodocu = 80 if padron.tipo_doc == 80 else 0
            cliente.tiporesp = 2 if padron.tipo_doc == 80 else 0
        else:
            cliente.nombre = nombre
            cliente.domicilio = ""
            cliente.localidad = 1
            cliente.cuit = nro_doc if tipo_doc == "80" else ""
            cliente.dni = nro_doc if tipo_doc != "80" else 0
            cliente.tipodocu = nro_doc
            cliente.tiporesp = 2 if tipo_doc == "80" else 0
        cliente.save()

        return cliente

    def VerificaFactura(self, tipo_comp, pto_vta, nro_comp):
        try:
            cabecera = Cabfact.get(
                Cabfact.tipocomp == tipo_comp,
                Cabfact.numero == '{}{}'.format(pto_vta[-4:], nro_comp[-8:])
            )
        except DoesNotExist:
            cabecera = Cabfact()

        return cabecera
