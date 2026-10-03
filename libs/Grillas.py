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


    def ArmaCabeceras(self, cabeceras=None, formatos=None):

        if not cabeceras:
            cabeceras = self.cabeceras

        self.setColumnCount(len(cabeceras))

        for col in range(0, len(cabeceras)):
            self.setHorizontalHeaderItem(col, QTableWidgetItem(cabeceras[col]))

        self.resizeRowsToContents()
        # NO se usa resizeColumnsToContents: con la tabla vacia (que es como
        # nace, antes de cargar los datos) calcula anchos minimos y el
        # encabezado queda arrancajo a la izquierda, con un mar de blanco al
        # lado. Se reparten los anchos segun el contenido de las cabeceras.
        self._reparte_anchos(cabeceras)
        self._estirar_la_mas_larga(cabeceras)

        # `formatos` es opcional y dice que hay en cada columna, para alinear
        # el encabezado igual que los datos: una columna de importes con el
        # encabezado a la izquierda y los numeros a la derecha se ve rota.
        if formatos:
            for col, tipo in enumerate(formatos):
                if col < len(formatos) and tipo:
                    self.formatos[col] = tipo
            self._alinea_encabezados()

        self.cabeceras = cabeceras
        self.OcultaColumnas()

    def _reparte_anchos(self, cabeceras):
        """Ancho minimo razonable por columna y el sobrante en la primera.

        Se calcula sobre el texto del encabezado, que es lo unico que se
        conoce antes de cargar los datos.
        """
        total = max(self.viewport().width(), 200)
        pesos = [max(60, min(200, len(str(c)) * 9 + 30)) for c in cabeceras]
        suma = float(sum(pesos)) or 1.0
        anchos = [max(56, int(total * p / suma)) for p in pesos]
        # La diferencia se la queda la ultima columna, que suele ser la
        # descripcion larga.
        anchos[-1] += total - sum(anchos)
        for col, ancho in enumerate(anchos):
            if ancho > 0:
                self.setColumnWidth(col, ancho)

    # Columnas cuyo contenido se alinea a la derecha porque se lee como
    # numero. Incluye los tipos declarados al armar el encabezado y los que se
    # descubren al cargar la primera fila.
    TIPOS_NUMERICOS = ('Decimal', 'Cantidad', 'Moneda', 'Importe',
                       'Porcentaje', 'Entero', 'Date', 'Time')

    def _estirar_la_mas_larga(self, cabeceras):
        """El ancho sobrante va a la columna de texto mas larga.

        estirar la ultima columna (que es lo que hace setStretchLastSection)
        deja una columna de importe ocupando media tabla, que es al reves de lo
        que conviene: los importes se comparan entre si en una columna angosta
        y el que se lee es el detalle.
        """
        ancho = self.horizontalHeader()
        ancho.setStretchLastSection(False)
        candidatas = [i for i, c in enumerate(cabeceras)
                      if self.formatos.get(i) not in self.TIPOS_NUMERICOS]
        if not candidatas:
            ancho.setStretchLastSection(True)
            return
        elegida = max(candidatas, key=lambda i: len(str(cabeceras[i])))
        for i in range(len(cabeceras)):
            ancho.setSectionResizeMode(
                i, QHeaderView.Stretch if i == elegida else QHeaderView.Interactive)

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

