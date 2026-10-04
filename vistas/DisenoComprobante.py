# coding=utf-8
"""Pantalla de diseno del comprobante: la marca que el cliente puede tocar.

Por que existe
--------------
La capa de marca (controladores/FacturaBranding.py, plantillas/factura_marca.csv
y los diez parametros FACTURA_MARCA_*) ya estaba escrita y funcionaba, pero
NADA escribia esos parametros y no habia ninguna pantalla: la marca estaba
desactivada en toda instalacion y para activarla habia que escribir diez filas
en paramsist a mano. O sea que el cliente no tenia nada para tocar el diseno de
su factura.

Que NO resuelve, y conviene decirlo en la pantalla
--------------------------------------------------
Los diez parametros son la CAPA DE MARCA: logo, fondo, web, leyenda y cuatro
colores. Mover un campo, agregar uno o cambiar el layout sigue siendo cosa de
editar la plantilla a mano. Esta pantalla no promete mas de lo que hace.

Lo que si agrega y no habia: el boton de VISTA PREVIA. Sin poder ver el
resultado sin emitir una factura, el cliente no sabe si lo que cargo le gusta.
Y no se puede probar con una factura real porque emitir deja rastro fiscal
contra ARCA, que no se puede deshacer. Asi que la vista previa arma el PDF con
datos de mentira y no toca la base.
"""
import os

import os

from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLineEdit, QVBoxLayout)

from libs.Botones import Boton, BotonArchivo, BotonCerrarFormulario
from libs.ComboBox import ComboSINO
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Utiles import icono

# Los cuatro colores de la marca: clave del parametro, nombre para el operador
# y valor por defecto. El orden es el que se muestra.
COLORES = [
    ("color_primario", "Principal", "#0F2A44"),
    ("color_secundario", "Secundario", "#0B2035"),
    ("color_acento", "Acento", "#F2A900"),
    ("color_texto_secundario", "Texto secundario", "#8EA8C3"),
]

LIMITE_WEB = 40
LIMITE_LEYENDA = 60


def normalizar_color(texto):
    """'#0F2A44', '0f2a44' o 'f2a900' -> '#0F2A44'. Vacio si no parece un color.

    Aceptar el hex sin '#' y en minuscula es a proposito: el operador lo
    pega de donde lo tenga, y un color invalido tiene que verse raro antes de
    guardarse, no pasar al comprobante.
    """
    limpio = str(texto or "").strip().lstrip("#")
    if len(limpio) == 6:
        limpio = "#" + limpio
    if len(limpio) != 7 or not limpio.startswith("#"):
        return None
    try:
        int(limpio[1:], 16)
    except ValueError:
        return None
    return limpio.upper()


class DisenoComprobanteView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Diseño del comprobante")
        self.resize(760, 540)

        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.lblAyuda = Etiqueta(
            texto="Esto define el logo, el fondo, los colores y los textos de "
                  "la factura. Para mover campos o cambiar el reparto de la "
                  "hoja hay que editar la plantilla: esto no lo hace.")
        self.lblAyuda.setWordWrap(True)
        self.verticalLayoutDatos.addWidget(self.lblAyuda)

        self.lblActiva = EtiquetaTitulo(texto="Aplicar diseño propio")
        self.verticalLayoutDatos.addWidget(self.lblActiva)
        self.ArmaEntrada('activa', texto='Usar diseño propio en los comprobantes',
                         control=ComboSINO())

        self.lblImagenes = EtiquetaTitulo(texto="Logo y fondo")
        self.verticalLayoutDatos.addWidget(self.lblImagenes)

        # guardar=False: se elige una imagen que YA esta, no se crea una. Con
        # guardar=True el boton abria un dialogo de guardar y preguntaba si
        # pisaba el archivo, que es al reves de lo que se quiere.
        layoutLogo = self.ArmaEntrada('logo', texto='Logo')
        self.btnArchivoLogo = BotonArchivo(
            archivos="Imagen (*.png *.jpg *.jpeg)",
            imagen=icono('carpeta'), tamanio=QSize(24, 24))
        self.btnArchivoLogo.guardar = False
        self.btnArchivoLogo.widgetArchivo = self.controles['logo']
        layoutLogo.addWidget(self.btnArchivoLogo)

        layoutFondo = self.ArmaEntrada('fondo', texto='Fondo A4')
        self.btnArchivoFondo = BotonArchivo(
            archivos="Imagen (*.png *.jpg *.jpeg)",
            imagen=icono('carpeta'), tamanio=QSize(24, 24))
        self.btnArchivoFondo.guardar = False
        self.btnArchivoFondo.widgetArchivo = self.controles['fondo']
        layoutFondo.addWidget(self.btnArchivoFondo)

        # La plantilla de la marca NO se impone. Vacia (que es lo normal) el
        # comprobante sale con la plantilla fiscal de siempre, con sus lineas
        # y sus cuadros, y arriba se suma el logo, el fondo y los colores.
        # Llenarla es para quien quiere deliberadamente otro reparto de la
        # hoja, y por eso va visible: una caja negra que cambia el formato
        # del comprobante sin que se note es la peor forma de hacerlo.
        self.lblPlantilla = EtiquetaTitulo(texto="Plantilla")
        self.verticalLayoutDatos.addWidget(self.lblPlantilla)
        self.ArmaEntrada(
            'formato',
            texto='Usar otra plantilla (vacío = la de siempre)')
        self.lblAyudaPlantilla = Etiqueta(
            texto="Vacío: el comprobante sale con la plantilla fiscal de "
                  "siempre, con sus líneas y sus cuadros, y el logo, el fondo "
                  "y los colores se suman encima.\n"
                  "Con una ruta: se usa esa plantilla y PIERDE el formato "
                  "fiscal (las líneas y los cuadros no están en "
                  "factura_marca.csv). Solo para quien quiera otro reparto "
                  "de la hoja.")
        self.lblAyudaPlantilla.setWordWrap(True)
        self.verticalLayoutDatos.addWidget(self.lblAyudaPlantilla)

        self.lblTextos = EtiquetaTitulo(texto="Textos")
        self.verticalLayoutDatos.addWidget(self.lblTextos)
        self.ArmaEntrada('web', texto='Sitio web (máx. {})'.format(LIMITE_WEB))
        self.ArmaEntrada('leyenda',
                         texto='Leyenda al pie (máx. {})'.format(LIMITE_LEYENDA))

        self.lblColores = EtiquetaTitulo(texto="Colores")
        self.verticalLayoutDatos.addWidget(self.lblColores)

        self.layoutColores = QGridLayout()
        self.muestras = {}
        for indice, (clave, nombre, defecto) in enumerate(COLORES):
            self.layoutColores.addWidget(Etiqueta(texto=nombre), indice, 0)

            # El campo queda editable a mano porque hay gente que prefiere
            # pegar el hex de otra parte.
            entrada = QLineEdit(defecto)
            entrada.setObjectName(clave)
            entrada.setMaxLength(7)
            self.controles[clave] = entrada
            self.layoutColores.addWidget(entrada, indice, 1)

            # El kwarg del icono es 'imagen'. 'icono' lo ignora en silencio y
            # el boton queda pelado, sin avisar nada.
            boton = Boton(texto="Elegir", imagen=icono('editar'),
                          tamanio=QSize(24, 24))
            boton.clicked.connect(
                lambda _marcado=False, c=clave: self.elegir_color(c))
            self.layoutColores.addWidget(boton, indice, 2)

            # Una muestra del color al lado, para no tener que imaginarse como
            # queda #0F2A44.
            muestra = QLabel("        ")
            muestra.setFrameShape(QFrame.Box)
            muestra.setFixedWidth(60)
            self.muestras[clave] = muestra
            self.layoutColores.addWidget(muestra, indice, 3)

            for clave, nombre, defecto in COLORES:
                entrada.textChanged.connect(
                    lambda texto, c=clave: self.pintar_muestra(c, texto))
                self.pintar_muestra(clave, defecto)
        self.layoutColores.setColumnStretch(1, 1)
        self.verticalLayoutDatos.addLayout(self.layoutColores)

        self.layoutBotones = QHBoxLayout()
        self.btnProbar = Boton(texto="Ver comprobante de prueba",
                              imagen=icono('imprimir'), tamanio=QSize(24, 24),
                              estilo='primario')
        self.btnGrabar = Boton(texto="Grabar", imagen=icono('guardar'),
                              tamanio=QSize(24, 24))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnProbar)
        self.layoutBotones.addWidget(self.btnGrabar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)

    # -- Colores ------------------------------------------------------------

    def elegir_color(self, clave):
        entrada = self.controles[clave]
        actual = normalizar_color(entrada.text())
        # Se parte del color que ya esta puesto, no del ultimo que se eligio en
        # cualquier parte del sistema de Qt.
        inicial = QColor(actual) if actual else QColor(255, 255, 255)

        color = QColorDialog.getColor(inicial, entrada, "Elegir color")
        if color.isValid():
            entrada.setText(color.name().upper())

    def pintar_muestra(self, clave, texto):
        muestra = self.muestras.get(clave)
        if muestra is None:
            return
        color = normalizar_color(texto)
        if color:
            muestra.setStyleSheet(
                "background-color: {}; border: 1px solid #999;".format(color))
        else:
            muestra.setStyleSheet("border: 1px solid #999;")

    def colores_invalidos(self):
        """Los campos de color que no se pueden usar, con lo que tienen."""
        malos = []
        for clave, nombre, _defecto in COLORES:
            if not normalizar_color(self.controles[clave].text()):
                malos.append("{} ({})".format(nombre, self.controles[clave].text()))
        return malos

