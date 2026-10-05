# coding=utf-8
import datetime
import decimal
import re

import xlsxwriter
from PyQt5 import QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QFileDialog, QAbstractItemView, QHeaderView, QLabel

from openpyxl.reader.excel import load_workbook

from libs import Ventanas
from libs.Utiles import EsVerdadero, AbrirArchivo, saveFileDialog


def _a_numero_texto(texto):
    """Convierte a float un numero escrito como lo muestra la grilla.

    Necesario porque las celdas se van a mostrar con separador de miles y coma
    decimal (1.234.567,89), que es como se lee un importe en Argentina, y el
    codigo que needs convertirlas a float tiene que entender las dos formas.

    Antes se hacia con re.sub("[^0123456789\\.]", "", texto), que con un
    separador de miles converts "1.234,56" en 1.23456 sin avisar: todos los
    totales de la factura quedaban mal y no se veía ningun error.
    """
    if texto is None:
        return 0
    if isinstance(texto, (int, float)):
        return float(texto)
    limpio = str(texto).strip()
    if not limpio:
        return 0
    limpio = limpio.replace(" ", "").replace("$", "").replace("%", "")

    tiene_coma = "," in limpio
    tiene_punto = "." in limpio

    if tiene_coma and tiene_punto:
        # El ultimo separador que aparece es el decimal.
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif tiene_coma:
        # Solo coma: puede ser miles ("1,234") o decimal ("1,5"). Con mas de
        # tres digitos despues es miles, que es el caso normal en Argentina.
        partes = limpio.split(",")
        if len(partes) == 2 and len(partes[1]) == 3:
            limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(",", ".")
    elif tiene_punto:
        # Solo punto, sin coma. En el formato argentino el punto es el separador
        # de miles, asi que "1.234" son mil doscientos treinta y cuatro.
        # Y no hay ambiguedad con 1.234 decimal porque el formateador escribe
        # ese caso como "1,23", con coma.
        partes = limpio.split(".")
        if len(partes) == 2 and len(partes[1]) == 3:
            limpio = limpio.replace(".", "")
    return float(limpio)


def _formato_importe(valor, decimales=2):
    """Muestra un importe como se lee en Argentina: 1.234.567,89.

    Solo es presentacion. El valor real queda guardado aparte en la celda, asi
    que los calculos no cambian.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    negativo = numero < 0
    absoluto = abs(numero)
    # Se separa la parte entera de la decimal a mano porque aca el separador
    # de miles es el punto y el decimal la coma, al reves del formato de Python.
    entero = int(absoluto)
    resto = absoluto - entero
    con_miles = "{:,.0f}".format(entero)
    con_miles = con_miles.replace(",", ".")
    fraccion = "{:.{}f}".format(resto, decimales).split(".")[1]
    return "{}{},{}".format("-" if negativo else "", con_miles, fraccion)


def _formato_cantidad(valor, decimales=2):
    """Muestra una cantidad sin ceros de mas: 2, 1,5 y 150.

    Una cantidad con los dos decimales siempre ("2,00", "150,00") es ruido:
    el usuario tiene que mirar si hay algo detras de la coma para saber si
    es entera o no. Los importes si llevan los dos decimales siempre, que es
    como se escriben los montos.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    texto = "{:.{}f}".format(abs(numero), decimales)
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
        if not texto:
            texto = "0"
        texto = texto.replace(".", ",")
    return ("-" if numero < 0 else "") + texto


class Grilla(QTableWidget):

    #columnas a ocultar
    columnasOcultas = []

    #lista con las cabeceras de la grilla
    cabeceras = []

    #tabla desde la cual obtener los datos
    tabla = None

    #campos de la tabla
    campos = None

    #condiciones para filtrar los datos
    condiciones = None

    #cantidad de registros a mostrar
    limite = 100

    #columnas habilitadas
    columnasHabilitadas = []

    #campos tabla
    camposTabla = None

    #valores a cargar
    data = None

    #indica si esta en la grilla
    engrilla = False

    #indica si las columnas son seleccionables o no
    enabled = False

    #widget para las columnas
    widgetCol = {}

    #color para la columna
    backgroundColorCol = {}

    #tamaño de la fuente
    tamanio = 12

    #emit signal
    keyPressed = QtCore.pyqtSignal(int)
    
    #formatos de las columnas
    formatos = {}

    def __init__(self, *args, **kwargs):

        QTableWidget.__init__(self, *args)

        # Los diccionarios y listas de clase son COMPARTIDOS entre todas las
        # grillas. Con formatos como atributo de clase, la tabla de la venta
        # dejaba sus tipos (Cantidad, Moneda...) en la de proveedores, que
        # abria despues en la misma corrida: ahi una columna de texto se
        # alineaba como numero. Se copian a la instancia para que cada tabla
        # tenga lo suyo.
        self.formatos = dict(self.formatos)
        self.cabeceras = list(self.cabeceras)
        self.columnasOcultas = list(self.columnasOcultas)
        self.columnasHabilitadas = list(self.columnasHabilitadas)
        self.widgetCol = dict(self.widgetCol)
        self.backgroundColorCol = dict(self.backgroundColorCol)
        # Para que resizeEvent sepa si vale la pena volver a repartir. Ver
        # resizeEvent: sin esto se recalcula en cada pixel del drag.
        self._ancho_del_ultimo_reparto = 0
        # Nombre de la columna de texto que se lleva el sobrante. Por defecto
        # gana la de nombre mas largo; una grilla puede fijar cual es (la de
        # detalle de una factura, que es la que el operador lee).
        self.columna_preferida = ""

        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        if 'habilitarorden' in kwargs:
            self.setSortingEnabled(kwargs['habilitarorden'])
        else:
            self.setSortingEnabled(True)

        # Estado vacio: una tabla sin filas es un rectangulo blanco enorme, y
        # no dice si esta cargando, si fallo la consulta o si de verdad no hay
        # nada. El cartel se pone y se saca solo segun la cantidad de filas,
        # asi que ningun controlador tiene que acordarse de updatedarlo.
        self._textoVacio = ""
        self._etiquetaVacia = QLabel(self.viewport())
        self._etiquetaVacia.setAlignment(Qt.AlignCenter)
        self._etiquetaVacia.setWordWrap(True)
        self._etiquetaVacia.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._etiquetaVacia.setStyleSheet(
            "color: #8A97A4; background: transparent; font-size: 13px;")

        if 'textoVacio' in kwargs:
            self.textoVacio = kwargs['textoVacio']
        else:
            self._actualiza_vacio()
        # self.itemClicked.connect(self.handleItemClicked)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)#para que se pueda editar el contenido con solo un click
        
        if 'enabled' in kwargs:
            self.enabled = kwargs['enabled']
        else:
            self.enabled = True

        self.setEnabled(self.enabled)

        # Filas alternadas: es la regla que define el tema para poder
        # distinguir una fila de otra al leer many columnas. Sin esto el color
        # del tema no se ve.
        self.setAlternatingRowColors(True)
        # Encabezado fijo: en tablas largas de datos fiscales, perder de vista
        # cual es cada columna al bajar es el problema clasico.
        self.verticalHeader().setVisible(False)

    def _actualiza_vacio(self):
        vacia = (self.rowCount() == 0 and bool(self.textoVacio))
        self._etiquetaVacia.setText(self.textoVacio if vacia else "")
        self._etiquetaVacia.setVisible(vacia)
        if vacia:
            self._etiquetaVacia.setGeometry(self.viewport().rect())

    # Texto del estado vacio. Es una propiedad y no un atributo a proposito:
    # casi todas las vistas lo asignan DESPUES de crear la grilla (ArmaCabeceras
    # y demas van antes), y con un atributo comun el cartel se calcularia con
    # el texto todavia vacio y no volveria a actualizarse.
    @property
    def textoVacio(self):
        return self._textoVacio

    @textoVacio.setter
    def textoVacio(self, valor):
        self._textoVacio = valor
        if hasattr(self, "_etiquetaVacia"):
            self._actualiza_vacio()

    def setRowCount(self, filas):
        # Todo lo que carga o borra filas pasa por aca, asi que es el punto
        # unico donde hay que decidir si corresponde el cartel de vacio.
        QTableWidget.setRowCount(self, filas)
        self._actualiza_vacio()

    def resizeEvent(self, *args, **kwargs):
        QTableWidget.resizeEvent(self, *args, **kwargs)
        if self._etiquetaVacia.isVisible():
            self._etiquetaVacia.setGeometry(self.viewport().rect())

        # Volver a repartir los anchos cuando la ventana cambia de ancho.
        #
        # Los anchos se calculan una sola vez, al armar las cabeceras, y en ese
        # momento la grilla todavia no tiene tamano: `_reparte_anchos` se
        # divide por 200 y todas las columnas quedan en su minimo de 56 px. La
        # columna estirada se lleva el sobrante, y el resultado era una columna
        # de 1768 px al lado de cinco de 56.
        #
        # Aca se vuelve a calcular con el ancho real. El margen de 40 px es
        # para no recalcular en cada pixel del drag del borde, que con una
        # grilla de 2000 filas se nota.
        actual = self.viewport().width()
        if abs(actual - self._ancho_del_ultimo_reparto) > 40:
            self._ancho_del_ultimo_reparto = actual
            if self.cabeceras:
                self._reparte_anchos(self.cabeceras)
                self._estirar_la_mas_larga(self.cabeceras)

    def ArmaCabeceras(self, cabeceras=None, formatos=None):

        if not cabeceras:
            cabeceras = self.cabeceras

        self.setColumnCount(len(cabeceras))

        for col in range(0, len(cabeceras)):
            self.setHorizontalHeaderItem(col, QTableWidgetItem(cabeceras[col]))

        self.resizeRowsToContents()

        # `formatos` dice que hay en cada columna. Se aplican ANTES de repartir
        # los anchos, y no despues: el reparto decide cuanto mide una columna a
        # partir de su tipo, asi que si se repartiera todavia sin conocerlos,
        # las columnas de importe se tratarian como texto corto y quedarian de
        # 56 px. Con "Neto", "IVA" y "Total" eso era lo que pasaba en la grilla
        # de carga de compras.
        if formatos:
            for col, tipo in enumerate(formatos):
                if col < len(cabeceras) and tipo:
                    self.formatos[col] = tipo

        # NO se usa resizeColumnsToContents: con la tabla vacia (que es como
        # nace, antes de cargar los datos) calcula anchos minimos y el
        # encabezado queda arrancajo a la izquierda, con un mar de blanco al
        # lado. Se reparten los anchos segun el tipo y el contenido del
        # encabezado.
        self._reparte_anchos(cabeceras)
        self._estirar_la_mas_larga(cabeceras)

        # Y despues se alinean los encabezados, que ya es solo pintar: el
        # ancho ya esta decidido.
        if formatos:
            self._alinea_encabezados()

        self.cabeceras = cabeceras
        self._esconde_columnas_auxiliares(cabeceras)
        self.OcultaColumnas()

    def _esconde_columnas_auxiliares(self, cabeceras):
        """Esconde las columnas que existen solo para guardar el id.

        El proyecto ya tiene esa convencion: una columna que arranca con
        guion bajo (`_id`) es el dato que la fila necesita para guardarse, no
        algo que el operador tenga que leer. Esas columnas se repartian el
        ancho como si fueran datos: `_reparte_anchos` les daba el minimo de 56
        px y quedaban a la vista como una franja de numeros al costado de la
        columna que si importa.

        Solo se esconden las que arrancan con `_`. Las que se llaman `Id` o
        `idcliente` y son dato real (el codigo de un grupo, el CUIT) se
        siguen viendo: ocultar un id que el operador usa seria peor que
        dejarlo angosto.
        """
        for col, nombre in enumerate(cabeceras):
            if str(nombre).startswith("_"):
                self.hideColumn(col)

    def _columna_es_de_texto(self, indice, nombre):
        """Esta columna se lee como texto, y por lo tanto se estira?

        Tres cosas la hacen NO texto: que el tipo declarado sea numerico, que
        el encabezado empiece con `_` (columna auxiliar) y que el nombre
        empiece con "id".

        La de "id" es la que faltaba. Con la tabla vacia --que es como nace y
        como se ve en un ABM sin datos-- no hay tipo declarado ni primera
        fila de donde deducirlo, asi que "Idcliente" era indistinguible de
        "Nombre" y se llevaba el ancho sobrante: 555 de 959 px, con el nombre
        partido en dos renglones al lado. Un identificador se lee entero en
        cuatro digitos; estirarlo no aporta nada.
        """
        if self.formatos.get(indice) in self.TIPOS_NUMERICOS:
            return False
        limpio = str(nombre).strip().lower()
        return not (limpio.startswith("_") or limpio.startswith("id"))

    def _reparte_anchos(self, cabeceras):
        """Ancho minimo razonable por columna y el sobrante en la primera.

        Se calcula sobre el texto del encabezado, que es lo unico que se
        conoce antes de cargar los datos.

        Sin columnas no hay nada que repartir, y `anchos[-1]` sobre una lista
        vacia es un IndexError. Pasaba con un ABM cuyo `camposAMostrar` esta
        vacio: `vistas/ABM.py` arma `cabeceras = []` en ese caso, y abrir la
        pantalla tiraba. Que la pantalla este vacia es un problema de esa
        pantalla; que se caiga al abrir es de esta linea.
        """
        if not cabeceras:
            return

        # Todo a Interactive antes de medir. Con una seccion en Stretch el
        # ancho lo impone Qt y `setColumnWidth` no la toca: el ancho de la
        # corrida anterior se queda pegado y esta cuenta no cierra. Es lo
        # mismo que hace `_reporte_anchos_con_datos`, y por el mismo motivo.
        encabezado = self.horizontalHeader()
        encabezado.setStretchLastSection(False)
        for col in range(len(cabeceras)):
            encabezado.setSectionResizeMode(col, QHeaderView.Interactive)

        total = max(self.viewport().width(), 200)

        # El reparto va por TIPO de columna, no por la longitud del encabezado.
        #
        # Antes el peso era `len(encabezado) * 9` para todas, asi que
        # "Idcliente" (9 letras) pesaba mas que "Nombre" (6) y el codigo se
        # llevaba la mitad de la tabla con los nombres cortados al lado. Un
        # identificador son cuatro digitos, mida lo que mida su nombre.
        #
        # Y repartirlo todo proporcionalmente hace que dos columnas nunca
        # puedan quedar tan desiguales como hace falta: con "Idcliente" y
        # "Nombre" salen 314 y 645, y 645 no es tres veces 314. Por eso las
        # columnas que NO son texto tienen ancho FIJO segun su tipo, y el
        # sobrante se lo reparten solo las de texto.
        ANCHOS_FIJOS = {
            'Date': 90, 'Time': 80,
            # "Cant." con dos digitos y una coma no necesita 90: son cinco
            # caracteres. Un codigo tampoco. Y con seis columnas, cada diez
            # pixeles que sobra en una fija es diez en la de texto, que es la
            # que se queda sin lugar.
            'Entero': 80, 'Cantidad': 80, 'Porcentaje': 80,
            # Un importe de siete digitos ("1.234.567,89") son once
            # caracteres: 100 alcanza de sobra.
            'Decimal': 100, 'Moneda': 100, 'Importe': 100,
        }
        ANCHO_ID = 100

        anchos = [0] * len(cabeceras)
        de_texto = []
        for i, nombre in enumerate(cabeceras):
            tipo = self.formatos.get(i)
            limpio = str(nombre).strip().lower()
            if limpio.startswith("id") or limpio.startswith("_"):
                anchos[i] = ANCHO_ID
            elif tipo in self.TIPOS_NUMERICOS:
                anchos[i] = ANCHOS_FIJOS.get(tipo, 100)
            else:
                de_texto.append(i)

        # Lo que queda es de las columnas de texto, en proporcion a su
        # encabezado.
        #
        # Si no alcanza para que todas tengan un ancho legible, se recorta a
        # las fijas antes que dejar una columna de texto en 60 px. Con nueve
        # columnas en 884 px las seis fijas se comian 600 y "Detalle" se
        # quedaba con 60: el nombre del producto al lado, y el detalle, que
        # es lo que se lee, ilegible.
        MINIMO_TEXTO = 90
        PISO_FIJO = 72
        # Se calcula antes de la cadena de if: el `elif` lo usa, y con una
        # grilla de solo columnas fijas no hay donde asignarlo adentro.
        sobrante = total - sum(anchos)
        if de_texto:
            while True:
                sobrante = total - sum(anchos)
                faltan = MINIMO_TEXTO * len(de_texto) - sobrante
                if faltan <= 0:
                    break
                recortables = [i for i in range(len(anchos))
                               if i not in de_texto and anchos[i] > PISO_FIJO]
                if not recortables:
                    break
                paso = float(faltan) / len(recortables)
                for i in recortables:
                    anchos[i] = max(PISO_FIJO, int(anchos[i] - paso))

            sobrante = total - sum(anchos)
            pesos = [max(60, min(400, len(str(cabeceras[i])) * 9 + 30))
                     for i in de_texto]
            suma = float(sum(pesos)) or 1.0
            for i, peso in zip(de_texto, pesos):
                anchos[i] = max(MINIMO_TEXTO, int(sobrante * peso / suma)) \
                    if sobrante > 0 else MINIMO_TEXTO
        elif sobrante > 0:
            paso = sobrante / float(len(anchos))
            anchos = [int(a + paso) for a in anchos]
        elif sobrante < 0:
            # No alcanza para todo. La falta se reparte entre todas, para que
            # ninguna quede en negativo y Qt la deje en su minimo. Antes era
            # `anchos[-1] += total - sum(anchos)`, y con nueve columnas en una
            # grilla angosta la ultima se comia -500 px.
            paso = sobrante / float(len(anchos))
            anchos = [max(1, int(a + paso)) for a in anchos]

        for col, ancho in enumerate(anchos):
            if ancho > 0:
                self.setColumnWidth(col, ancho)

    # Columnas cuyo contenido se alinea a la derecha porque se lee como
    # numero. Incluye los tipos declarados al armar el encabezado y los que se
    # descubren al cargar la primera fila.
    TIPOS_NUMERICOS = ('Decimal', 'Cantidad', 'Moneda', 'Importe',
                       'Porcentaje', 'Entero', 'Date', 'Time')

    # Tope de ancho para las columnas que no se leen como texto.
    #
    # Un identificador son cuatro digitos: 120 px alcanzan de sobra. Sin tope,
    # `resizeColumnsToContents` le daba a "Idcliente" 512 de los 959 px de la
    # tabla y los nombres quedaban cortados al lado. Si el dato de una columna
    # de id necesita mas que eso, no es un id, y ahi la columna se va a ver
    # cortada: es preferible a que se coma media tabla.
    ANCHO_MAXIMO_NO_TEXTO = 120

    def _estirar_la_mas_larga(self, cabeceras):
        """La columna de texto mas larga se lleva el ancho sobrante.

        Estirar la ultima columna (que es lo que hace `setStretchLastSection`)
        deja una columna de importe ocupando media tabla, que es al reves de lo
        que conviene: los importes se comparan entre si en una columna angosta
        y el que se lee es el detalle. Con una sola columna estirada, las otras
        conservan la proporcion que les dio `_reparte_anchos`... SI esa
        proporcion se calculo con el ancho real de la tabla. Y no siempre: al
        armar las cabeceras la grilla todavia no tiene tamano, y `_reporte_anchos`
        se divide por 200. Por eso `resizeEvent` vuelve a repartir.
        """
        ancho = self.horizontalHeader()
        ancho.setStretchLastSection(False)
        candidatas = [i for i, c in enumerate(cabeceras)
                      if self._columna_es_de_texto(i, c)]
        if not candidatas:
            ancho.setStretchLastSection(True)
            return
        # Gana la que la grilla pidio, si esta entre las candidatas. Antes
        # ganaba la de nombre mas largo, y en la grilla de la factura eso era
        # "SubTotal" o "Unitario"... no: "Detalle" quedava repartido en
        # proporcion a sus siete letras y se quedaba en 40 px, con el nombre
        # del producto partido en dos lineas.
        elegida = None
        if self.columna_preferida in cabeceras:
            elegida = cabeceras.index(self.columna_preferida)
        if elegida is None or not self._columna_es_de_texto(elegida,
                                                           cabeceras[elegida]):
            elegida = max(candidatas, key=lambda i: len(str(cabeceras[i])))
        for i in range(len(cabeceras)):
            ancho.setSectionResizeMode(
                i, QHeaderView.Stretch if i == elegida else QHeaderView.Interactive)

    def _reparte_anchos_con_datos(self):
        """Reparte los anchos cuando ya se sabe que hay en cada columna.

        Con la tabla vacia (que es como nace) no hay forma de distinguir un
        codigo angosto de una columna de texto larga, asi que se decide por el
        texto del encabezado y gana la que tiene el nombre mas largo. En el
        ABM de clientes eso elegia "Idcliente" (9 letras) por sobre "Nombre"
        (6), y el codigo se llevaba 732 de los 959 px: los nombres quedaban
        cortados en dos renglones con 700 px de blanco al lado.

        Con la primera fila ya se distinguen: un codigo es numerico, y
        `_estirar_la_mas_larga` deja los numericos fuera de las candidatas.
        """
        encabezado = self.horizontalHeader()
        columnas = min(self.columnCount(), len(self.cabeceras))
        # Todo a Interactive antes de medir. Con una seccion en Stretch el
        # ancho lo impone Qt: ni resizeColumnsToContents ni setColumnWidth la
        # tocan, y el codigo se queda con el ancho que le habia tocado antes.
        for col in range(columnas):
            encabezado.setSectionResizeMode(col, QHeaderView.Interactive)
        self.resizeColumnsToContents()
        for col in range(columnas):
            nombre = self.cabeceras[col]
            if self._columna_es_de_texto(col, nombre):
                # El encabezado es lo unico que explica que hay en la
                # columna: si queda mas angosto que su propio texto se lee
                # "Idclien...".
                minimo = max(90, min(220, len(str(nombre)) * 9 + 24))
                ancho = self.columnWidth(col)
                if 0 < ancho < minimo:
                    self.setColumnWidth(col, minimo)
            else:
                # Sin dato, `resizeColumnsToContents` deja la columna en el
                # minimo de Qt (56 px), y el tope de 120 no la mueve: un tope
                # acota, no agranda. Sin este piso, "Neto" e "IVA" de la
                # grilla de compras quedan en 56 px aunque su tipo diga que
                # son importes.
                if self.columnWidth(col) < 90:
                    self.setColumnWidth(col, 90)
                if self.columnWidth(col) > self.ANCHO_MAXIMO_NO_TEXTO:
                    self.setColumnWidth(col, self.ANCHO_MAXIMO_NO_TEXTO)
        self._estirar_la_mas_larga(self.cabeceras)

    def _alinea_encabezados(self):
        for col, tipo in self.formatos.items():
            if col >= self.columnCount():
                continue
            encabezado = self.horizontalHeaderItem(col)
            if encabezado is None:
                continue
            if tipo in self.TIPOS_NUMERICOS:
                encabezado.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                encabezado.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    # Decimales por tipo de columna. Una cantidad y un importe no se muestran
    # igual, y mostrarlos con los mismos decimales hace que el usuario tenga
    # que contar los ceros para saber qué es.
    DECIMALES_POR_TIPO = {
        'Cantidad': 2,
        'Moneda': 2,
        'Importe': 2,
        'Decimal': 2,
        'Porcentaje': 2,
        'Entero': 0,
    }

    def _texto_celda(self, col, valor):
        """Como se muestra el valor, segun el tipo declarado de la columna."""
        tipo = self.formatos.get(col, 'Decimal')
        if tipo == 'Entero':
            try:
                return "{:,.0f}".format(float(valor)).replace(",", ".")
            except (TypeError, ValueError):
                return str(valor)
        if tipo == 'Cantidad':
            # Sin ceros de mas: "2" y no "2,00".
            return _formato_cantidad(valor, self.DECIMALES_POR_TIPO['Cantidad'])
        if tipo in ('Moneda', 'Importe'):
            # Los importes llevan los dos decimales siempre.
            return _formato_importe(valor, self.DECIMALES_POR_TIPO.get(tipo, 2))
        if tipo in ('Decimal', 'Porcentaje'):
            return _formato_importe(valor, self.DECIMALES_POR_TIPO.get(tipo, 2))
        return str(valor)

    def AgregaItem(self, items=None,
                   backgroundColor=None, readonly=False):
        """Agrega una fila.

        `backgroundColor` va en None a proposito. Antes el default era blanco
        y se pintaba celda por celda, lo que tapaba el color alternado que
        define el tema y hacia que cualquier tema distinto del actual se
        viera igual. Quien quiera un color de fondo lo pide explicitamente.
        """

        if items:
            col = 0
            cantFilas = self.rowCount() + 1
            self.setRowCount(cantFilas)
            for x in items:
                flags = QtCore.Qt.ItemIsSelectable
                # Si la columna declara un tipo numerico y el valor llega como
                # texto, se convierte. Hace falta porque casi todos los
                # controladores arman la fila con str(...): sin esto la
                # columna queda como texto, sin alineacion a la derecha y sin
                # separador de miles, por mas que el encabezado diga que es un
                # importe.
                if col in self.formatos and self.formatos[col] in self.TIPOS_NUMERICOS \
                        and isinstance(x, str) and not isinstance(x, bytes):
                    try:
                        x = decimal.Decimal(x)
                    except decimal.InvalidOperation:
                        pass

                if isinstance(x, bool):
                    item = QTableWidgetItem(x)
                    if x:
                        item.setCheckState(QtCore.Qt.Checked)
                    else:
                        item.setCheckState(QtCore.Qt.Unchecked)
                    self.formatos[col] = 'Bool'
                elif isinstance(x, (int, float, decimal.Decimal)):
                    # El tipo se resuelve ANTES de armar el texto, o la
                    # primera fila se formatearia con el tipo por defecto y
                    # las siguientes con el declarado, y una columna
                    # quedaria con "21,00" arriba y "21" abajo.
                    #
                    # Sin tipo declarado se asume Decimal y no se intenta
                    # adivinar: una columna de importes a la que se le pasa un
                    # 0 de arranque (la fila de "Saldo Inicial" de la ficha
                    # del cliente) se volveria "Entero" y ahi los 1.234,56 se
                    # muestran como 1.235. Ver "1,00" de mas en un codigo
                    # molesta; redondear un importe no.
                    if col not in self.formatos:
                        self.formatos[col] = 'Decimal'
                    # El texto de la celda es para MIRAR. El valor real se
                    # guarda aparte en UserRole, porque hay codigo que lee la
                    # celda para sumar: si se guardara solo el texto formateado
                    # con puntos de miles, "1.234,56" se leeria como 1.23456 y
                    # todos los totales quedarian mal sin dar ningun error.
                    item = QTableWidgetItem(self._texto_celda(col, x))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setData(QtCore.Qt.UserRole, x)
                # en caso de que sea formato de fecha
                elif isinstance(x, (datetime.date)):
                    fecha = x.strftime('%d/%m/%Y')
                    item = QTableWidgetItem(fecha)
                    self.formatos[col] = 'Date'
                # en caso de que sea formato de hora
                elif isinstance(x, (datetime.time)):
                    fecha = x.strftime('%H:%M:%S')
                    item = QTableWidgetItem(fecha)
                    self.formatos[col] = 'Time'
                elif isinstance(x, (bytes)):
                    if EsVerdadero(x):
                        item = 'Si'
                    else:
                        item = 'No'
                    item = QTableWidgetItem(QTableWidgetItem(x))
                    self.formatos[col] = 'Bytes'
                else:
                    item = QTableWidgetItem(QTableWidgetItem(x))
                    # No pisa un tipo que la grilla ya declaro, igual que el
                    # caso numerico de mas arriba. Sin esto, la fila de
                    # arranque (vacia) pasaba por el `else` y dejaba todas las
                    # columnas en 'String': en la grilla de compras, "Neto" e
                    # "IVA" declarados como 'Moneda' perdian el tipo al abrir
                    # la pantalla y quedaban con el ancho de un texto corto en
                    # vez del de un importe.
                    if col not in self.formatos:
                        self.formatos[col] = 'String'

                if readonly:
                    flags = QtCore.Qt.ItemIsSelectable
                elif col in self.columnasHabilitadas:
                    if isinstance(x, (bool)):
                        flags |= QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
                    else:
                        flags |= QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                else:
                    if self.enabled and not readonly:
                        flags |= QtCore.Qt.ItemIsEnabled

                item.setFlags(flags)
                if col in self.backgroundColorCol:
                    item.setBackground(self.backgroundColorCol[col])

                if backgroundColor and isinstance(backgroundColor, QColor):
                    item.setBackground(backgroundColor)

                self.setItem(cantFilas - 1, col, item)
                # if self.widgetCol:
                #     self.ArmaWidgetCol(col)
                if col in self.widgetCol:
                    widgetColumna = self.widgetCol[col]
                    self.setItemDelegateForColumn(col, widgetColumna)
                    # self.setItemDelegate(widgetColumna)
                    # self.setCellWidget(cantFilas - 1, col, widgetColumna)
                col += 1
            self.resizeRowsToContents()
            # El ancho se ajusta UNA vez, cuando entra la primera fila. Con
            # datos ya cargados tiene sentido que las columnas midan lo que
            # necesitan; recalcular en cada fila hace que la tabla "tiemble"
            # mientras se carga y ralentiza con muchas filas.
            if cantFilas == 1:
                self.resizeColumnsToContents()
                # Con la primera fila ya se sabe que hay en cada columna, asi
                # que se pueden alinear los encabezados aunque la tabla no haya
                # declarado los tipos: asi todas las tablas de la app quedan
                # bien sin tocar las 30 pantallas una por una.
                self._alinea_encabezados()
                # Y recien ahi se reparte el sobrante: con la tabla vacia no se
                # puede saber que "Idcliente" es un codigo y "Nombre" un texto.
                self._reparte_anchos_con_datos()

    def OcultaColumnas(self):
        for x in self.columnasOcultas:
            self.hideColumn(x)

    def ModificaItem(self, valor, fila, col, backgroundColor=None):
        """

        :param fila: la fila que se quiere modificar
        :param valor: valor a modificar
        :type col: entero en caso de indicar un numero de columna y string si quiero el nombre
        """
        if not isinstance(col, int):
            numCol = self.cabeceras.index(col)
        else:
            numCol = col

        if isinstance(valor, (int, float, decimal.Decimal)):
            # Igual que en AgregaItem: el texto es para mirar y el numero real
            # va aparte, para que los calculos no dependan del formato.
            if numCol not in self.formatos:
                self.formatos[numCol] = 'Decimal'
            item = QTableWidgetItem(self._texto_celda(numCol, valor))
            item.setData(QtCore.Qt.UserRole, valor)
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        else:
            item = QTableWidgetItem(valor)

        if numCol in self.columnasHabilitadas:
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        else:
            # item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setFlags(QtCore.Qt.ItemIsSelectable)

        if col in self.backgroundColorCol:
            item.setBackground(self.backgroundColorCol[col])

        self.setItem(fila, numCol, item)
        self.resizeColumnsToContents()
        # Editar una celda no puede dejar la tabla de nuevo con la columna de
        # codigo ocupando media pantalla: se vuelve a repartir el sobrante.
        self._reparte_anchos_con_datos()
        #self.dataChanged()

    def ObtenerItem(self, fila, col):

        if isinstance(col, int):
            numCol = col
        else:
            numCol = self.cabeceras.index(col)

        try:
            celda = self.item(fila, numCol)
            # Se lee el valor crudo que se guardo al cargar, no el texto: el
            # texto lleva separador de miles y coma decimal, para que se lea
            # bien, y parsearlo a mano es justo lo que antes dabia malos
            # totales sin avisar.
            crudo = celda.data(QtCore.Qt.UserRole)
            if crudo is not None:
                return crudo
            return celda.text()
        except Exception:
            return 0

    def ObtenerItemNumerico(self, fila, col):

        if isinstance(col, int):
            numCol = col
        else:
            numCol = self.cabeceras.index(col)

        try:
            celda = self.item(fila, numCol)
            if celda is None:
                return 0
            if celda.checkState() == QtCore.Qt.Checked:
                return True
            crudo = celda.data(QtCore.Qt.UserRole)
            if crudo is not None:
                return float(crudo)
            return _a_numero_texto(celda.text())
        except Exception:
            return 0

    def CargaDatos(self, avance=None):

        self.blockSignals(True)
        self.setRowCount(0)
        self.blockSignals(False)

    def focusInEvent(self, *args, **kwargs):
        self.engrilla = True

    def focusOutEvent(self, *args, **kwargs):
        self.engrilla = False

    def ExportaExcel(self, columnas=None, archivo="", titulo="", nuevo=True, hoja='', fila=0, col=0):

        if not columnas:
            columnas = self.cabeceras

        if nuevo:
            archivo = archivo.replace('.', '').replace('/', '')
        if not archivo.startswith("excel"):
            archivo = "excel/" + archivo

        if nuevo:
            cArchivo = saveFileDialog(filename=archivo,
                                      files="Archivos de Excel (*.xlsx)")
        else:
            cArchivo = archivo
        # cArchivo = QFileDialog.getSaveFileName(caption="Guardar archivo", directory="", filter="*.XLSX")
        if not cArchivo:
            return

        if nuevo:
            workbook = xlsxwriter.Workbook(cArchivo)
        else:
            try:
                # Carga el archivo
                workbook = load_workbook(cArchivo)
            except:
                Ventanas.showAlert("Sistema", f"Ocurrio un error al intentar abrir el archivo {cArchivo}")
                return

        if hoja:
            # Selecciona la hoja por su nombre
            worksheet = workbook[hoja]
        else:
            #creamos una hoja nueva
            worksheet = workbook.add_worksheet()

        formato_fecha = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        # fila = 0
        # col = 0
        if titulo:
            worksheet.write(fila, col, titulo)
            fila += 2

        for c in columnas:
            worksheet.write(fila, col, c)
            col += 1

        fila += 1
        for row in range(self.rowCount()):
            col = 0
            for c in columnas:
                indice = c if isinstance(c, int) else self.cabeceras.index(c)

                if self.formatos.get(indice) == 'Date':
                    # Las fechas se guardan como texto; para Excel hay que
                    # pasarlas como fecha, no como numero.
                    texto = self.item(row, indice).text()
                    worksheet.write_datetime(
                        fila, col,
                        datetime.datetime.strptime(texto, '%d/%m/%Y').date(),
                        formato_fecha)
                    col += 1
                    continue

                dato = self.ObtenerItem(fila=row, col=c)
                if isinstance(dato, bool):
                    worksheet.write(fila, col, 'SI' if dato else 'NO')
                elif isinstance(dato, (int, float, decimal.Decimal)):
                    # Numero: se escribe como numero, que en Excel se puede
                    # sumar. Antes se escribia el texto y la celda quedaba
                    # como texto.
                    worksheet.write(fila, col, float(dato))
                else:
                    texto = str(dato).strip()
                    try:
                        worksheet.write(fila, col, float(_a_numero_texto(texto)))
                    except ValueError:
                        worksheet.write(fila, col, texto)
                col += 1
            fila += 1

        # cabeceras_excel = [{'header': x} for x in columnas]
        # worksheet.add_table(0, 0, fila, col-1, cabeceras_excel)
        workbook.close()
        AbrirArchivo(cArchivo)


    def keyPressEvent(self, event):
        super(Grilla, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())

