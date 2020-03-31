from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs.Excel import Excel
from libs.Utiles import GuardarArchivo, MesIdentificador, PeriodoAFecha
from modelos.Cabfact import Cabfact
from vistas.InformeRecategorizacionMonotributo import InfRecMonotributoView


class InfRecMonotributoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = InfRecMonotributoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(self.onClickBtnExcel)

    def onClickBtnExcel(self):
        excel = Excel()
        if not excel.ObtieneArchivo(archivo="informe recategorizacion de {} a {}".format(
                                                self.view.spnAnio.value(),
                                                self.view.cboPeriodo.GetDato().replace("/", ""))):
            return

        desde, hasta = self.view.cboPeriodo.RangoFecha(self.view.spnAnio.value())
        datos = Cabfact.DatosAgrupadosPeriodo(
            desde=desde,
            hasta=hasta
        )
        fila = 0
        excel.Titulo('Informe para recategorizacion', desdecol='A', hastacol='B', fila=fila)
        fila += 1
        avance = 1
        total = len(datos)
        total_facturacion = 0
        for d in datos:
            QApplication.processEvents()
            self.view.avance.actualizar(avance / total * 100)
            avance += 1
            total_facturacion += float(d.total)

        datos = [
            'Total Facturado', total_facturacion
        ]
        excel.EscribeFila(datos=datos, fila=fila)
        excel.Cerrar()