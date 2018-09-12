# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs.Utiles import GuardarArchivo, FechaMysql
from modelos.CabFacProv import CabFactProv
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
        arch = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                              filename="REGINFO_CV_COMPRAS_CBTE"), "w")
        archDet = open(GuardarArchivo(caption="Guardar archivo", directory="cpras-vtas", filter="*.TXT",
                                 filename="REGINFO_CV_COMPRAS_ALICUOTAS"), "w")
        if not arch or not archDet:
            return

        anchos = [8, 3, 5, 20, 16, 2, 20, 30, 15, 15, 15, 15, 15, 15, 15, 15, 3, 10, 1, 1, 15, 15, 11, 20, 15]
        anchosDet = [3, 5, 20, 2, 20, 15, 4, 15]

        data = CabFactProv.select().where(CabFactProv.fecha.between(lo=self.view.periodo.dInicio,
                                                                    hi=self.view.periodo.dFin))

        for d in data:
            fecha = FechaMysql(d.fechaem)
            tipocomp = str(d.tipocomp.codigo).zfill(3)
            ptovta = d.numero[:4].zfill(5)
            numero = d.numero[4:].zfill(20)
            despacho = ''
            if d.idproveedor.tiporesp.idtiporesp == 3: #consumidor final
                tipodoc = '96'
            else:
                tipodoc = '80'
            nrodoc = d.idproveedor.cuit.replace('-','').zfill(20)
            nombre = d.idproveedor.nombre[:30]
            total = str(d.neto + d.iva + d.percepciondgr + d.impuestos)
