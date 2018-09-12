# coding=utf-8
import os

from peewee import fn

from controladores.ControladorBase import ControladorBase
from libs import Ventanas, Constantes
from libs.Utiles import GuardarArchivo, FechaMysql, LeerIni
from modelos.CabFacProv import CabFactProv
from modelos.DetFactProv import DetFactProv
from vistas.RG3685 import RG3685View


class RG3685ComprasController(ControladorBase):

    def __init__(self):
        super(RG3685ComprasController, self).__init__()
        self.view = RG3685View()
        self.view.setWindowTitle("RG 3685 Compras")
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnProcesar.clicked.connect(self.Procesar)

    def Procesar(self):
        if not os.path.isdir("cpras-vtas"):
            os.mkdir("cpras-vtas")

        arch = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                              filename="REGINFO_CV_COMPRAS_CBTE_{}".format(self.view.periodo.cPeriodo)), "w")
        archDet = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                                 filename="REGINFO_CV_COMPRAS_ALICUOTAS_{}".format(self.view.periodo.cPeriodo)), "w")
        if not arch or not archDet:
            return

        anchos = [8, 3, 5, 20, 16, 2, 20, 30, 15, 15, 15, 15, 15, 15, 15, 15, 3, 10, 1, 1, 15, 15, 11, 30, 15]
        anchosDet = [3, 5, 20, 2, 20, 15, 4, 15]

        data = CabFactProv.select().where(CabFactProv.periodo == self.view.periodo.cPeriodo)

        for d in data:
            if LeerIni(clave='base') == 'sqlite': #esto es porque sqlite no soporta boolean
                exporta = d.tipocomp.codigo in Constantes.COMPEXPORTA
            else:
                exporta = d.tipocomp.exporta
            if exporta:
                detalle = DetFactProv.select(DetFactProv.iva, fn.SUM(DetFactProv.neto).alias("neto")).group_by(
                    DetFactProv.iva).where(DetFactProv.idpcabecera == d.idpcabfact)
                fecha = FechaMysql(d.fechaem)
                tipocomp = str(d.tipocomp.codigo).zfill(3)
                ptovta = d.numero[:4].zfill(5)
                if ptovta == "00000":
                    ptovta = "00001" #citi compras no permite pto vta en 0
                numero = d.numero[4:].zfill(20)
                despacho = ''
                if d.idproveedor.tiporesp.idtiporesp == 3: #consumidor final
                    tipodoc = '96'
                else:
                    tipodoc = '80'
                nrodoc = d.idproveedor.cuit.replace('-','').zfill(20)
                nombre = d.idproveedor.nombre[:30]
                total = '{:.{prec}f}'.format(d.neto + d.iva + d.percepciondgr +
                            d.impuestos + d.exentos + d.percepcioniva +
                            d.nogravados, prec=2).replace('.','').zfill(15)
                nogravado = '{:.{prec}f}'.format(d.nogravados, prec=2).replace('.', '').zfill(15)
                exento = '{:.{prec}f}'.format(d.exentos, prec=2).replace('.', '').zfill(15)
                percepcioniva = '{:.{prec}f}'.format(d.percepcioniva, prec=2).replace('.', '').zfill(15)
                interno = '{:.{prec}f}'.format(d.impuestos, prec=2).replace('.', '').zfill(15)
                percepdgr = '{:.{prec}f}'.format(d.percepciondgr, prec=2).replace('.', '').zfill(15)
                impmun = str(0).zfill(15)
                impuesto = str(0).zfill(15)
                moneda = 'PES'
                cambio = '{:.{prec}f}'.format(1, prec=6).replace('.','').zfill(10)
                cantalic = str(detalle.count()).zfill(1)
                codop = '0'
                creditofiscal = '{:.{prec}f}'.format(d.iva, prec=2).replace('.','').zfill(15)
                otros = '{:.{prec}f}'.format(0, prec=6).replace('.', '').zfill(15)
                cuitemisor = '{:.{prec}f}'.format(0, prec=6).replace('.', '').zfill(11)
                denoemisor = ''
                ivacomision = '{:.{prec}f}'.format(0, prec=6).replace('.','').zfill(15)

                for det in detalle:
                    if d.tipocomp.letra == 'C':
                        codop = 'A'
                        cantalic = '0'
                    elif d.iva == 0:
                        codop = '0'

                    neto = '{:.{prec}f}'.format(det.neto, prec=2).replace('.', '').zfill(15)
                    alicuota = Constantes.ALICUOTA_AFIP[int('{:.{prec}f}'.format(det.iva, prec=0))]
                    impuestodetalle = '{:.{prec}f}'.format(det.neto * det.iva / 100, prec=2).replace('.', '').zfill(15)
                    if d.tipocomp.codigo not in [11, 32, 13]:
                        itemsdet = [
                            tipocomp, ptovta, numero, tipodoc, nrodoc,
                            neto, alicuota, impuestodetalle
                        ]
                        archDet.write("".join("%*s" % i for i in zip(anchosDet, itemsdet)))
                        archDet.write("\n")

                items = [
                    fecha, tipocomp, ptovta, numero, despacho, tipodoc, nrodoc,
                    nombre, total, nogravado, exento, percepcioniva, impuesto, percepdgr,
                    impmun, interno, moneda, cambio, cantalic, codop, creditofiscal, otros,
                    cuitemisor, denoemisor, ivacomision
                ]
                arch.write("".join("%*s" % i for i in zip(anchos, items)))
                arch.write("\n")

        arch.close()
        archDet.close()
        Ventanas.showAlert("Sistema", "Proceso finalizado")
        self.view.close()

