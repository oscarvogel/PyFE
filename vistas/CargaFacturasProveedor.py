# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.ComboBox import ComboConstComp
from libs.EntradaTexto import Factura, EntradaTexto
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Spinner import Periodo
from libs.Utiles import imagen, icono
from modelos import Proveedores, Tipocomprobantes
from modelos.Articulos import Articulo
from modelos.CentroCostos import CentroCosto
from vistas.Busqueda import UiBusqueda


class CargaFacturaProveedorView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Carga facturas de proveedor")

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)

        self.gridLayout = QGridLayout()
        self.lblCodigoProv = Etiqueta(texto="Proveedor")
        self.textProveedor = Proveedores.Valida()
        self.lblNombProv = Etiqueta()
        self.textProveedor.widgetNombre = self.lblNombProv
        self.gridLayout.addWidget(self.lblCodigoProv, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.textProveedor, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.lblNombProv, 0, 2, 1, 1)

        self.lblCodTipoComp = Etiqueta(texto="Tipo comprobante")
        self.textTipoComp = Tipocomprobantes.Valida()
        self.lblNomTipoComp = Etiqueta()
        self.textTipoComp.widgetNombre = self.lblNomTipoComp
        self.gridLayout.addWidget(self.lblCodTipoComp, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.textTipoComp, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.lblNomTipoComp, 1, 2, 1, 1)

        self.lblFactura = Etiqueta(texto='Numero')
        self.textFactura = Factura()
        self.gridLayout.addWidget(self.lblFactura, 1, 3, 1, 1)
        self.gridLayout.addLayout(self.textFactura, 1, 4, 1, 1)

        self.lblFechaCarga = Etiqueta(texto="Fecha Carga")
        self.fechaCarga = Fecha()
        self.fechaCarga.setFecha()
        self.gridLayout.addWidget(self.lblFechaCarga, 2, 0, 1, 1)
        self.gridLayout.addWidget(self.fechaCarga, 2, 1, 1, 1)

        self.lblFechaEm = Etiqueta(texto="Fecha Emisión")
        self.fechaEmision = Fecha()
        self.fechaEmision.setFecha()
        self.gridLayout.addWidget(self.lblFechaEm, 2, 3, 1, 1)
        self.gridLayout.addWidget(self.fechaEmision, 2, 4, 1, 1)

        self.lblPeriodo = Etiqueta(texto="Periodo")
        self.periodo = Periodo()
        self.gridLayout.addWidget(self.lblPeriodo, 2, 5, 1, 1)
        self.gridLayout.addLayout(self.periodo, 2, 6, 1, 1)

        self.lblModoCpte = Etiqueta(texto="Modo comprobante")
        self.cboModoCpte = ComboConstComp()
        self.gridLayout.addWidget(self.lblModoCpte, 3, 0, 1, 1)
        self.gridLayout.addWidget(self.cboModoCpte, 3, 1, 1, 1)

        self.lblCAE = Etiqueta(texto='CAE/CAI')
        self.textCAE = EntradaTexto(placeholderText='CAE/CAI')
        self.gridLayout.addWidget(self.lblCAE, 3, 2, 1, 1)
        self.gridLayout.addWidget(self.textCAE, 3, 3, 1, 1)
        self.layoutPpal.addLayout(self.gridLayout)

        self.gridDatos = GrillaFactProv()
        self.layoutPpal.addWidget(self.gridDatos)

        self.gridTotales = QGridLayout()
        self.lblExentos = Etiqueta(texto="Exentos")
        self.textExentos = EntradaTexto(placeholderText="Exentos")
        self.gridTotales.addWidget(self.lblExentos, 0, 0)
        self.gridTotales.addWidget(self.textExentos, 0, 1)
        lblInternos = Etiqueta(texto="Imp. Internos")
        self.textInternos = EntradaTexto(placeholderText="Imp. Internos")
        self.gridTotales.addWidget(lblInternos, 0, 2)
        self.gridTotales.addWidget(self.textInternos, 0, 3)
        self.lblNeto = Etiqueta(texto="Netos")
        self.textNeto = EntradaTexto(enabled=False, placeholderText="Neto")
        self.gridTotales.addWidget(self.lblNeto, 0, 4)
        self.gridTotales.addWidget(self.textNeto, 0, 5)

        self.lblNoGravado = Etiqueta(texto="No gravados")
        self.textNoGravado = EntradaTexto(placeholderText="No gravados")
        self.gridTotales.addWidget(self.lblNoGravado, 1, 0)
        self.gridTotales.addWidget(self.textNoGravado, 1, 1)
        self.lblPercepcionDGR = Etiqueta(texto="Percepción DGR")
        self.textPercepcionDGR = EntradaTexto(placeholderText="Percepción DGR", enabled=False)
        self.gridTotales.addWidget(self.lblPercepcionDGR, 1, 2)
        self.gridTotales.addWidget(self.textPercepcionDGR, 1, 3)
        self.lblIVA = Etiqueta(texto="IVA")
        self.textIVA = EntradaTexto(enabled=False)
        self.gridTotales.addWidget(self.lblIVA, 1, 4)
        self.gridTotales.addWidget(self.textIVA, 1, 5)

        self.lblPercepcionIVA = Etiqueta(texto="Percepción IVA")
        self.textPercepcionIVA = EntradaTexto(placeholderText="Percepción IVA")
        self.gridTotales.addWidget(self.lblPercepcionIVA, 2, 0)
        self.gridTotales.addWidget(self.textPercepcionIVA, 2, 1)
        self.lblTotal = Etiqueta(texto="Total")
        self.textTotal = EntradaTexto(enabled=False)
        self.gridTotales.addWidget(self.lblTotal, 2, 4)
        self.gridTotales.addWidget(self.textTotal, 2, 5)

        self.layoutPpal.addLayout(self.gridTotales)

        self.layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=icono('guardar'), autodefault=False, enabled=False, estilo='primario')
        self.btnConstatacion = Boton(texto="Constatación", imagen=icono('arca'),
                                     autodefault=False, enabled=False)
        self.btnPercepDGR = Boton(texto="Percepción DGR", imagen=imagen('dgr-misiones.png'),
                                  enabled=False, autodefault=False)
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnGrabar)
        self.layoutBotones.addWidget(self.btnPercepDGR)
        self.layoutBotones.addWidget(self.btnConstatacion)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)

class GrillaFactProv(Grilla):

    # El indice de 'Producto'. Va al final a proposito: la grilla ya usaba los
    # indices de las columnas viejas en el F2 del centro de costos, en el salto
    # de fila con Enter y en el calculo de totales, y meter una columna en el
    # medio correria los tres sin que se note. Agregandola al final, lo que
    # hay que tocar es una sola linea.
    COL_PRODUCTO = 7

    def __init__(self, *args, **kwargs):
        Grilla.__init__(self, *args, **kwargs)
        cabecera = [
            'Ctro Costos', 'Cantidad', 'Neto', 'IVA', 'Detalle',
            'Nombre Ctro Costos', 'Total',
            # El producto va ultimo y es OPCIONAL: una factura de proveedor
            # tiene gastos, impuestos y servicios que no entran al inventario.
            # Si fuera obligatorio, habria que inventar un producto "varios"
            # para que el renglon se pueda guardar, y ese producto terminaria
            # con stock real. Vacio significa "este renglon no mueve stock".
            'Producto', 'Nombre Producto',
        ]
        self.ArmaCabeceras(cabeceras=cabecera, formatos=[
            # El orden tiene que ser el de las columnas. Sin esto, "Cantidad",
            # "Neto", "IVA" y "Total" no son columnas numericas para la
            # grilla: se reparten como texto corto y quedan de 56 px, con el
            # importe pegado al borde. Un importe de siete digitos necesita
            # 110 px aunque el encabezado tenga tres letras.
            'Entero',        # Ctro Costos
            'Cantidad',      # Cantidad
            'Moneda',        # Neto
            'Moneda',        # IVA
            'String',        # Detalle
            'String',        # Nombre Ctro Costos
            'Moneda',        # Total
            'Entero',        # Producto
            'String',        # Nombre Producto
        ])
        self.enabled = True
        self.columnasHabilitadas = [0, 1, 2, 3, 4, self.COL_PRODUCTO]
        item = ['', '', '', '', '', '', '', '', '']
        for i in range(8):
            self.AgregaItem(items=item)

    def keyPressEvent(self, event):

        if event.key() == Qt.Key_F2:
            if self.currentColumn() == 0:
                ventana = UiBusqueda()
                ventana.modelo = CentroCosto
                ventana.cOrden = "nombre"  # orden de busqueda
                ventana.limite = 100  # maximo registros a mostrar
                ventana.campos = ["idctrocosto", "nombre"]  # campos a mostrar
                ventana.campoBusqueda = CentroCosto.nombre  # campo sobre el cual realizar la busqueda
                ventana.campoRetorno = CentroCosto.idctrocosto  # campo del cual obtiene el dato para retornar el codigo/valor
                ventana.campoRetornoDetalle = CentroCosto.nombre  # campo que retorna el detalle
                ventana.CargaDatos()
                ventana.exec_()
                if ventana.lRetval:
                    self.ModificaItem(fila=self.currentRow(), col=self.currentColumn(), valor=ventana.ValorRetorno)
                    self.ModificaItem(fila=self.currentRow(), col='Nombre Ctro Costos', valor=ventana.campoRetornoDetalle)

            elif self.currentColumn() == self.COL_PRODUCTO:
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
                    self.ModificaItem(fila=self.currentRow(), col='Producto',
                                     valor=ventana.ValorRetorno)
                    self.ModificaItem(fila=self.currentRow(), col='Nombre Producto',
                                     valor=ventana.campoRetornoDetalle)

        elif event.key() in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
            codigo = self.ObtenerItem(fila=self.currentRow(), col='Ctro Costos')
            try:
                ctro = CentroCosto.get_by_id(codigo)
                self.ModificaItem(fila=self.currentRow(), col='Nombre Ctro Costos',
                                  valor=ctro.nombre)
            except CentroCosto.DoesNotExist:
                pass

            if self.currentColumn() == self.COL_PRODUCTO:
                self._completa_nombre_producto(self.currentRow())

            if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
                if self.currentColumn() >= self.COL_PRODUCTO:
                    self.setCurrentCell(self.currentRow() + 1, 0)
                else:
                    self.setCurrentCell(self.currentRow(), self.currentColumn() + 1)
        super(GrillaFactProv, self).keyPressEvent(event)

    def _completa_nombre_producto(self, fila):
        """Escribe el nombre del producto al elegir el codigo, como el centro
        de costos. Un renglon con el codigo del producto y el nombre vacio se
        ve como un error de tipeo; con los dos llenos, se ve como lo que es."""
        codigo = self.ObtenerItem(fila=fila, col='Producto')
        if not codigo:
            return
        try:
            articulo = Articulo.get_by_id(codigo)
        except Articulo.DoesNotExist:
            return
        self.ModificaItem(fila=fila, col='Nombre Producto', valor=articulo.nombre)


class PercepDGRView(Formulario):

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Carga de percepciones de DGR")
        self.resize(650,550)
        layoutPpal = QVBoxLayout(Form)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        self.gridPercepDGR = Grilla()
        self.gridPercepDGR.enabled = True
        cabeceras = [
            'Codigo', 'Nombre', 'Monto'
        ]
        self.gridPercepDGR.ArmaCabeceras(cabeceras=cabeceras)
        self.gridPercepDGR.columnasHabilitadas = [0, 2]
        items = [
            '', '', ''
        ]
        for x in range(10):
            self.gridPercepDGR.AgregaItem(items=items)

        layoutPpal.addWidget(self.gridPercepDGR)

        layoutBotones = QHBoxLayout()
        self.btnCerrarDGR = BotonCerrarFormulario(autodefault=False)
        layoutBotones.addWidget(self.btnCerrarDGR)
        layoutPpal.addLayout(layoutBotones)
