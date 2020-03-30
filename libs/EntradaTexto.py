# coding=utf-8
import datetime
import os
import uuid

from PyQt5 import QtCore
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QKeySequence, QIcon, QTextDocument, QImage
from PyQt5.QtWidgets import QLineEdit, QHBoxLayout, QTextEdit, QWidget, QToolBar, QVBoxLayout, QFontComboBox, QAction, \
    QComboBox, QActionGroup, QMessageBox, QFileDialog, QCompleter

from libs import Ventanas
from libs.Etiquetas import Etiqueta
from libs.Utiles import validar_cuit, imagen, GuardarArchivo

FONT_SIZES = [7, 8, 9, 10, 11, 12, 13, 14, 18, 24, 36, 48, 64, 72, 96, 144, 288]
IMAGE_EXTENSIONS = ['.jpg','.png','.bmp']
HTML_EXTENSIONS = ['.htm', '.html']

def hexuuid():
    return uuid.uuid4().hex

def splitext(p):
    return os.path.splitext(p)[1].lower()


class EntradaTexto(QLineEdit):

    ventana = None
    # para cuando se presiona ENTER cual es el widget que obtiene el foco
    proximoWidget = None

    # guarda la ultima tecla presionada
    lastKey = None

    largo = 0

    #para campos numericos que debo rellenar con ceros adelante
    relleno = 0

    #emit signal
    keyPressed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, *args, **kwargs):

        QLineEdit.__init__(self, *args)
        self.ventana = parent
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(12)
        self.setFont(font)

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])
        if 'placeholderText' in kwargs:
            self.setPlaceholderText(kwargs['placeholderText'])

        if 'alineacion' in kwargs:
            if kwargs['alineacion'].upper() == 'DERECHA':
                self.setAlignment(QtCore.Qt.AlignRight)
            elif kwargs['alineacion'].upper() == 'IZQUIERDA':
                self.setAlignment(QtCore.Qt.AlignLeft)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        if 'inputmask' in kwargs:
            self.setInputMask(kwargs['inputmask'])

    def keyPressEvent(self, event):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QLineEdit.keyPressEvent(self, event)
        self.keyPressed.emit(event.key())

    def focusOutEvent(self, QFocusEvent):
        if self.relleno > 0:
            self.setText(self.text().zfill(self.relleno))

        if self.text():
            self.setStyleSheet("background-color: Dodgerblue")
        else:
            self.setStyleSheet("background-color: white")
        QLineEdit.focusOutEvent(self, QFocusEvent)

    def focusInEvent(self, QFocusEvent):
        self.selectAll()
        QLineEdit.focusInEvent(self, QFocusEvent)

    def setLargo(self, largo=0):
        if largo > 0:
            self.largo = largo
            self.setMaxLength(self.largo)

    def value(self):
        return float(self.text()) if self.text() else 0.

class Factura(QHBoxLayout):

    numero = ''
    titulo = ''
    tamanio = 12
    enabled = True

    def __init__(self, parent=None, *args, **kwargs):
        QHBoxLayout.__init__(self)
        if 'titulo' in kwargs:
            self.titulo = kwargs['titulo']
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        if 'enabled' in kwargs:
            self.enabled = kwargs['enabled']

        self.setupUi(parent)

    def setupUi(self, layout):

        if self.titulo:
            self.labelTitulo = Etiqueta(layout, texto=self.titulo, tamanio=self.tamanio)
            self.labelTitulo.setObjectName("labelTitulo")
            self.addWidget(self.labelTitulo)

        self.lineEditPtoVta = EntradaTexto(layout, placeholderText="Pto Vta", tamanio=self.tamanio)
        self.lineEditPtoVta.setObjectName("lineEditPtoVta")
        self.lineEditPtoVta.setEnabled(self.enabled)
        self.addWidget(self.lineEditPtoVta)

        self.lineEditNumero = EntradaTexto(layout, placeholderText="Numero", tamanio=self.tamanio)
        self.lineEditNumero.setObjectName("lineEditNumero")
        self.lineEditNumero.setEnabled(self.enabled)
        self.addWidget(self.lineEditNumero)

        self.lineEditPtoVta.proximoWidget = self.lineEditNumero
        self.lineEditNumero.largo = 8
        self.lineEditPtoVta.largo = 4
        self.lineEditPtoVta.setMaximumWidth(40)
        self.lineEditNumero.setMaximumWidth(70)

        self.lineEditPtoVta.editingFinished.connect(self.AssignNumero)
        self.lineEditNumero.editingFinished.connect(self.AssignNumero)

    def AssignNumero(self):
        if self.lineEditNumero.text():
            self.lineEditNumero.setText(str(self.lineEditNumero.text()).zfill(8))
        if self.lineEditPtoVta.text():
            self.lineEditPtoVta.setText(str(self.lineEditPtoVta.text()).zfill(4))

        self.numero = str(self.lineEditPtoVta.text()).zfill(4) + \
                      str(self.lineEditNumero.text()).zfill(8)


class TextEdit(QTextEdit):
    tamanio = 12

    def __init__(self, *args, **kwargs):
        QTextEdit.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']

        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)

    def canInsertFromMimeData(self, source):

        if source.hasImage():
            return True
        else:
            return super(TextEdit, self).canInsertFromMimeData(source)

    def insertFromMimeData(self, source):

        cursor = self.textCursor()
        document = self.document()

        if source.hasUrls():

            for u in source.urls():
                file_ext = splitext(str(u.toLocalFile()))
                if u.isLocalFile() and file_ext in IMAGE_EXTENSIONS:
                    image = QImage(u.toLocalFile())
                    document.addResource(QTextDocument.ImageResource, u, image)
                    cursor.insertImage(u.toLocalFile())

                else:
                    # If we hit a non-image or non-local URL break the loop and fall out
                    # to the super call & let Qt handle it
                    break

            else:
                # If all were valid images, finish here.
                return


        elif source.hasImage():
            image = source.imageData()
            uuid = hexuuid()
            document.addResource(QTextDocument.ImageResource, uuid, image)
            cursor.insertImage(uuid)
            return

        super(TextEdit, self).insertFromMimeData(source)


class CUIT(EntradaTexto):

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99-99999999-9")

    def focusOutEvent(self, QFocusEvent):
        EntradaTexto().focusOutEvent(QFocusEvent)
        if not validar_cuit(self.text()):
            Ventanas.showAlert("Sistema", "ERROR: CUIT/CUIL no valido. Verfique!!!")

class EntradaFecha(EntradaTexto):

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99/99/9999")

    def setFecha(self, fecha=datetime.datetime.today(), format=None):
        if format:
            if format == "Ymd":
                fecha = datetime.date(year=int(fecha[:4]),
                                      month=int(fecha[4:6]),
                                      day=int(fecha[-2:]))
        if isinstance(fecha, int):
            if fecha > 0:
                self.setDate(datetime.date.today() + datetime.timedelta(days=fecha))
            else:
                self.setDate(datetime.date.today() - datetime.timedelta(days=abs(fecha)))
        else:
            self.setDate(fecha)

    def getFechaSql(self):
        fecha = str(self.text())
        fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        return fecha

    def setDate(self, QDate):
        fecha = QDate.strftime("%d/%m/%Y")
        self.setText(fecha)


class TextoEnriquecido(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.path holds the path of the currently open file.
        # If none, we haven't got a file open yet (or creating new).
        self.path = None

        self.setupUi()
        self.conectarWidgets()

    def setupUi(self):
        layoutPpal = QVBoxLayout(self)

        layoutToolBar = QHBoxLayout()
        edit_toolbar = QToolBar("Editar")
        edit_toolbar.setIconSize(QSize(16, 16))

        self.undo_action = QAction(QIcon(imagen('arrow-curve-180-left.png')), "Deshacer", self)
        self.undo_action.setStatusTip("Deshacer ultimo cambio")
        edit_toolbar.addAction(self.undo_action)

        self.redo_action = QAction(QIcon(imagen('arrow-curve.png')), "Rehacer", self)
        self.redo_action.setStatusTip("Rehacer ultimo cambio")
        edit_toolbar.addAction(self.redo_action)

        self.cut_action = QAction(QIcon(imagen('scissors.png')), "Cortar", self)
        self.cut_action.setStatusTip("Cortar texto seleccionado")
        self.cut_action.setShortcut(QKeySequence.Cut)
        edit_toolbar.addAction(self.cut_action)

        self.copy_action = QAction(QIcon(imagen('document-copy.png')), "Copiar", self)
        self.copy_action.setStatusTip("Copia texto seleccionado")
        self.copy_action.setShortcut(QKeySequence.Copy)
        edit_toolbar.addAction(self.copy_action)

        self.paste_action = QAction(QIcon(imagen('clipboard-paste-document-text.png')), "Pegar", self)
        self.paste_action.setStatusTip("Pegar desde ")
        self.paste_action.setShortcut(QKeySequence.Paste)
        edit_toolbar.addAction(self.paste_action)

        self.select_action = QAction(QIcon(imagen('selection-input.png')), "Seleccionar todo", self)
        self.select_action.setStatusTip("Seleccionar todo el texto")
        self.select_action.setShortcut(QKeySequence.SelectAll)
        edit_toolbar.addAction(self.select_action)

        self.wrap_action = QAction(QIcon(imagen('arrow-continue.png')), "Ajusta el texto a la ventana", self)
        self.wrap_action.setStatusTip("Ajusta/desajusta el texto a la ventana")
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(True)
        edit_toolbar.addAction(self.wrap_action)

        layoutToolBar.addWidget(edit_toolbar)

        toolbar_formato = QToolBar("Formato")
        toolbar_formato.setIconSize(QSize(16, 16))

        self.fonts = QFontComboBox()
        toolbar_formato.addWidget(self.fonts)

        self.fontsize = QComboBox()
        self.fontsize.addItems([str(s) for s in FONT_SIZES])
        toolbar_formato.addWidget(self.fontsize)

        self.bold_action = QAction(QIcon(imagen('edit-bold.png')), "Negrita", self)
        self.bold_action.setStatusTip("Negrita")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setCheckable(True)
        toolbar_formato.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(imagen('edit-italic.png')), "Italica", self)
        self.italic_action.setStatusTip("Italica")
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.setCheckable(True)
        toolbar_formato.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(imagen('edit-underline.png')), "Subrayado", self)
        self.underline_action.setStatusTip("Subrayado")
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.setCheckable(True)
        toolbar_formato.addAction(self.underline_action)

        self.alignl_action = QAction(QIcon(imagen('edit-alignment.png')), "Alinear izquierda", self)
        self.alignl_action.setStatusTip("Alinear texto a la izquierda")
        self.alignl_action.setCheckable(True)
        toolbar_formato.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon(imagen('edit-alignment-center.png')), "Alinear centrado", self)
        self.alignc_action.setStatusTip("Alineacion centrada del texto")
        self.alignc_action.setCheckable(True)
        toolbar_formato.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon(imagen('edit-alignment-right.png')), "Alinear derecha", self)
        self.alignr_action.setStatusTip("Alinear texto a la derecha")
        self.alignr_action.setCheckable(True)
        toolbar_formato.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon(imagen('edit-alignment-justify.png')), "Justificar", self)
        self.alignj_action.setStatusTip("Texto justificado")
        self.alignj_action.setCheckable(True)
        toolbar_formato.addAction(self.alignj_action)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

        layoutToolBar.addWidget(toolbar_formato)

        layoutPpal.addLayout(layoutToolBar)
        self.editor = TextEdit(tamanio=10)
        self.editor.setAutoFormatting(QTextEdit.AutoAll)
        # Initialize default font size.
        font = QFont('Times', 12)
        self.editor.setFont(font)
        # We need to repeat the size to init the current format.
        self.editor.setFontPointSize(12)

        layoutPpal.addWidget(self.editor)

        # A list of all format-related widgets/actions, so we can disable/enable signals when updating.
        self._format_actions = [
            self.fonts,
            self.fontsize,
            self.bold_action,
            self.italic_action,
            self.underline_action,
            # We don't need to disable signals for alignment, as they are paragraph-wide.
        ]

        # Initialize.
        self.update_format()

    def conectarWidgets(self):
        self.fonts.currentFontChanged.connect(self.editor.setCurrentFont)
        self.editor.selectionChanged.connect(self.update_format)
        self.undo_action.triggered.connect(self.editor.undo)
        self.redo_action.triggered.connect(self.editor.redo)
        self.cut_action.triggered.connect(self.editor.cut)
        self.copy_action.triggered.connect(self.editor.copy)
        self.paste_action.triggered.connect(self.editor.paste)
        self.select_action.triggered.connect(self.editor.selectAll)
        self.wrap_action.triggered.connect(self.edit_toggle_wrap)
        # Connect to the signal producing the text of the current selection. Convert the string to float
        # and set as the pointsize. We could also use the index + retrieve from FONT_SIZES.
        self.fontsize.currentIndexChanged[str].connect(lambda s: self.editor.setFontPointSize(float(s)) )
        self.bold_action.toggled.connect(lambda x: self.editor.setFontWeight(QFont.Bold if x else QFont.Normal))
        self.italic_action.toggled.connect(self.editor.setFontItalic)
        self.underline_action.toggled.connect(self.editor.setFontUnderline)
        self.alignl_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignLeft))
        self.alignc_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignCenter))
        self.alignr_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignRight))
        self.alignj_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignJustify))

    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    def update_format(self):
        """
        Update the font format toolbar/actions when a new text selection is made. This is neccessary to keep
        toolbars/etc. in sync with the current edit state.
        :return:
        """
        # Disable signals for all format widgets, so changing values here does not trigger further formatting.
        self.block_signals(self._format_actions, True)

        self.fonts.setCurrentFont(self.editor.currentFont())
        # Nasty, but we get the font-size as a float but want it was an int
        self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))

        self.italic_action.setChecked(self.editor.fontItalic())
        self.underline_action.setChecked(self.editor.fontUnderline())
        self.bold_action.setChecked(self.editor.fontWeight() == QFont.Bold)

        self.alignl_action.setChecked(self.editor.alignment() == Qt.AlignLeft)
        self.alignc_action.setChecked(self.editor.alignment() == Qt.AlignCenter)
        self.alignr_action.setChecked(self.editor.alignment() == Qt.AlignRight)
        self.alignj_action.setChecked(self.editor.alignment() == Qt.AlignJustify)

        self.block_signals(self._format_actions, False)

    def edit_toggle_wrap(self):
        self.editor.setLineWrapMode( 1 if self.editor.lineWrapMode() == 0 else 0 )

    def file_open(self, archivo=''):
        # path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "HTML documents (*.html);Text documents (*.txt);All files (*.*)")
        path = archivo
        try:
            with open(path, 'rU') as f:
                text = f.read()

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.path = path
            # Qt will automatically try and guess the format as txt/html
            self.editor.setText(text)
            # self.update_title()

    def file_save(self, path=None):
        self.path = path
        if self.path is None:
            # If we do not have a path, we need to use Save As.
            return self.file_saveas()

        text = self.editor.toHtml() if splitext(self.path) in HTML_EXTENSIONS else self.editor.toPlainText()

        try:
            with open(self.path, 'w') as f:
                f.write(text)

        except Exception as e:
            self.dialog_critical(str(e))

    def file_saveas(self, path=None):
        if not path:
            # If dialog is cancelled, will return ''
            return

        text = self.editor.toHtml() if splitext(path) in HTML_EXTENSIONS else self.editor.toPlainText()

        try:
            with open(path, 'w') as f:
                f.write(text)

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.path = path
            # self.update_title()

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def toHtml(self):
        return self.editor.toHtml()

    def toPlainText(self):
        return self.editor.toPlainText()

class AutoCompleter(EntradaTexto):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def creaCompleter(self, datos=[]):
        completer = QCompleter(datos)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(completer)

class EmailCompleter(AutoCompleter):

    modelo = None #modelo a consultar
    condicion = None #condicion de filtro de los correos

    def cargaDatos(self):
        datos = []
        if self.modelo:
            correos = self.modelo.select()
        if self.condicion:
            correos = correos.where(self.condicion)

        for c in correos:
            datos.append(c.email)
        self.creaCompleter(datos)