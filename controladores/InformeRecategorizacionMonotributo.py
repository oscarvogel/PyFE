from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs.Excel import Excel
from libs.Utiles import GuardarArchivo, MesIdentificador, PeriodoAFecha, FormatoFecha
from modelos.Cabfact import Cabfact
from modelos.CategoriasMonotributo import CategoriaMono
from modelos.ParametrosSistema import ParamSist
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

        fila += 2
        datos = [
            'Detalle', 'Montos'
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        datos = [
            'Ingresos Brutos Devengados entre {} y {}'.format(
                FormatoFecha(desde, formato="dma"), FormatoFecha(hasta, formato="dma")
            ), total_facturacion
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        categoria_monotributo = ParamSist.ObtenerParametro("CATEGORIA_MONOTRIBUTO")
        datos = [
            'Categoria Actual', categoria_monotributo
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        try:
            datos_categoria = CategoriaMono.get_by_id(categoria_monotributo)
            datos = [
                f'Categoria actual {datos_categoria.categoria}', datos_categoria.ing_brutos
            ]
        except:
            datos = [
                'Datos de categoria no encontrado', 0
            ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        categoria_monto = CategoriaMono.CategoriaMonto(total_facturacion)
        if categoria_monto:
            datos = [
                f'Recategorizacion {categoria_monto.categoria}', categoria_monto.ing_brutos
            ]
        else:
            datos = [
                'Datos para recategorizacion no encontrado'
            ]
        excel.EscribeFila(datos=datos, fila=fila)

        excel.Cerrar()