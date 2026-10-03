# coding=utf-8
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton

from libs.Utiles import imagen, openFileNameDialog, GuardarArchivo, icono


class Boton(QPushButton):

    def __init__(self, *args, **kwargs):
        QPushButton.__init__(self, *args)

        texto = ''
        if 'texto' in kwargs:
            texto = kwargs['texto']

        self.setText(texto)

        # Que clase de boton es. Se lee antes de armar el icono porque de eso
        # depende que variante del set se use (ver abajo).
        clase = kwargs.get('estilo', '')

        if 'imagen' in kwargs:
            self.setIcon(QIcon(kwargs['imagen']))

            if 'tamanio' in kwargs:
                if kwargs['tamanio'] and isinstance(kwargs['tamanio'],QSize):
                    self.setIconSize(kwargs['tamanio'])
            else:
                self.setIconSize(QSize(32,32))

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])

        if 'autodefault' in kwargs:
            self.setAutoDefault(kwargs['autodefault'])
        else:
            self.setAutoDefault(True)
        self.setDefault(False)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        # Jerarquia de acciones. Sin esto todos los botones de una pantalla se
        # ven con el mismo peso, y el usuario no tiene forma de saber cual es la
        # accion principal y cual es la que cancela.
        #   'primario' -> la accion principal de la pantalla (una sola)
        #   'peligro'  -> borrar, anular, algo que no se puede deshacer
        #   'plano'    -> accion terciaria, sin borde
        # El color lo decide el tema (temas/pyfe.css); aca solo se marca.
        if 'estilo' in kwargs:
            self.setProperty("clase", clase)

        # El icono tiene que acompañar al color del boton, o se pierde:
        #   primario -> fondo azul, el icono azul desaparece sobre el fondo
        #   peligro  -> texto rojo, el icono azul dice otra cosa
        # Qt no sabe recolorear un QIcon desde el stylesheet, asi que las
        # variantes en blanco y en rojo tienen que existir como archivo
        # (tools/generar_iconos.py).
        #
        # Se resuelve por nombre de archivo porque la llamada puede pasar el
        # nombre ('nuevo') o la ruta ya resuelta (icono('nuevo')), y en los dos
        # casos hay que llegar al mismo archivo.
        if kwargs.get('imagen') and clase in ('primario', 'peligro'):
            import os as _os

            from libs.recursos import icono as _icono
            base = _os.path.basename(str(kwargs['imagen']))
            nombre = _os.path.splitext(base)[0]
            variante = _icono(nombre, claro=(clase == 'primario'),
                              peligro=(clase == 'peligro'))
            if variante and _os.path.normcase(variante) != _os.path.normcase(
                    str(kwargs['imagen'])):
                self.setIcon(QIcon(variante))


class BotonMain(Boton):
    """Boton grande de la pantalla de inicio.

    El icono va en 34 px y el texto en 11 pt: con el icono a 48 el dibujo le
    ganaba al texto y el boton se leia como un icono con un subtitulo, en vez
    de un boton con un icono. El alto minimo mantiene una zona de click
    comoda sin dejar botones gigantes.
    """

    def __init__(self, *args, **kwargs):
        Boton.__init__(self, *args, **kwargs)
        self.setMinimumHeight(84)
        self.setMinimumWidth(190)
        self.setIconSize(QSize(34, 34))
        fuente = self.font()
        fuente.setPointSizeF(11)
        self.setFont(fuente)

class BotonAceptar(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Aceptar'
        kwargs['imagen'] = icono('check')
        kwargs['tamanio'] = QSize(32,32)
        Boton.__init__(self, *args, **kwargs)

# Textos de los botones estandar de un dialogo, en castellano.
# Qt los rotula con el idioma del sistema operativo y, sin los archivos de
# traduccion de Qt instalados, salen "OK" y "Cancel" en ingles dentro de una
# app que esta toda en castellano. DialogoPassword y PrimerArranque ya lo
# resolvian a mano; esto lo deja igual en un solo lugar y de paso le da al
# boton de aceptar la jerarquia de accion principal.
TEXTOS_DIALOGO = {
    'aceptar': "Aceptar",
    'cancelar': "Cancelar",
}


def botonera_dialogo(aceptar=None, cancelar=None, **kwargs):
    """Devuelve un QDialogButtonBox Aceptar/Cancelar en castellano.

    Se usa en vez de armar el QDialogButtonBox a mano para no volver a dejar
    un dialogo en ingles por olvido.
    """
    from PyQt5.QtWidgets import QDialogButtonBox

    caja = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    caja.button(QDialogButtonBox.Ok).setText(aceptar or TEXTOS_DIALOGO['aceptar'])
    caja.button(QDialogButtonBox.Ok).setProperty("clase", "primario")
    caja.button(QDialogButtonBox.Cancel).setText(cancelar or TEXTOS_DIALOGO['cancelar'])
    return caja

class BotonCerrarFormulario(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Cerrar'
        kwargs['imagen'] = icono('cerrar')
        kwargs['tamanio'] = QSize(32,32)
        Boton.__init__(self, *args, **kwargs)
        self.setDefault(False)

class BotonArchivo(Boton):
    widgetArchivo = None
    files = None
    guardar = False
    directorio = ""
    nombre_archivo = ""

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '...'
        if 'archivos' in kwargs:
            self.files = kwargs['archivos']

        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.guardar:
                self.archivo = openFileNameDialog(files=self.files)
            else:
                self.archivo = GuardarArchivo(caption="Guardar archivo", directory=self.directorio,
                                                             filter=self.files,
                                                             filename=self.nombre_archivo)
            if self.widgetArchivo and self.archivo:
                self.widgetArchivo.setText(self.archivo)