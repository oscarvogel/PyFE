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
import re

from PyQt5.QtCore import QEvent, QObject, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QScrollArea,
                             QShortcut, QSizePolicy, QVBoxLayout, QWidget)

from libs.busqueda import normalizar
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Constantes import NOMBRE_PRODUCTO, SITIO_EMPRESA
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
        ("stock", "Stock", "productos"),
        ("productos", "Productos", "productos"),
        ("importar-articulos", "Importar productos desde Excel", "importar"),
        ("ajustes-stock", "Ajustes de stock", "ajustar-texto"),
        ("movimientos-stock", "Movimientos de stock", "reportes"),
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
        ("diseno-comprobante", "Diseño del comprobante", "comprobantes"),
        ("parametros", "Parámetros del sistema", "configuracion"),
        ("correo-reportes", "Correo de reportes de errores", "email"),
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

        # Ctrl+K lleva al buscador. Con 36 acciones es el atajo que mas se
        # usa, y buscar con el raton obliga a scrollear la barra lateral.
        self._atajo_buscador = QShortcut(QKeySequence("Ctrl+K"), self)
        self._atajo_buscador.activated.connect(self.enfocar_buscador)

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
        pegado adentro (por ejemplo 'Cuit 20-12345678-9'), de copiar y pegar
        desde una etiqueta de la pantalla. Mostrarlo crudo en el encabezado
        daba 'CUIT Cuit 20-12345678-9'.

        No se corrige el dato: el CUIT que se usa para facturar sale de
        [WSFEv1], y ese esta bien. Esto solo evita mostrar basura.
        """
        if not valor:
            return ""
        limpio = "".join(c for c in str(valor) if c.isdigit() or c == "-").strip("-")
        return limpio

    @staticmethod
    def _version():
        """La version que se le muestra al usuario.

        La fuente de verdad es `libs/build_info.py` (BUILD_VERSION), que es lo
        que el actualizador compara contra el manifiesto de vogel-releases.
        Se lee primero esa porque es la unica que dice con precision que build
        esta corriendo: `version.txt` lo escribe Windows al compilar y en
        desarrollo dice 0.9.0 siempre.

        El fallback a `version.txt` se mantiene: PyInstaller lee ese archivo
        con eval(), asi que no se le puede agregar una clave propia, y la app
        sigue necesitando el archivo suelto al lado del ejecutable
        (compila.bat lo copia). Antes buscaba una clave `versionName` que
        nadie escribia, y por eso la barra de estado y Acerca de salian con
        la version vacia, sin error.
        """
        try:
            from libs.build_info import BUILD_VERSION, es_build_productivo
            from libs.actualizaciones import VERSION_RE

            if es_build_productivo() and VERSION_RE.match((BUILD_VERSION or "").strip()):
                return "v" + BUILD_VERSION.strip()
        except Exception:
            pass

        try:
            from libs.recursos import rutas_base
            for base in rutas_base():
                ruta = os.path.join(base, "version.txt")
                if not os.path.isfile(ruta):
                    continue
                with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()

                # Los valores van como u'0.8.10', no como 0.8.10=...
                for clave in ("ProductVersion", "FileVersion"):
                    encontrado = re.search(
                        clave + r"'\s*,\s*u?'([^']+)'", contenido)
                    if encontrado and encontrado.group(1).strip():
                        return "v" + encontrado.group(1).strip()

                encontrado = re.search(r"filevers\s*=\s*\(([^)]*)\)", contenido)
                if encontrado:
                    numeros = re.findall(r"\d+", encontrado.group(1))
                    if len(numeros) >= 3:
                        return "v" + ".".join(numeros[:3])
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
        vertical.setContentsMargins(0, 10, 0, 12)
        vertical.setSpacing(0)

        # Buscador. Con 36 acciones, scrollear la barra lateral es la unica
        # forma de encontrar algo que no este en las cuatro primeras lineas.
        self.txtBuscar = QLineEdit()
        self.txtBuscar.setObjectName("buscadorLateral")
        self.txtBuscar.setPlaceholderText("Buscar…")
        self.txtBuscar.setClearButtonEnabled(True)
        self.txtBuscar.addAction(
            self._lupa(), QLineEdit.LeadingPosition)
        self.txtBuscar.textChanged.connect(self._filtrar_lateral)
        self.txtBuscar.returnPressed.connect(self._ir_al_primer_resultado)
        lateral_buscador = QWidget()
        layout_buscador = QVBoxLayout(lateral_buscador)
        layout_buscador.setContentsMargins(10, 0, 10, 8)
        layout_buscador.addWidget(self.txtBuscar)
        self.lblSinResultados = QLabel("")
        self.lblSinResultados.setObjectName("sinResultados")
        self.lblSinResultados.setVisible(False)
        layout_buscador.addWidget(self.lblSinResultados)
        vertical.addWidget(lateral_buscador)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("scrollLateral")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenido = QWidget()
        self.layoutLateral = QVBoxLayout(contenido)
        self.layoutLateral.setContentsMargins(10, 0, 10, 10)
        self.layoutLateral.setSpacing(2)

        self.grupoBotones = QButtonGroup(self)
        self.grupoBotones.setExclusive(True)

        # Se guarda la seccion de cada boton para poder esconder la seccion
        # entera cuando ninguno de sus botones coincide con la busqueda.
        self._seccion_de = {}
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
                boton.clicked.connect(
                    lambda _=False, c=clave: self.navegar.emit(c))
                self.botonesNav[clave] = boton
                self._seccion_de[clave] = encabezado
                self.layoutLateral.addWidget(boton)

        self.layoutLateral.addStretch(1)
        scroll.setWidget(contenido)
        vertical.addWidget(scroll)
        vertical.addWidget(self._construir_pie_lateral())
        return lateral

    def _construir_pie_lateral(self):
        """El boton de Acerca de, abajo de la lista y siempre a la vista.

        Va fuera del scroll a proposito: si viviera dentro se perderia de vista
        en listas largas, y es justo el boton que se busca cuando algo anda
        mal y hay que preguntar a quien lo desarrollo.
        """
        pie = QPushButton("Acerca de")
        pie.setObjectName("botonAcercaDe")
        pie.setCursor(Qt.PointingHandCursor)
        pie.setToolTip("Version, datos del desarrollo y como pedir ayuda")
        pie.clicked.connect(self.abrir_acerca_de)

        marco = QWidget()
        layout = QVBoxLayout(marco)
        layout.setContentsMargins(10, 8, 10, 0)
        layout.addWidget(pie)
        return marco

    def abrir_acerca_de(self):
        self.construir_acerca_de().exec_()

    def construir_acerca_de(self):
        """Arma el dialogo de Acerca de y lo devuelve sin abrirlo.

        Va separado de abrir_acerca_de para poder renderizarlo en las
        herramientas de control: un dialogo que solo existe adentro de un
        exec_() no se puede mirar hasta que alguien lo abre.
        """
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtWidgets import QDialog, QPushButton

        from libs.Constantes import EMPRESA_DESARROLLO, WHATSAPP_EMPRESA

        dlg = QDialog(self)
        dlg.setWindowTitle("Acerca de {}".format(NOMBRE_PRODUCTO))
        dlg.setObjectName("dialogoAcercaDe")
        vertical = QVBoxLayout(dlg)
        vertical.setSpacing(10)

        ruta_logo = ruta_recurso("imagenes/marca/marca-48.png")
        if ruta_logo:
            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            logo.setPixmap(QPixmap(ruta_logo).scaledToHeight(
                48, Qt.SmoothTransformation))
            vertical.addWidget(logo)

        titulo = QLabel(NOMBRE_PRODUCTO)
        titulo.setObjectName("tituloAcercaDe")
        titulo.setAlignment(Qt.AlignCenter)
        vertical.addWidget(titulo)

        # El dominio va aca y no en el titulo de la ventana: el producto lo
        # instala un tercero y el titulo tiene que ser el nombre del producto.
        detalles = QLabel(
            "Version {version}\n"
            "Desarrollo: {empresa}\n"
            "Web: https://{sitio}\n"
            "WhatsApp: {whatsapp}\n\n"
            "Ante cualquier falla de conexion con AFIP, copie el detalle del "
            "error y envielo por WhatsApp.".format(
                version=self._version() or "(sin version)",
                empresa=EMPRESA_DESARROLLO,
                sitio=SITIO_EMPRESA,
                whatsapp=WHATSAPP_EMPRESA))
        detalles.setObjectName("labelSubtitulo")
        detalles.setWordWrap(True)
        detalles.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vertical.addWidget(detalles)

        # Boton propio y no QDialogButtonBox: el de la caja de botones toma el
        # texto del idioma del sistema y en una maquina en ingles salia
        # "Close" en una pantalla que por lo demas esta toda en Castellano.
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("botonCerrar")
        cerrar.clicked.connect(dlg.reject)
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(cerrar)
        vertical.addLayout(fila)
        dlg.setAttribute(Qt.WA_DeleteOnClose, False)
        return dlg

    def _lupa(self):
        from PyQt5.QtGui import QIcon
        from libs.recursos import ruta_recurso
        return QIcon(ruta_recurso("imagenes/iconos/buscar.svg"))

    def _normalizar(self, texto):
        """Minúsculas y sin tildes, para que buscar 'configuracion' encuentre
        'Configuración'.

        Es el mismo criterio que usan las búsquedas contra la base (ver
        libs/busqueda.py): si la barra lateral acepta "configuracion" y el
        buscador de clientes no, el operador concluye que el cliente no existe.
        """
        return normalizar(texto)

    def _filtrar_lateral(self, texto):
        """Muestra solo los botones que coinciden, y esconde las secciones que
        se quedan sin ninguno."""
        consulta = self._normalizar(texto).strip()

        if not consulta:
            for boton in self.botonesNav.values():
                boton.setVisible(True)
            for clave in self.botonesNav:
                self._seccion_de[clave].setVisible(True)
            self.lblSinResultados.setVisible(False)
            return

        secciones_con_algo = set()
        encontrados = 0
        for clave, boton in self.botonesNav.items():
            coincide = (consulta in self._normalizar(boton.text())
                        or consulta in self._normalizar(clave)
                        or consulta in self._normalizar(
                            self._seccion_de[clave].text()))
            boton.setVisible(coincide)
            if coincide:
                encontrados += 1
                secciones_con_algo.add(id(self._seccion_de[clave]))

        for clave, boton in self.botonesNav.items():
            self._seccion_de[clave].setVisible(
                id(self._seccion_de[clave]) in secciones_con_algo)

        self.lblSinResultados.setText(
            "Sin resultados para\n«{}»".format(texto.strip()))
        self.lblSinResultados.setVisible(encontrados == 0)

    def _ir_al_primer_resultado(self):
        """Enter lleva al primer resultado, para poder emitir con el teclado."""
        for clave, boton in self.botonesNav.items():
            if boton.isVisible():
                boton.setFocus()
                return

    def enfocar_buscador(self):
        self.txtBuscar.setFocus()
        self.txtBuscar.selectAll()

    def buscar(self, texto):
        """Busca y deja el foco en el primer resultado. Lo usa el atajo."""
        self.txtBuscar.setText(texto)
        self._ir_al_primer_resultado()

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
