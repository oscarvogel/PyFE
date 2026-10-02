# coding=utf-8
"""Armazon de la aplicacion: barra lateral por dominios + area de contenido.

Por que esto reemplaza a los 9 botones
--------------------------------------
La pantalla anterior era una fila de 9 botones iguales. Cada uno abria un menu
que aparecia pegado a la posicion del cursor, y detras de esos 9 botones habia
unas 30 acciones distintas. Ademas, cinco modulos completos (todo Compras) no
estaban conectados a ningun boton: los controladores estaban escritos y no habia
forma de abrirlos.

Aca la navegacion esta a la vista, agrupada por lo que el usuario quiere hacer
y no por el orden en que se escribieron los controladores, y la lista completa
esta en SECCIONES, que es la unica fuente de verdad.

Sobre ese dato trabaja el controlador: cada CLAVE tiene que tener un destino.
Si alguien agrega una seccion y olvida el destino, el test lo detecta (ver
tests/test_navegacion.py). Es el mismo bug que hoy esconde a Compras.
"""

import os

from PyQt5.QtCore import QEvent, QObject, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Constantes import NOMBRE_PRODUCTO
from libs.Utiles import icono
from libs.recursos import ruta_recurso
from vistas.VistaBase import VistaBase


# (titulo de seccion, icono, [(clave, texto, icono), ...])
#
# La clave es el contrato con el controlador. Los textos van con acento porque
# esto se lee, no es un dato.
SECCIONES = [
    ("Facturación", "nueva-venta", [
        ("nueva-venta", "Venta rápida", "nueva-venta"),
        ("comprobantes", "Comprobantes", "comprobantes"),
        ("remitos", "Remitos", "carpeta"),
        ("recibos", "Recibos", "cuentas"),
        ("reimprimir-factura", "Reimprimir factura", "imprimir"),
        ("reimprimir-remito", "Reimprimir remito", "documento"),
    ]),
    ("Compras", "proveedores", [
        ("proveedores", "Proveedores", "proveedores"),
        ("centro-costos", "Centros de costo", "monotributo"),
        ("carga-facturas", "Cargar comprobantes", "agregar"),
        ("iva-compras", "IVA compras", "reportes"),
        ("rg3685-compras", "RG 3685 compras", "documento"),
    ]),
    ("Fiscal", "reportes", [
        ("iva-ventas", "IVA ventas", "reportes"),
        ("rg3685-ventas", "RG 3685 ventas", "excel"),
        ("importar", "Importar comprobantes", "importar"),
    ]),
    ("Clientes", "clientes", [
        ("clientes", "Alta y modificación", "clientes"),
        ("cuenta-corriente", "Cuenta corriente", "cuentas"),
        ("enviar-email", "Enviar por email", "email"),
    ]),
    ("Stock", "productos", [
        ("productos", "Productos", "productos"),
        ("grupos", "Grupos", "vacio"),
        ("impuestos", "Impuestos", "excel"),
        ("informe-ventas-grupo", "Ventas por grupo", "reportes"),
    ]),
    ("ARCA / AFIP", "arca", [
        ("diagnostico", "Diagnóstico de servicio", "refrescar"),
        ("consulta-cuit", "Consulta de CUIT", "buscar"),
        ("constatacion", "Constatación de comprobantes", "check"),
        ("consulta-cae", "Consulta de CAE", "documento"),
        ("rinde-caea", "Rinde CAEA individual", "certificado"),
    ]),
    ("Monotributo", "monotributo", [
        ("categorias-mono", "Categorías", "monotributo"),
        ("informe-recategorizacion", "Informe de recategorización", "excel"),
    ]),
    ("Catálogos", "vacio", [
        ("localidades", "Localidades", "vacio"),
        ("tipo-comprobantes", "Tipos de comprobante", "comprobantes"),
        ("tipo-documentos", "Tipos de documento", "documento"),
        ("tipo-responsable", "Tipos de responsable", "clientes"),
    ]),
    ("Configuración", "configuracion", [
        ("configuracion", "Configuración de inicio", "configuracion"),
        ("parametros", "Parámetros del sistema", "configuracion"),
        ("firma-email", "Firma de correo", "email"),
        ("certificados", "Certificados digitales", "certificado"),
    ]),
]

# Acciones que se destacan en el panel de bienvenida: son las que se usan todos
# los dias. No es la lista completa, es la respuesta a "que hago ahora".
ACCIONES_RAPIDAS = [
    ("nueva-venta", "Nueva venta", "Emitir una factura", "nueva-venta"),
    ("clientes", "Clientes", "Alta o buscar un cliente", "clientes"),
    ("cuenta-corriente", "Cuenta corriente", "Ver saldos y pagos", "cuentas"),
    ("productos", "Productos", "Cargar o consultar el stock", "productos"),
]


class ItemNavegacion(QPushButton):
    """Un boton de la barra lateral. Checkable para marcar el activo."""

    def __init__(self, clave, texto, icono_nombre, *args, **kwargs):
        QPushButton.__init__(self, *args, **kwargs)
        self.clave = clave
        self.setText(texto)
        self.setObjectName("itemNavegacion")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(20, 20))
        ruta = icono(icono_nombre)
        if ruta:
            from PyQt5.QtGui import QIcon
            self.setIcon(QIcon(ruta))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class PanelBienvenida(QWidget):
    """El area de contenido cuando todavia no se abrio ninguna pantalla."""

    def __init__(self, al_navegar):
        QWidget.__init__(self)
        self.setObjectName("panelBienvenida")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(8)

        self.lblSaludo = EtiquetaTitulo(texto=NOMBRE_PRODUCTO)
        layout.addWidget(self.lblSaludo)

        self.lblTexto = Etiqueta(
            texto="Elegí una sección de la izquierda, o empezá por una de estas:")
        self.lblTexto.setObjectName("labelSubtitulo")
        layout.addWidget(self.lblTexto)
        layout.addSpacing(18)

        grilla = QGridLayout()
        grilla.setSpacing(14)
        for i, (clave, titulo, detalle, icono_nombre) in enumerate(ACCIONES_RAPIDAS):
            tarjeta = self._tarjeta(clave, titulo, detalle, icono_nombre, al_navegar)
            grilla.addWidget(tarjeta, i // 2, i % 2)
        layout.addLayout(grilla)
        layout.addStretch(1)

    @staticmethod
    def _tarjeta(clave, titulo, detalle, icono_nombre, al_navegar):
        caja = QFrame()
        caja.setObjectName("tarjetaAccion")
        caja.setCursor(Qt.PointingHandCursor)
        vertical = QVBoxLayout(caja)
        vertical.setContentsMargins(18, 16, 18, 16)
        vertical.setSpacing(4)

        ruta = icono(icono_nombre)
        if ruta:
            from PyQt5.QtGui import QIcon, QPixmap
            etiqueta = QLabel()
            pixmap = QPixmap(ruta)
            etiqueta.setPixmap(pixmap.scaled(28, 28, Qt.KeepAspectRatio,
                                             Qt.SmoothTransformation))
            vertical.addWidget(etiqueta)

        lblTitulo = Etiqueta(texto=titulo)
        lblTitulo.setObjectName("tituloTarjeta")
        vertical.addWidget(lblTitulo)

        lblDetalle = Etiqueta(texto=detalle)
        lblDetalle.setObjectName("detalleTarjeta")
        vertical.addWidget(lblDetalle)

        caja.clave = clave
        # Se usa un boton invisible que cubre la tarjeta: recibe el foco y el
        # click sin pelear con las etiquetas de arriba. Lleva su propio
        # objectName porque el tema pinta todos los QPushButton con fondo y
        # borde: sin esto se ve un rectangulo blanco en cada tarjeta.
        boton = QPushButton(caja)
        boton.setObjectName("botonTarjeta")
        boton.setFocusPolicy(Qt.StrongFocus)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setAccessibleName(titulo)
        boton.setToolTip(detalle)
        boton.clicked.connect(lambda _=False, c=clave: al_navegar(c))
        caja.installEventFilter(_FiltroTarjetas(caja, al_navegar))
        return caja


class _FiltroTarjetas(QObject):
    """Click en cualquier parte de la tarjeta, no solo en el boton invisible."""

    def __init__(self, caja, al_navegar):
        QObject.__init__(self, caja)
        self.caja = caja
        self.al_navegar = al_navegar

    def eventFilter(self, obj, evento):
        if obj is self.caja and evento.type() == QEvent.MouseButtonRelease:
            self.al_navegar(self.caja.clave)
            return True
        return False


class MainView(VistaBase):

    # La vista no sabe abrir pantallas: avisa la clave y el controlador decide.
    navegar = pyqtSignal(str)

    def initUi(self):
        self.setWindowTitle(NOMBRE_PRODUCTO)
        self.setMinimumSize(900, 560)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        raiz.addWidget(self._construir_encabezado())

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self._construir_lateral())

        self.contenedor = QWidget()
        self.contenedor.setObjectName("areaContenido")
        self.layoutContenido = QVBoxLayout(self.contenedor)
        self.layoutContenido.setContentsMargins(0, 0, 0, 0)
        self.panelBienvenida = PanelBienvenida(self.navegar.emit)
        self.layoutContenido.addWidget(self.panelBienvenida)
        cuerpo.addWidget(self.contenedor, 1)

        raiz.addLayout(cuerpo, 1)
        raiz.addWidget(self._construir_barra_estado())

        # El encabezado y la barra de estado muestran configuracion, no logica
        # de negocio: se leen aca para que la vista se sostenga sola y para que
        # se pueda renderizar y probar sin levantar los controladores. El
        # controlador despues los refresca con iniciar().
        self.refrescar_datos()

    # -- Encabezado --------------------------------------------------------
    def _construir_encabezado(self):
        marco = QFrame()
        marco.setObjectName("encabezado")
        horizontal = QHBoxLayout(marco)
        horizontal.setContentsMargins(18, 10, 18, 10)
        horizontal.setSpacing(12)

        # Logo. Va el isotipo recortado, no el logo completo: el original tiene
        # mucho aire alrededor y a 40 px de alto el simbolo quedaria diminuto.
        self.lblLogo = QLabel()
        self.lblLogo.setObjectName("logoEncabezado")
        self.lblLogo.setFixedHeight(40)
        ruta_logo = ruta_recurso("imagenes/marca/marca-48.png")
        if ruta_logo:
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(ruta_logo)
            self.lblLogo.setPixmap(pixmap.scaledToHeight(
                40, Qt.SmoothTransformation))
        self.lblLogo.setAccessibleName("Vogel Consultoria")
        horizontal.addWidget(self.lblLogo)

        textos = QVBoxLayout()
        textos.setSpacing(0)
        self.lblTitulo = EtiquetaTitulo(texto=NOMBRE_PRODUCTO)
        textos.addWidget(self.lblTitulo)
        self.lblEmpresa = Etiqueta(texto="")
        self.lblEmpresa.setObjectName("labelSubtitulo")
        textos.addWidget(self.lblEmpresa)
        horizontal.addLayout(textos)
        horizontal.addStretch(1)

        # El modo en pantalla. Antes solo se anunciaba con un print() a una
        # consola que el usuario nunca ve, y el sistema emite comprobantes
        # fiscales: no puede quedar la duda de si se esta en homologacion.
        self.chipModo = QLabel("")
        self.chipModo.setObjectName("chipModo")
        horizontal.addWidget(self.chipModo)

        return marco

    def establecer_modo(self, homologacion):
        if homologacion:
            self.chipModo.setText("HOMOLOGACIÓN · no factura a AFIP")
            self.chipModo.setProperty("modo", "homo")
        else:
            self.chipModo.setText("PRODUCCIÓN · factura a AFIP")
            self.chipModo.setProperty("modo", "produccion")
        # Cambiar una propiedad dinamica no refresca el estilo solo.
        estilo = self.chipModo.style()
        estilo.unpolish(self.chipModo)
        estilo.polish(self.chipModo)
        self.chipModo.update()

    # -- Datos de configuracion --------------------------------------------
    def refrescar_datos(self):
        """Lee del sistema.ini lo que va en el encabezado y la barra de estado."""
        from libs.Utiles import LeerIni

        try:
            homologacion = LeerIni("homo") == "S"
            empresa = LeerIni(clave="empresa", key="FACTURA")
            cuit = LeerIni(clave="cuit", key="FACTURA")
            # La clave se llama pto_vta, no punto_venta: es la que lee
            # controladores/Facturas.py al emitir. Con el nombre equivocado la
            # barra de estado muestra siempre vacio.
            punto_venta = LeerIni(clave="pto_vta", key="WSFEv1")
            ultima_copia = LeerIni("ultima_copia")
        except Exception:
            homologacion, empresa, cuit, punto_venta, ultima_copia = None, "", "", "", ""

        self.establecer_modo(homologacion)
        self.establecer_empresa(empresa, self._solo_cuit(cuit))
        self.establecer_estado(
            punto_venta=punto_venta,
            resguardo=(ultima_copia if ultima_copia and ultima_copia != "00000000"
                       else "sin copia"),
            version=self._version(),
        )

    @staticmethod
    def _solo_cuit(valor):
        """Se queda solo con los digitos y guiones del CUIT.

        Hay instalaciones donde el valor de [FACTURA] cuit quedo con el rotulo
        pegado adentro (por ejemplo 'Cuit 20-17946115-4'), de copiar y pegar
        desde una etiqueta de la pantalla. Mostrarlo crudo en el encabezado
        daba 'CUIT Cuit 20-17946115-4'.

        No se corrige el dato: el CUIT que se usa para facturar sale de
        [WSFEv1], y ese esta bien. Esto solo evita mostrar basura.
        """
        if not valor:
            return ""
        limpio = "".join(c for c in str(valor) if c.isdigit() or c == "-").strip("-")
        return limpio

    @staticmethod
    def _version():
        """La version sale de version.txt, que es la que se mete en el .exe."""
        try:
            from libs.recursos import rutas_base
            for base in rutas_base():
                ruta = os.path.join(base, "version.txt")
                if os.path.isfile(ruta):
                    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                        for linea in f:
                            if linea.strip().startswith("versionName"):
                                return "v" + linea.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return ""

    def establecer_empresa(self, nombre, cuit):
        self.lblEmpresa.setText("{} · CUIT {}".format(nombre, cuit) if cuit
                                else (nombre or ""))

    # -- Barra lateral -----------------------------------------------------
    def _construir_lateral(self):
        lateral = QFrame()
        lateral.setObjectName("barraLateral")
        # 228 px y no mas: es lo que entra en una pantalla de 1024 de ancho
        # junto con el area de contenido. Con 252 la ventana pedia 1040 px y en
        # una notebook chica el borde derecho quedaba fuera.
        lateral.setFixedWidth(228)

        vertical = QVBoxLayout(lateral)
        vertical.setContentsMargins(0, 12, 0, 12)
        vertical.setSpacing(0)

        self.grupoBotones = QButtonGroup(self)
        self.grupoBotones.setExclusive(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("scrollLateral")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenido = QWidget()
        self.layoutLateral = QVBoxLayout(contenido)
        self.layoutLateral.setContentsMargins(10, 0, 10, 10)
        self.layoutLateral.setSpacing(2)

        self.botonesNav = {}
        for titulo, _icono_seccion, items in SECCIONES:
            encabezado = QLabel(titulo)
            encabezado.setObjectName("tituloSeccion")
            # El margen va en el label, no en el layout, para que el fondo del
            # sidebar no se corte entre secciones.
            encabezado.setContentsMargins(10, 11, 0, 4)
            self.layoutLateral.addWidget(encabezado)

            for clave, texto, icono_nombre in items:
                boton = ItemNavegacion(clave, texto, icono_nombre)
                self.grupoBotones.addButton(boton)
                # Esto es lo que hace que el boton funcione. Sin el connect, el
                # boton se dibuja y cambia de color al verlo marcado, pero no
                # abre nada: el error es invisible hasta que alguien lo prueba.
                boton.clicked.connect(lambda _=False, c=clave: self.navegar.emit(c))
                self.botonesNav[clave] = boton
                self.layoutLateral.addWidget(boton)

        self.layoutLateral.addStretch(1)
        scroll.setWidget(contenido)
        vertical.addWidget(scroll)
        return lateral

    # -- Barra de estado ---------------------------------------------------
    def _construir_barra_estado(self):
        marco = QFrame()
        marco.setObjectName("barraEstado")
        horizontal = QHBoxLayout(marco)
        horizontal.setContentsMargins(16, 5, 16, 5)
        horizontal.setSpacing(16)

        # Solo va lo que NO esta en otro lado. El modo ya se ve en el chip del
        # encabezado y el CUIT con la empresa en el subtitulo: repetirlo aqui
        # era ademas lo que inflaba el ancho minimo de la ventana a 1094 px, y
        # en una pantalla de 1024 la barra empujaba el contenido fuera de la
        # derecha.
        self.lblPuntoVenta = QLabel("")
        self.lblArca = QLabel("")
        self.lblResguardo = QLabel("")
        self.lblVersion = QLabel("")

        for etiqueta in (self.lblPuntoVenta, self.lblArca,
                         self.lblResguardo, self.lblVersion):
            etiqueta.setObjectName("datoEstado")
            # Preferred, no Ignored: Ignored hace que el layout les de ancho
            # cero y desaparecen. Preferred respeta el ancho del texto pero
            # con minimumWidth(0) puede encogerse si no entra, que es lo que
            # evita que un dato mas largo agrande la ventana.
            politica = etiqueta.sizePolicy()
            politica.setHorizontalPolicy(QSizePolicy.Preferred)
            etiqueta.setSizePolicy(politica)
            etiqueta.setMinimumWidth(0)
            horizontal.addWidget(etiqueta)

        horizontal.addStretch(1)
        return marco

    def establecer_estado(self, punto_venta=None, arca=None, resguardo=None,
                          version=None):
        self.lblPuntoVenta.setText("Pto. de venta {}".format(punto_venta)
                                   if punto_venta else "")
        self.lblArca.setText("ARCA: {}".format(arca) if arca else "ARCA: sin consultar")
        self.lblResguardo.setText("Resguardo {}".format(resguardo) if resguardo else "")
        self.lblVersion.setText(version or "")

    # -- Navegacion --------------------------------------------------------
    def marcar_activo(self, clave):
        boton = self.botonesNav.get(clave)
        if boton:
            boton.setChecked(True)

    def mostrar_salida_de_contenido(self, widget):
        """Cambia el panel de bienvenida por la pantalla elegida."""
        self.layoutContenido.removeWidget(self.panelBienvenida)
        self.panelBienvenida.setParent(None)
        self.layoutContenido.addWidget(widget)
