# coding=utf-8
"""Las tres pantallas de stock: consultar, ajustar y auditar.

Por que tres y no una con pestanas
----------------------------------
Consulta, ajuste y auditoria son tres trabajos distintos y con frecuencias
distintas: se consulta todo el tiempo, se ajusta una vez por conteo, y la
auditoria se mira cuando algo no cierra. Meterlas en una pantalla con
pestanas hace que la que se usa siempre compita por el lugar con las otras dos.

Y el ajuste NO es un ABM
-----------------------
`vistas/ABM.py` edita y borra registros de una tabla, y un movimiento de
stock no se edita ni se borra: se escribe el contrario. Si el ajuste fuera un
ABM, el operador tendria ahi un boton de borrar que no se puede dejar
habilitado, y la primera vez que lo aprieta se pierde el historico de por que
el stock quedo asi. Por eso el ajuste tiene su propia pantalla, con un
formulario y no con una grilla.
"""

from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Checkbox import CheckBox
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Fechas import Fecha
from libs.Grillas import Grilla
from libs.Utiles import icono
from modelos.Articulos import Articulo
from vistas.Busqueda import UiBusqueda
from vistas.VistaBase import VistaBase


class _BuscarProducto(object):
    """El buscador de articulo con F2, igual que el de centro de costos.

    Va como mixin y no copiado en las tres pantallas: las tres necesitan
    elegir un articulo, y tres copias del mismo bloque de UiBusqueda
    divergen en cuanto una cambia.

    LA FIRMA DEL CALLBACK
    ---------------------
    `al_elegir` recibe SIEMPRE dos argumentos: `(idarticulo, nombre)`. No
    "los que haga falta": el buscador siempre tiene los dos, y un callback que
    acepte uno solo revienta con TypeError en el momento de apretar F2, que es
    un camino que ningun test abre porque la ventana es modal.
    """

    def _buscar_producto(self, al_elegir):
        ventana = UiBusqueda()
        ventana.modelo = Articulo
        ventana.cOrden = "nombre"
        ventana.limite = 100
        ventana.campos = ["idarticulo", "nombre"]
        ventana.campoBusqueda = Articulo.nombre
        ventana.campoRetorno = Articulo.idarticulo
        ventana.campoRetornoDetalle = Articulo.nombre
        ventana.CargaDatos()
        ventana.exec_()
        if ventana.lRetval:
            al_elegir(ventana.ValorRetorno, ventana.campoRetornoDetalle)


class StockView(VistaBase):
    """Cuanto hay de cada cosa, y cuales estan faltando."""

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Stock")
        self.layoutPpal = QVBoxLayout(self)

        filtros = QHBoxLayout()
        self.txtBuscar = EntradaTexto(placeholderText="Buscar producto")
        filtros.addWidget(Etiqueta(texto="Buscar"))
        filtros.addWidget(self.txtBuscar)
        # El filtro que mas se usa es "solo los que faltan", asi que queda
        # arriba del todo y no escondido en un combo con tres opciones.
        self.chkSoloFaltantes = CheckBox(texto="Solo faltantes")
        self.chkIncluirSinControlar = CheckBox(texto="Incluir sin controlar")
        filtros.addWidget(self.chkSoloFaltantes)
        filtros.addWidget(self.chkIncluirSinControlar)
        self.layoutPpal.addLayout(filtros)

        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        self.gridDatos.ArmaCabeceras(cabeceras=[
            'Codigo', 'Producto', 'Unidad', 'Stock', 'Minimo', 'Estado',
        ], formatos=[
            'Entero', 'String', 'String', 'Cantidad', 'Cantidad', 'String',
        ])
        # Sin este cartel, la primera vez que se abre la pantalla (que es
        # siempre: ningun producto controla stock todavia) se ve una grilla en
        # blanco y parece un bug. Con el cartel se entiende al toque que hay
        # que tildar la casilla o marcar los productos.
        self.gridDatos.textoVacio = (
            "Ningún producto controla stock todavía.\n\n"
            "Tildá «Incluir sin controlar» para verlos, o usá "
            "«Marcar productos» para activarlo.")
        self.layoutPpal.addWidget(self.gridDatos)

        layoutBotones = QHBoxLayout()
        self.btnAjustar = Boton(texto="Ajustar", imagen=icono('ajustar-texto'),
                                estilo='primario',
                                tooltip="Contar y corregir el stock de un producto")
        self.btnMovimientos = Boton(texto="Movimientos", imagen=icono('reportes'),
                                    tooltip="Ver de donde viene cada cambio de stock")
        self.btnMarcar = Boton(texto="Marcar productos",
                               imagen=icono('check'),
                               tooltip="Marcar como controlado todo lo que "
                                       "todavia no lo esta")
        self.btnExcel = Boton(texto="Exportar", imagen=icono('excel'))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnAjustar)
        layoutBotones.addWidget(self.btnMovimientos)
        layoutBotones.addWidget(self.btnMarcar)
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(layoutBotones)

    def Mostrar(self, filas):
        self.gridDatos.setRowCount(0)
        for fila in filas:
            self.gridDatos.AgregaItem(fila)

    def ProductoElegido(self):
        """Devuelve el id del articulo de la fila elegida, o None."""
        if self.gridDatos.currentRow() < 0:
            return None
        return self.gridDatos.ObtenerItem(
            fila=self.gridDatos.currentRow(), col='Codigo')


class AjustesStockView(VistaBase, _BuscarProducto):
    """Contar y corregir. No es un ABM porque un movimiento no se edita."""

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Ajustar stock")
        self.resize(560, 320)
        self.layoutPpal = QVBoxLayout(self)
        self.layoutPpal.addWidget(EtiquetaTitulo(texto=self.windowTitle()))

        # El producto va con F2 y no con un combo de mil articulos: un combo
        # de mil entradas se abre a la mitad de la pantalla y no se encuentra
        # nada.
        filaProducto = QHBoxLayout()
        filaProducto.addWidget(Etiqueta(texto="Producto"))
        self.txtProducto = EntradaTexto()
        # Ancho a proposito: el default deja el campo angosto y no entra ni un
        # código de cinco dígitos, y el caso normal es escribir el código a
        # mano aunque exista el F2.
        self.txtProducto.setFixedWidth(110)
        self.txtProducto.returnPressed.connect(self.buscar_producto)
        self.lblNombre = Etiqueta()
        filaProducto.addWidget(self.txtProducto)
        filaProducto.addWidget(self.lblNombre)
        self.layoutPpal.addLayout(filaProducto)

        # Se muestra y no se edita: la pantalla ajusta, no define el stock.
        # Si se pudiera escribir aca, un numero mal tipeado se convierte en
        # el stock real sin que pase por ningun movimiento.
        filaActual = QHBoxLayout()
        filaActual.addWidget(Etiqueta(texto="Stock actual"))
        self.txtStockActual = EntradaTexto(enabled=False)
        filaActual.addWidget(self.txtStockActual)
        self.lblUltimo = Etiqueta()
        filaActual.addWidget(self.lblUltimo)
        self.layoutPpal.addLayout(filaActual)

        filaCantidad = QHBoxLayout()
        filaCantidad.addWidget(Etiqueta(texto="Cantidad a ajustar"))
        self.txtCantidad = EntradaTexto()
        filaCantidad.addWidget(self.txtCantidad)
        self.lblAyuda = Etiqueta(texto="Con signo: + entra, - sale")
        filaCantidad.addWidget(self.lblAyuda)
        self.layoutPpal.addLayout(filaCantidad)

        filaObs = QHBoxLayout()
        filaObs.addWidget(Etiqueta(texto="Observacion"))
        self.txtObservacion = EntradaTexto(
            placeholderText="Por qué se ajusta: conteo, rotura, error de carga")
        filaObs.addWidget(self.txtObservacion)
        self.layoutPpal.addLayout(filaObs)

        self.lblResultado = Etiqueta()
        self.layoutPpal.addWidget(self.lblResultado)

        layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=icono('guardar'),
                               autodefault=False, estilo='primario')
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        layoutBotones.addWidget(self.btnGrabar)
        layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(layoutBotones)
        self.layoutPpal.addStretch(1)

    def F2Producto(self, al_elegir):
        self._buscar_producto(al_elegir)

    def buscar_producto(self, *args, **kwargs):
        """F2 y Enter abren el buscador. Es lo unico que hace este metodo."""
        self.F2Producto(self.ProductoElegido)

    def ProductoElegido(self, idarticulo, nombre):
        self.txtProducto.setText(str(idarticulo))
        self.lblNombre.setText(nombre or "")


class MovimientosStockView(VistaBase, _BuscarProducto):
    """De donde sale cada numero. Sin esto, un faltante no se explica."""

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Movimientos de stock")
        self.layoutPpal = QVBoxLayout(self)

        filtros = QHBoxLayout()
        filtros.addWidget(Etiqueta(texto="Desde"))
        self.desdeFecha = Fecha()
        self.desdeFecha.setFecha(-30)
        filtros.addWidget(self.desdeFecha)
        filtros.addWidget(Etiqueta(texto="Hasta"))
        self.hastaFecha = Fecha()
        self.hastaFecha.setFecha()
        filtros.addWidget(self.hastaFecha)
        filtros.addWidget(Etiqueta(texto="Producto"))
        self.txtProducto = EntradaTexto()
        self.txtProducto.setMaximumWidth(90)
        self.lblNombreProducto = Etiqueta()
        filtros.addWidget(self.txtProducto)
        filtros.addWidget(self.lblNombreProducto)
        filtros.addStretch(1)
        self.layoutPpal.addLayout(filtros)

        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        self.gridDatos.ArmaCabeceras(cabeceras=[
            'Fecha', 'Codigo', 'Producto', 'Origen', 'Cantidad',
            'Comprobante', 'Observacion', 'Anulado',
        ], formatos=[
            'Date', 'Entero', 'String', 'String', 'Cantidad', 'String',
            'String', 'String',
        ])
        # "Todavía no hay movimientos" y "no hay movimientos en esas fechas" son
        # dos cosas distintas, y sin el cartel no se sabe cual de las dos es.
        self.gridDatos.textoVacio = "No hay movimientos de stock en ese período."
        self.layoutPpal.addWidget(self.gridDatos)

        layoutBotones = QHBoxLayout()
        self.btnBuscarProducto = Boton(texto="Buscar producto",
                                        imagen=icono('buscar'))
        self.btnExcel = Boton(texto="Exportar", imagen=icono('excel'))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnBuscarProducto)
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(layoutBotones)

    def Mostrar(self, filas):
        self.gridDatos.setRowCount(0)
        for fila in filas:
            self.gridDatos.AgregaItem(fila)

    def F2Producto(self, al_elegir):
        self._buscar_producto(al_elegir)
