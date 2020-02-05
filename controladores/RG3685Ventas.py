# coding=utf-8
import os

from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs import Ventanas, Constantes
from libs.Utiles import GuardarArchivo, FechaMysql, Normaliza
from modelos.Cabfact import Cabfact
from vistas.RG3685 import RG3685View


class RG3685VentasController(ControladorBase):

    def __init__(self):
        super(RG3685VentasController, self).__init__()
        self.view = RG3685View()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnProcesar.clicked.connect(self.Procesar)

    def Procesar(self):
        #arch = open(Constantes.ARCHIVO_CITI_VTAS + "ventas" + self.periodo.cPeriodo + ".txt", "w")
        #archDet = open(Constantes.ARCHIVO_CITI_VTAS + "alicuotas-ventas" + self.periodo.cPeriodo + ".txt", "w")
        if not os.path.isdir("cpras-vtas"):
            os.mkdir("cpras-vtas")

        data = Cabfact.select().where(Cabfact.fecha.between(lo=self.view.periodo.dInicio,
                                                              hi=self.view.periodo.dFin))
        arch = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                              filename="REGINFO_CV_VENTAS_CBTE_{}".format(self.view.periodo.cPeriodo)), "w")
        archDet = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                                 filename="REGINFO_CV_VENTAS_ALICUOTAS_{}".format(self.view.periodo.cPeriodo)), "w")
        if not arch or not archDet:
            return

        anchos = [8, 3, 5, 20, 20, 2, 20, 30, 15, 15, 15, 15, 15, 15, 15, 15, 3, 10, 1, 1, 15, 8]
        anchosDet = [3, 5, 20, 15, 4, 15 ]

        totalData = len(data)
        cant = 0.0
        for d in data:
            QApplication.processEvents()
            cant += 1.
            self.view.avance.actualizar(cant/totalData*100.)
            if d.tipocomp.exporta:
                fecha = FechaMysql(d.fecha)
                tipocomp = str(d.tipocomp.codigo).zfill(3)
                ptovta = d.numero[:4].zfill(5)
                numero = d.numero[4:].zfill(20)
                if d.cliente.tiporesp.idtiporesp == 3: #consumidor final
                    if d.total > 1000:
                        tipodoc = '96'
                        ndoc = str(d.cliente.dni).zfill(20) if d.cliente.dni != 0 else '11111111'.zfill(20)
                    else:
                        tipodoc = '99' if d.cliente.dni == 0 or d.cliente.dni == '11111111' else '96'
                        ndoc = ''.zfill(20) if d.cliente.dni == '11111111' else str(d.cliente.dni).zfill(20)
                else:
                    tipodoc = '80'
                    ndoc = d.cliente.cuit.replace('-','').zfill(20)
                nombre = Normaliza(d.nombre[:30])
                total = '{:.{prec}f}'.format(d.total, prec=2).replace('.','').zfill(15)
                nogravado, nocategorizado, exentas, percepcion, municipal, impinterno, otros = \
                    ''.zfill(15), ''.zfill(15), ''.zfill(15), ''.zfill(15), ''.zfill(15),''.zfill(15),''.zfill(15)
                percepciondgr = '{:.{prec}f}'.format(d.percepciondgr, prec=2).replace('.','').zfill(15)
                moneda = 'PES'
                cambio = '1000000'.zfill(10)
                if d.netoa != 0 and d.netob != 0:
                    cantalic = '2'
                elif d.netoa != 0 and d.netob == 0:
                    cantalic = '1'
                elif d.netoa == 0 and d.netob != 0:
                    cantalic = '1'
                else:
                    cantalic = '1'

                if d.netoa == 0 and d.netob == 0:
                    codop = 'A'
                else:
                    codop = '0'
                vencepago = ''.zfill(8)
                items = [fecha, tipocomp, ptovta, numero, numero, tipodoc, ndoc, nombre, total, nogravado, nocategorizado,
                        exentas, percepcion, percepciondgr, municipal, impinterno, moneda, cambio, cantalic,
                        codop, otros, vencepago]
                arch.write("".join("%*s" % i for i in zip(anchos, items)))
                arch.write("\n")

                if d.netoa != 0:
                    alicuota = Constantes.ALICUOTA_AFIP[21]
                    impuesto = '{:.{prec}f}'.format(round(float(d.netoa) * 21. / 100,2), prec=2)\
                        .replace(".","").zfill(15)
                    items = [tipocomp, ptovta, numero, str(d.netoa).replace(".","").zfill(15), alicuota, impuesto]
                    archDet.write("".join("%*s" % i for i in zip(anchosDet, items)))
                    archDet.write("\n")

                if d.netob != 0:
                    alicuota = Constantes.ALICUOTA_AFIP[10.5]
                    impuesto = '{:.{prec}f}'.format(round(float(d.netob) * 10.5 / 100,2), prec=2)\
                        .replace(".","").zfill(15)
                    items = [tipocomp, ptovta, numero, str(d.netob).replace(".","").zfill(15), alicuota, impuesto]
                    archDet.write("".join("%*s" % i for i in zip(anchosDet, items)))
                    archDet.write("\n")

                if d.netoa == 0 and d.netob == 0:
                    alicuota = Constantes.ALICUOTA_AFIP[0]
                    impuesto = '0'.zfill(15)
                    items = [tipocomp, ptovta, numero, str(d.netob).replace(".","").zfill(15), alicuota, impuesto]
                    archDet.write("".join("%*s" % i for i in zip(anchosDet, items)))
                    archDet.write("\n")

        arch.close()
        archDet.close()
        Ventanas.showAlert("Sistema", "Proceso finalizado")
        self.view.close()


