from datetime import datetime

from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs.Excel import Excel
from libs.Utiles import FormatoFecha, diferencia_meses
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
        self.view.cboCategoriaMono.currentIndexChanged.connect(lambda : self.GrabaParametros('CATEGORIA'))
        self.view.spnCantAdhOS.editingFinished.connect(lambda : self.GrabaParametros('OS'))
        self.view.cboActividad.currentIndexChanged.connect(lambda : self.GrabaParametros('ACTIVIDAD'))

    def exec_(self):
        self.view.cboCategoriaMono.setText(ParamSist.ObtenerParametro("CATEGORIA_MONOTRIBUTO"))
        self.view.spnCantAdhOS.setText(ParamSist.ObtenerParametro("CANTIDAD_ADH_OS"))
        self.view.cboActividad.setIndex(ParamSist.ObtenerParametro("ACTIVIDAD_MONOTRIBUTO"))
        super().exec_()

    def onClickBtnExcel(self):
        excel = Excel()
        if not excel.ObtieneArchivo(archivo="informe recategorizacion de {} a {}".format(
                                                self.view.spnAnio.value(),
                                                self.view.cboPeriodo.GetDato().replace("/", ""))):
            return

        #ajuste por Gonzalo
        if (self.view.cboPeriodo.GetDato() == "Julio/Diciembre"):
            desde, hasta = self.view.cboPeriodo.RangoFecha(self.view.spnAnio.value() + 1)
        else:
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
            ingresos = categoria_monto.ing_brutos
            if ParamSist.ObtenerParametro("ACTIVIDAD_MONOTRIBUTO") == "S":
                cuota = float(categoria_monto.imp_servicio)
            else:
                cuota = float(categoria_monto.imp_cosas_muebles)
            aporte_os = float(categoria_monto.obra_social) * (float(
                ParamSist.ObtenerParametro("CANTIDAD_ADH_OS") or 0
            ) + 1) + float(categoria_monto.sipa)
        else:
            datos = [
                'Datos para recategorizacion no encontrado'
            ]
            ingresos = 0
            cuota = 0
            aporte_os = 0
        excel.EscribeFila(datos=datos, fila=fila)

        fila +=1
        datos = [
            'Hasta el {} todavia podes facturar'.format(
                FormatoFecha(hasta)
            ), round(float(ingresos) - total_facturacion, 2)
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        meses = diferencia_meses(hasta, datetime.now().date()) + 1
        datos = [
            f"Faltan {meses} meses para la proxima recategorizacion", meses
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        datos = [
            "Por mes podes facturar", f"=+B{fila-1}/B{fila}"
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 2
        datos = [
            "Montos para la nueva categoria", ""
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        datos = [
            'Cuota Mensual', cuota
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        datos = [
            'Aporte autonomo / Obra social', aporte_os
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        fila += 1
        datos = [
            'Total', aporte_os + cuota
        ]
        excel.EscribeFila(datos=datos, fila=fila)

        excel.Cerrar()

    def GrabaParametros(self, parametro=''):
        if parametro == 'CATEGORIA':
            ParamSist.GuardarParametro("CATEGORIA_MONOTRIBUTO", self.view.cboCategoriaMono.text())
        elif parametro == 'OS':
            ParamSist.GuardarParametro("CANTIDAD_ADH_OS", self.view.spnCantAdhOS.text())
        elif parametro == 'ACTIVIDAD':
            ParamSist.GuardarParametro("ACTIVIDAD_MONOTRIBUTO", self.view.cboActividad.text())