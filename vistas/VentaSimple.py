# coding=utf-8
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
                              QGridLayout, QHBoxLayout, QHeaderView, QListWidget,
                              QTableWidget, QTableWidgetItem, QVBoxLayout)

from decimal import Decimal

from libs.Botones import Boton, BotonCerrarFormulario, botonera_dialogo
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla, _formato_importe
from libs.GroupBox import Agrupacion
from libs.Utiles import imagen, icono
from modelos.Formaspago import ComboFormapago


# -- El selector de producto -------------------------------------------------
# El precio al publico va en su PROPIA columna y no pegado al final de la fila.
# Con los importes pegados al codigo de barras hay que contarlos a ojo para
# compararlos; alineados se comparan de verdad, que es lo que el operador
# esta haciendo cuando escribe "acc" y tiene 4 access points delante.
COL_CODIGO = 0
COL_DETALLE = 1
COL_BARRA = 2
COL_PRECIO = 3
CABECERAS_ARTICULOS = ["Código", "Detalle", "Cód. barras", "Precio al público"]

# El ancho se mide contra el contenido (ver `_ancho_para_contenido`), asi que
# estos dos son solo los topes: el piso para que no quede una ventana de
# skeleton y el techo para no pasarse de la pantalla.
ANCHO_MINIMO_SELECTOR = 720
ALTO_SELECTOR = 460


class VentaSimpleCantidadPrecioDialog(Formulario):
    def __init__(self, articulo, cantidad, precio):
        Formulario.__init__(self)
        self.articulo = articulo
        self.setupUi(self)
        self.textCantidad.setText(str(cantidad))
        self.textPrecio.setText(str(precio))

    def setupUi(self, Form):
        self.setWindowTitle("Cantidad y precio")
        self.declara_tamano(420, 160)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.articulo.nombre)
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textPrecio = EntradaTexto(placeholderText="Precio")
        self.layoutDatos.addWidget(Etiqueta(texto="Cantidad"), 0, 0)
        self.layoutDatos.addWidget(self.textCantidad, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Precio"), 1, 0)
        self.layoutDatos.addWidget(self.textPrecio, 1, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textCantidad.proximoWidget = self.textPrecio
        self.textCantidad.returnPressed.connect(self.textPrecio.setFocus)
        self.textPrecio.returnPressed.connect(self.accept)

    def valores(self):
        return self.textCantidad.text(), self.textPrecio.text()


class VentaSimpleAltaClienteDialog(Formulario):
    def __init__(self, busqueda):
        Formulario.__init__(self)
        self.busqueda = busqueda
        self.setupUi(self)
        self.textNombre.setText(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Agregar cliente")
        self.declara_tamano(520, 220)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Agregar cliente")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textNombre = EntradaTexto(placeholderText="Nombre")
        self.textDocumento = EntradaTexto(placeholderText="CUIT/DNI")
        self.textDomicilio = EntradaTexto(placeholderText="Domicilio")
        self.layoutDatos.addWidget(Etiqueta(texto="Nombre"), 0, 0)
        self.layoutDatos.addWidget(self.textNombre, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="CUIT/DNI"), 1, 0)
        self.layoutDatos.addWidget(self.textDocumento, 1, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Domicilio"), 2, 0)
        self.layoutDatos.addWidget(self.textDomicilio, 2, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textNombre.proximoWidget = self.textDocumento
        self.textDocumento.proximoWidget = self.textDomicilio
        self.textDomicilio.returnPressed.connect(self.accept)

    def valores(self):
        return {
            "nombre": self.textNombre.text().strip(),
            "documento": self.textDocumento.text().strip(),
            "domicilio": self.textDomicilio.text().strip(),
        }


class VentaSimpleAltaArticuloDialog(Formulario):
    def __init__(self, busqueda):
        Formulario.__init__(self)
        self.busqueda = busqueda
        self.setupUi(self)
        self.textNombre.setText(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Agregar articulo")
        self.declara_tamano(520, 220)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Agregar articulo")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textNombre = EntradaTexto(placeholderText="Nombre")
        self.textPrecio = EntradaTexto(placeholderText="Precio")
        self.textIva = EntradaTexto(placeholderText="IVA")
        self.textCodigoBarra = EntradaTexto(placeholderText="Código de barras")
        self.textPrecio.setText("0.00")
        self.textIva.setText("21")
        self.layoutDatos.addWidget(Etiqueta(texto="Nombre"), 0, 0)
        self.layoutDatos.addWidget(self.textNombre, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Precio"), 1, 0)
        self.layoutDatos.addWidget(self.textPrecio, 1, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="IVA"), 2, 0)
        self.layoutDatos.addWidget(self.textIva, 2, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Código barras"), 3, 0)
        self.layoutDatos.addWidget(self.textCodigoBarra, 3, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textNombre.proximoWidget = self.textPrecio
        self.textPrecio.proximoWidget = self.textIva
        self.textIva.proximoWidget = self.textCodigoBarra
        self.textCodigoBarra.returnPressed.connect(self.accept)

    def valores(self):
        return {
            "nombre": self.textNombre.text().strip(),
            "precio": self.textPrecio.text().strip(),
            "iva": self.textIva.text().strip(),
            "codbarra": self.textCodigoBarra.text().strip(),
        }


class VentaSimpleSeleccionClienteDialog(Formulario):
    """Elegir un cliente de los que coinciden con lo que se escribio.

    Recibe COMO buscar, no la lista: el buscador se vuelve a consultar cada vez
    que se escribe, que es lo que hace falta cuando hay miles de clientes. Con
    la lista ya armada no habia forma de acotar sin cerrar el dialogo y volver
    a escribir desde la venta.
    """

    def __init__(self, buscador, busqueda=""):
        Formulario.__init__(self)
        self.buscador = buscador          # callable(texto) -> (clientes, total)
        self.busqueda_inicial = busqueda
        self.clientes = []
        self.total = 0
        self.cliente = None
        self.setupUi(self)
        self.buscar(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccionar cliente")
        self.resize(560, 420)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Seleccionar cliente")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.txtBuscar = EntradaTexto(
            placeholderText="Buscar por nombre, CUIT o DNI")
        self.txtBuscar.setObjectName("txtBuscar")
        self.txtBuscar.setText(self.busqueda_inicial)
        self.txtBuscar.textChanged.connect(self.buscar)
        self.txtBuscar.returnPressed.connect(self._elegir_para_entrar)
        self.layoutPpal.addWidget(self.txtBuscar)

        self.listaClientes = QListWidget()
        self.listaClientes.itemDoubleClicked.connect(self.accept)
        self.layoutPpal.addWidget(self.listaClientes)

        # Sin esto no hay forma de saber si la lista esta completa o recortada:
        # con 800 coincidencias y 100 filas, ver 100 no dice si falta nada.
        self.lblCuenta = Etiqueta("")
        self.lblCuenta.setObjectName("lblCuenta")
        self.layoutPpal.addWidget(self.lblCuenta)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def buscar(self, texto):
        """Vuelve a consultar y redibuja la lista."""
        self.clientes = []
        self.listaClientes.clear()

        texto = str(texto or "").strip()
        if not texto:
            # Volcar todos los clientes no es una busqueda: es una pantalla
            # imposible de usar, y ademas esconde que hay que acotar.
            self.lblCuenta.setText("Escribi para buscar entre los clientes.")
            return

        self.clientes, self.total = self.buscador(texto)
        for cliente in self.clientes:
            documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
            self.listaClientes.addItem("{} - {} - {}".format(
                cliente.idcliente, cliente.nombre, documento))
        # Igual que en articulos: con una sola se marca sola, con varias no.
        # Dos clientes con nombres parecidos existen, y elegir el de arriba
        # sin que nadie lo elija es cobrarle al cliente equivocado.
        if len(self.clientes) == 1:
            self.listaClientes.setCurrentRow(0)

        if self.total > len(self.clientes):
            self.lblCuenta.setText(
                "Mostrando {} de {} coincidencias. Seguí escribiendo para acotar.".format(
                    len(self.clientes), self.total))
        elif self.total > 1:
            self.lblCuenta.setText(
                "{} coincidencias. Elegí una con las flechas o el mouse.".format(
                    self.total))
        else:
            self.lblCuenta.setText(
                "{} coincidencia{}".format(self.total, "" if self.total == 1 else "s"))

    def _elegir_para_entrar(self):
        """Enter elige lo marcado. Sin nada marcado, no hace nada.

        Antes tomaba la fila 0 por las dudas, que con varias coincidencias
        era decidirle al operador a cuál cliente se le cobra.
        """
        if self.listaClientes.currentRow() < 0:
            return
        self.accept()

    def accept(self):
        fila = self.listaClientes.currentRow()
        if fila < 0 or fila >= len(self.clientes):
            return
        self.cliente = self.clientes[fila]
        Formulario.accept(self)


class VentaSimpleSeleccionArticuloDialog(Formulario):
    """Elegir un articulo del catalogo, sin tener que acordarse el nombre.

    Es el hermano de VentaSimpleSeleccionClienteDialog y existe por el mismo
    motivo: con el campo de producto vacio, Enter tiene que hacer algo util, y
    lo util es abrir el catalogo. Antes decia "Ingrese un producto", que es un
    aviso de que no se entendio que hacer.

    Recibe COMO buscar, no la lista, por la misma razon que el de clientes: el
    buscador se vuelve a consultar cada vez que se escribe, que es lo que hace
    falta cuando hay catalogo de verdad y no dos articulos de prueba.
    """

    def __init__(self, buscador, busqueda=""):
        Formulario.__init__(self)
        self.buscador = buscador          # callable(texto) -> (articulos, total)
        self.busqueda_inicial = busqueda
        self.articulos = []
        self.total = 0
        self.articulo = None
        # El ancho se mide una sola vez, contra la primera busqueda. Ver
        # `_ajustar_ancho_una_vez`.
        self._ancho_ya_calculado = False
        self.setupUi(self)
        self.buscar(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccionar producto")
        self.resize(ANCHO_MINIMO_SELECTOR, ALTO_SELECTOR)
        # El ancho definitivo lo calcula `buscar` con el contenido de esta
        # busqueda, una sola vez. `resize` de arriba es el piso.

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Seleccionar producto")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.txtBuscar = EntradaTexto(
            placeholderText="Buscar por nombre, código o código de barras")
        self.txtBuscar.setObjectName("txtBuscar")
        self.txtBuscar.setText(self.busqueda_inicial)
        self.txtBuscar.textChanged.connect(self.buscar)
        self.txtBuscar.returnPressed.connect(self._elegir_para_entrar)
        self.layoutPpal.addWidget(self.txtBuscar)

        # QTableWidget y no QListWidget porque la fila tiene que decir mas de
        # una cosa: nombre, codigo de barras y PRECIO. En una lista el precio
        # era texto pegado al final, sin alinear, imposible de comparar.
        self.listaArticulos = QTableWidget(0, len(CABECERAS_ARTICULOS))
        self.listaArticulos.setObjectName("listaArticulos")
        self.listaArticulos.setHorizontalHeaderLabels(CABECERAS_ARTICULOS)
        # Un selector no se edita. Si el operador escribiera en una celda se
        # llevaria un articulo con el precio que se invento de tipear, y sin
        # ningun aviso: en una venta eso es cobrar cualquier cosa.
        self.listaArticulos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Filas enteras y una sola eleccion: elegir una fila es elegir el
        # articulo, no una celda suelta. Con celdas sueltas el operador
        # marcaba el precio y Aceptar no cerraba, porque currentRow() daba -1.
        self.listaArticulos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.listaArticulos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listaArticulos.verticalHeader().setVisible(False)
        self.listaArticulos.itemDoubleClicked.connect(self.accept)

        # Solo el Detalle se estira. Las otras tres columnas tienen un ancho que
        # ya se sabe (un codigo, un codigo de barras, un importe) y con Stretch
        # en la ultima el precio se comeria media ventana.
        cabecera = self.listaArticulos.horizontalHeader()
        for columna in (COL_CODIGO, COL_BARRA, COL_PRECIO):
            cabecera.setSectionResizeMode(columna, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(COL_DETALLE, QHeaderView.Fixed)
        cabecera.setStretchLastSection(False)
        # El ancho de Detalle lo pone `_ancho_para_contenido`, y va FIJO a
        # proposito. Con `Stretch` Qt toma el ancho del contenido como minimo
        # del layout, y un layout con minimo grande empuja la ventana: el
        # dialogo crecia solo cada vez que aparecia un nombre mas largo, que es
        # justo lo contrario de "se mide una vez al abrir". Fijo, el unico que
        # decide el ancho es el `resize` de `_ajustar_ancho_una_vez`.
        cabecera.setMinimumSectionSize(60)
        # La columna de importes con el titulo pegado a la izquierda y los
        # numeros a la derecha se ve rota: el titulo se alinea como los datos.
        cabecera_item = self.listaArticulos.horizontalHeaderItem(COL_PRECIO)
        if cabecera_item is not None:
            cabecera_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layoutPpal.addWidget(self.listaArticulos)

        # Igual que en el de clientes: con la lista recortada hay que poder
        # decir cuantas hay de verdad, o 100 filas no dicen si falta algo.
        self.lblCuenta = Etiqueta("")
        self.lblCuenta.setObjectName("lblCuenta")
        # Wrap, y no por estetica. Un QLabel toma el ancho de su texto como
        # MINIMO del layout, asi que "2 coincidencias. Elegi una con las flechas
        # o el mouse." empujaba el dialogo mas que cualquier columna: la
        # ventana cresia al escribir, y no por el contenido de la lista sino por
        # el aviso de abajo. Con wrap, el mensaje se parte en dos lineas y la
        # ventana se queda con el ancho que se midio.
        self.lblCuenta.setWordWrap(True)
        self.layoutPpal.addWidget(self.lblCuenta)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def buscar(self, texto):
        """Vuelve a consultar y redibuja la lista."""
        texto = str(texto or "").strip()

        if not texto:
            # Volcar el catalogo entero no es una busqueda. Ademas, con un
            # catalogo chico uno quiere ver todo, asi que se lo ofrece: los
            # primeros, avisando que hay mas.
            self.articulos, self.total = self.buscador("")
            self._poblar()
            self.lblCuenta.setText(
                "Escribi para acotar. {} producto{} en el catalogo.".format(
                    self.total, "" if self.total == 1 else "s"))
            if self.articulos:
                self.listaArticulos.setCurrentCell(0, COL_DETALLE)
            self._ajustar_ancho_una_vez()
            return

        self.articulos, self.total = self.buscador(texto)
        self._poblar()
        # Con una sola coincidencia se marca sola: no hay nada que decidir y
        # Enter tiene que servir. Con varias NO: ver _elegir_para_entrar.
        if len(self.articulos) == 1:
            self.listaArticulos.setCurrentCell(0, COL_DETALLE)
        else:
            # Sin esto, con 2 o mas la fila 0 puede quedar marcada sola al
            # repintar, que es exactamente el bug que motivo todo esto.
            self.listaArticulos.clearSelection()
        self._ajustar_ancho_una_vez()

        if self.total > len(self.articulos):
            self.lblCuenta.setText(
                "Mostrando {} de {} coincidencias. Seguí escribiendo para "
                "acotar.".format(len(self.articulos), self.total))
        elif self.total > 1:
            # Sin esta frase el operador cree que el de arriba ya esta
            # elegido, y es justo lo que paso: escribia "w" y se llevaba el
            # primero de los dos WHEY CUTTER.
            self.lblCuenta.setText(
                "{} coincidencias. Elegí una con las flechas o el mouse.".format(
                    self.total))
        else:
            self.lblCuenta.setText(
                "{} coincidencia{}".format(
                    self.total, "" if self.total == 1 else "s"))

    def _poblar(self):
        """Vuelca `self.articulos` en la grilla, una fila por articulo.

        `setRowCount(0)` antes no es cosmetica: es lo que baja la fila
        marcada. QTableView recuerda la fila actual entre un repintado y el
        siguiente, asi que sin esto, escribir una letra mas con 2 coincidencias
        dejaba la fila 0 elegida sola otra vez.
        """
        self.listaArticulos.setRowCount(0)
        self.listaArticulos.clearSelection()
        self.listaArticulos.setRowCount(len(self.articulos))

        for fila, articulo in enumerate(self.articulos):
            for columna in range(len(CABECERAS_ARTICULOS)):
                celda = QTableWidgetItem(self._celda_texto(articulo, columna))
                if columna == COL_PRECIO:
                    celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.listaArticulos.setItem(fila, columna, celda)

    def _celda_texto(self, articulo, columna):
        if columna == COL_CODIGO:
            return str(articulo.idarticulo)
        if columna == COL_DETALLE:
            return str(articulo.nombre or "")
        if columna == COL_BARRA:
            return str(articulo.codbarra or "")
        return self._precio_texto(articulo)

    def _precio_texto(self, articulo):
        """El precio al publico como se lee en Argentina, o vacio si no hay.

        OJO: `_formato_importe(None)` no da un importe, devuelve el TEXTO
        "None". Un articulo viejo sin precio cargado se veria como si costara
        "None", que parece un dato roto y no un dato que falta. Por eso el
        None se bankea aca, antes de formatear.
        """
        try:
            precio = articulo.preciopub
        except AttributeError:
            return ""
        if precio is None:
            return ""
        return _formato_importe(precio)

    # -- Ancho ----------------------------------------------------------------
    # Por que se mide y no se elige un numero
    # --------------------------------------
    # El reporte decia "que sea mas ancho" con dos capturas: una del selector
    # ya estirado a mano a ~950 px y la fila de 110 caracteres que el operador
    # estaba intentando leer. Con el `resize(560, 420)` de antes, a 560 px
    # entraba la mitad del nombre y habia que arrastrar la ventana cada vez,
    # porque `resize` corre en cada construccion y no recuerda nada.
    #
    # Un numero inventado ("pongamosle 900") se desarma apenas aparezca un
    # nombre de 120 caracteres. Asi que el ancho sale de medir el texto de las
    # celdas con la fuente real de la grilla.

    ANCHO_POR_COLUMNA = 24   # el padding que Qt deja a los lados de cada celda

    def _ancho_para_contenido(self):
        """El ancho de cada columna, y el total que hace falta para todas.

        Devuelve el total y ademas deja la columna Detalle con el ancho medido,
        porque es `Fixed`: si no se lo pone aca, Qt le pone el del contenido
        y la ventana se vuelve a mover sola.
        """
        if not self.articulos:
            return None

        metrics = QFontMetrics(self.listaArticulos.font())
        anchos = []
        for columna, titulo in enumerate(CABECERAS_ARTICULOS):
            # Se mide el titulo tambien: "Precio al publico" es mas largo que
            # varios precios de dos decimales, y una columna que no entra
            # muestra "Preci..." en lugar del precio.
            mayor = metrics.horizontalAdvance(titulo)
            for articulo in self.articulos:
                ancho_texto = metrics.horizontalAdvance(
                    self._celda_texto(articulo, columna))
                if ancho_texto > mayor:
                    mayor = ancho_texto
            anchos.append(mayor + self.ANCHO_POR_COLUMNA)

        self.listaArticulos.setColumnWidth(COL_DETALLE, anchos[COL_DETALLE])

        # Las otras tres las pone `ResizeToContents` apenas tienen contenido, y
        # eso es exacto: no hay nada que adivinar.
        return sum(anchos)

    def _ancho_maximo(self):
        """El tope NO esta aca: lo aplica `Formulario.ajusta_tamano`.

        Ese metodo corre en el `showEvent`, una sola vez, y ya hace tres cosas
        queangian el ancho final: piso de 900x560 (porque este dialogo ahora
        tiene una QTableWidget dentro y entra en la clase "con grilla"), el
        `minimumSizeHint` del layout, y el tope del 92% de la pantalla. Por eso
        este metodo no trae el suyo: dos topes distintos terminarian peleandose
        y el menor gana siempre, que es el unico resultado que no explica nada.

        Queda como metodo porque los tests lo pisan para poder medir el ancho
        con contenido, que si no en `offscreen` (pantalla de 800 px) el tope
        muerde siempre y todo queda en 720.
        """
        return 10 ** 6

    def _ajustar_ancho_una_vez(self):
        """El ancho se calcula una sola vez, al abrir.

        Medir en cada tecla haría que la ventana crezca y se achique mientras
        se escribe: el Detalle se estira a medida que el texto que se busca se
        parece menos a los nombres largos, y eso se lee como que la pantalla
        anda sola. Una vez al abrir es estable, y el operador puede estirarla
        a mano si quiere.

        El `resize` de aca es una peticion: la ultima palabra la tiene
        `Formulario.ajusta_tamano`, que en el primer `show` agranda hasta que
        el contenido entre y lo recorta al 92% de la pantalla.
        """
        if self._ancho_ya_calculado:
            return
        self._ancho_ya_calculado = True

        ancho = self._ancho_para_contenido()
        if ancho is None:
            return
        self.resize(max(ANCHO_MINIMO_SELECTOR, min(ancho, self._ancho_maximo())),
                    self.height())

    def _elegir_para_entrar(self):
        """Enter elige lo marcado, y solo si hay algo marcado.

        Antes se llamaba _aceptar_primero y hacia setCurrentRow(0) si no
        habia nada marcado. Con un catalogo donde dos productos se parecen
        (dos "WHEY CUTTER ..." que difieren en el sabor) eso era elegir por
        el operador: el que estaba de arriba. Ahora, sin nada marcado, Enter
        no hace nada y el operador tiene que elegir a proposito.
        """
        if self.listaArticulos.currentRow() < 0:
            return
        self.accept()

    def accept(self):
        """Aceptar requiere una fila elegida.

        Con varias coincidencias y nada marcado, Aceptar no cierra: si
        cerrara, el articulo quedaria en None y el controlador lo tomaria
        como "no elegiste nada", que no es lo que el operador quiso.
        """
        fila = self.listaArticulos.currentRow()
        if fila < 0 or fila >= len(self.articulos):
            return
        self.articulo = self.articulos[fila]
        Formulario.accept(self)


class VentaSimpleView(Formulario):
    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Nueva venta")
        self.resize(980, 640)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Nueva venta")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.agrupaCliente = Agrupacion(titulo="Cliente")
        self.layoutCliente = QGridLayout()
        self.checkConsumidorFinal = QCheckBox("Consumidor final")
        self.checkConsumidorFinal.setChecked(True)
        self.textCliente = EntradaTexto(placeholderText="Buscar cliente por nombre, CUIT o DNI")
        self.textDocumento = EntradaTexto(placeholderText="CUIT/DNI")
        self.layoutCliente.addWidget(self.checkConsumidorFinal, 0, 0)
        self.layoutCliente.addWidget(Etiqueta(texto="Cliente"), 0, 1)
        self.layoutCliente.addWidget(self.textCliente, 0, 2)
        self.layoutCliente.addWidget(Etiqueta(texto="Documento"), 0, 3)
        self.layoutCliente.addWidget(self.textDocumento, 0, 4)
        self.agrupaCliente.setLayout(self.layoutCliente)
        self.layoutPpal.addWidget(self.agrupaCliente)

        self.agrupaArticulo = Agrupacion(titulo="Agregar producto")
        self.layoutArticulo = QGridLayout()
        self.textArticulo = EntradaTexto(placeholderText="Código, nombre o código de barras")
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textCantidad.setText("1")
        self.btnAgregar = Boton(texto="Agregar", imagen=icono('nuevo'), tamanio=QSize(16, 16), autodefault=False)
        self.layoutArticulo.addWidget(Etiqueta(texto="Producto"), 0, 0)
        self.layoutArticulo.addWidget(self.textArticulo, 0, 1)
        self.layoutArticulo.addWidget(Etiqueta(texto="Cantidad"), 0, 2)
        self.layoutArticulo.addWidget(self.textCantidad, 0, 3)
        self.layoutArticulo.addWidget(self.btnAgregar, 0, 4)
        self.agrupaArticulo.setLayout(self.layoutArticulo)
        self.layoutPpal.addWidget(self.agrupaArticulo)

        self.gridVenta = Grilla(tamanio=10)
        # Se declara que hay en cada columna. Sirve para dos cosas: alinear el
        # encabezado igual que los datos (una columna de importes con el
        # titulo a la izquierda y los numeros a la derecha se ve rota) y
        # mostrar cada tipo con sus decimales. "Cant." queda angosta porque el
        # ancho se reparte segun el encabezado, y antes se comia media fila.
        #
        # La columna Stock va cuarta, entre Detalle y Unitario: es un dato del
        # producto y tiene que leerse pegado al producto. Insertarla al final
        #eria mas simple, pero la dejaria separada de lo que describe.
        #
        # OJO con `columnasHabilitadas`: son INDICES, no nombres. Al insertar
        # Stock en el medio, Unitario pasa de 3 a 4 e IVA de 4 a 5, asi que la
        # lista de editables se corre con ella. Stock queda fuera a proposito:
        # el stock es derivado de los movimientos, y si se pudiera escribir ahi
        # un numero se creeria que el inventario cambio sin que exista ningun
        # movimiento que lo diga.
        self.gridVenta.ArmaCabeceras(
            cabeceras=["Cant.", "Codigo", "Detalle", "Stock", "Unitario", "IVA",
                       "SubTotal"],
            formatos=["Cantidad", "String", "String", "Cantidad", "Moneda",
                      "Entero", "Moneda"])
        self.gridVenta.enabled = True
        self.gridVenta.columnasHabilitadas = [0, 1, 2, 4, 5]
        self.gridVenta.textoVacio = "Todavía no hay productos en la venta.\nBuscá uno arriba y presioná Agregar."
        self.layoutPpal.addWidget(self.gridVenta)

        self.layoutTotales = QHBoxLayout()
        self.cboFormaPago = ComboFormapago()
        self.cboFormaPago.setCurrentIndex(self.cboFormaPago.findData("1"))
        # Solo lectura y NO deshabilitado. `enabled=False` llama
        # `setEnabled(False)`, y Qt pinta un widget deshabilitado con la
        # paleta de inactivo: el total salia gris, como un campo de
        # formulario que no se puede tocar, al lado del boton
        # "Emitir factura". Ademas no deja seleccionar el texto, y un
        # operador que necesita pasarlo por whatsapp no lo puede copiar.
        #
        # `setReadOnly(True)` conserva lo que importa: no se puede
        # escribir a mano el total de una venta.
        self.textTotal = EntradaTexto(tamanio=16, alineacion="DERECHA")
        self.textTotal.setReadOnly(True)
        self.textTotal.setText(_formato_importe(Decimal("0")))
        self.layoutTotales.addWidget(Etiqueta(texto="Forma de pago"))
        self.layoutTotales.addWidget(self.cboFormaPago)
        # Cuotas de la tarjeta (issue #37). Solo se muestra cuando la forma
        # elegida tiene planes; con EFECTIVO queda escondido.
        self.lblCuotas = Etiqueta(texto="Cuotas")
        self.cboCuotas = QComboBox()
        self.cboCuotas.setFixedWidth(130)
        self.lblCuotas.setVisible(False)
        self.cboCuotas.setVisible(False)
        self.layoutTotales.addWidget(self.lblCuotas)
        self.layoutTotales.addWidget(self.cboCuotas)
        self.layoutTotales.addWidget(Etiqueta(texto="Total"))
        self.layoutTotales.addWidget(self.textTotal)
        self.layoutPpal.addLayout(self.layoutTotales)

        self.layoutBotones = QHBoxLayout()
        # Jerarquia de la barra de accion: emitir es lo que el usuario vino a
        # hacer, borrar un renglon es lo que no quiere tocar por error y cerrar
        # es salir sin hacer nada. Antes los tres se veian iguales.
        self.btnEmitir = Boton(texto="Emitir factura", imagen=icono('guardar'),
                               autodefault=False, estilo="primario")
        self.btnPresupuesto = Boton(texto="Guardar presupuesto", imagen=icono('nuevo'),
                                    autodefault=False)
        self.btnBorrar = Boton(texto="Borrar renglón", imagen=icono('borrar'),
                               tamanio=QSize(32, 32), autodefault=False, estilo="peligro")
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnEmitir)
        self.layoutBotones.addWidget(self.btnPresupuesto)
        self.layoutBotones.addStretch(1)
        self.layoutBotones.addWidget(self.btnBorrar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)
