# coding=utf-8
import logging
import os
import sys

from PyQt5.QtWidgets import QApplication, QDialog
from os.path import join


from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

aplicar_compatibilidad_pysimplesoap()

from libs.Utiles import LeerIni, initialize_logger


def _configurar_instalacion_nueva():
    """Si la instalacion nunca fue configurada, corre el asistente.

    Tiene que pasar antes de importar controladores.Main, porque ese
    import arma la conexion a la base. Devuelve False si el usuario
    cancela, para no seguir arrancando a ciegas.
    """
    from libs.instalacion import (es_primer_arranque, guardar_config_inicial,
                                  marcar_instalacion_configurada)

    if not es_primer_arranque():
        # Instalacion previa a este cambio: se marca para que el asistente
        # no vuelva a aparecer. No se le pide nada al usuario.
        marcar_instalacion_configurada()
        return True

    print("No se encontro una configuracion previa, se inicia el asistente.")
    from vistas.PrimerArranque import DialogoPrimerArranque

    dialogo = DialogoPrimerArranque()
    if dialogo.exec_() != QDialog.Accepted:
        print("Configuracion inicial cancelada. Se sale.")
        return False

    resultado = guardar_config_inicial(dialogo.datos())
    print("Configuracion guardada. Base: {}{}".format(
        resultado["base"],
        " (password protegido con DPAPI)" if resultado.get("modo_secreto") == "dpapi" else ""))
    return True


def _pedir_password_base():
    """Si hace falta el password de la base, lo pide aca.

    Va despues de crear la QApplication porque es un dialogo. Solo aparece
    en instalaciones MySQL: con sqlite el password no se usa para conectar.

    Opciones: se puede elegir recordarlo, en cuyo caso se guarda protegido
    por DPAPI, o dejarlo solo en memoria y que se pida en cada arranque.
    Devuelve False si el usuario cancela, para no seguir arrancando a
    ciegas contra una base a la que no va a poder entrar.
    """
    if LeerIni(clave='base') != 'mysql':
        return True

    from libs.secretos import (guardar_en_sesion, obtener_de_sesion,
                               persistir_password_base, resolver_password_base)

    if resolver_password_base() is not None:
        return True

    from vistas.DialogoPassword import DialogoPassword

    dialogo = DialogoPassword(
        mensaje="No se pudo leer el password de la base desde la "
                "configuracion. Ingreselo para continuar.")
    if dialogo.exec_() != QDialog.Accepted:
        return False

    password, recordar = dialogo.valores()
    if not password:
        return False

    guardar_en_sesion("password_base", password)
    if recordar:
        try:
            persistir_password_base(password)
        except Exception as e:
            # No es motivo para no entrar: el password ya quedo en memoria.
            print("No se pudo guardar el password: {}".format(type(e).__name__))
    return True


def _carpeta_de_la_app():
    """Donde esta instalado el programa."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _asegurar_carpeta_de_trabajo():
    """Deja la carpeta de trabajo apuntando a la instalacion.

    LeerIni y GrabarIni resuelven sistema.ini con os.getcwd(). Con un
    ejecutable de una sola pieza, el cwd es desde donde el usuario hizo
    doble clic, que puede ser el escritorio: el sistema.ini terminaria
    en cualquier lado y en 'Program Files' no habria permiso de escritura.

    Asi que, siTodavia no hay una carpeta de trabajo configurada, se fija
    a la carpeta de la app, se cambia el cwd y se guarda. Esto tambien
    deja que el instalador no tenga que escribir el sistema.ini: lo crea
    la propia app con los datos del asistente.
    """
    from libs.Utiles import GrabarIni, LeerIni

    actual = LeerIni(clave="iniciosistema")
    if actual and os.path.isdir(actual) and os.path.abspath(actual) != os.path.abspath(os.getcwd()):
        return actual

    carpeta = _carpeta_de_la_app().rstrip("/\\") + "/"

    # Antes de tocar nada de configuracion: si no, el archivo se escribe
    # en el cwd equivocado.
    try:
        if os.path.abspath(carpeta) != os.path.abspath(os.getcwd()):
            os.chdir(carpeta)
    except OSError as e:
        print("No se pudo cambiar a la carpeta del programa: {}".format(e))
        return actual or carpeta

    try:
        GrabarIni(clave="iniciosistema", key="param", valor=carpeta)
    except Exception as e:
        print("No se pudo guardar iniciosistema: {}".format(type(e).__name__))
    return carpeta


def inicio():
    # 0) Carpeta de trabajo. Tiene que ser lo primero: LeerIni resuelve
    #    sistema.ini con os.getcwd(), y en un ejecutable de una sola pieza
    #    el cwd es desde donde el usuario hizo doble clic. Sin esto, el
    #    archivo se escribe en el escritorio y no hay permiso en
    #    'Program Files'.
    carpeta = _asegurar_carpeta_de_trabajo()

    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)

    # Estilo, fuente y colores, antes de construir ninguna ventana. Se aplica
    # sobre la QApplication entera para que las 30+ vistas hereden el mismo
    # tema sin tener que pedirlo una por una. Antes no habia ninguna capa de
    # estilo: la app corria con el aspecto crudo del sistema.
    from libs.tema import aplicar_tema
    tema = aplicar_tema(app)
    if not tema.get("css"):
        print("No se encontro el tema en {}. Se usa el estilo base.".format(
            tema.get("ruta_css") or "temas/pyfe.css"))
    else:
        print("Tema aplicado: {} (fuente {}, estilo {})".format(
            tema["ruta_css"], tema["fuente"], tema["estilo"]))

    # 1) Instalacion nueva: asistente. Crea el sistema.ini con los datos
    #    que da el usuario, asi que va antes que todo lo demas.
    if not _configurar_instalacion_nueva():
        return

    # 2) Logger
    initialize_logger(carpeta)

    if LeerIni(clave='homo') == 'S':
        print("Sistema en modo homologacion")
    else:
        print("Sistema en modo produccion")

    # 4) Password, solo si es MySQL y no se pudo leer de la config.
    if not _pedir_password_base():
        print("No se ingreso el password de la base. Se sale.")
        return

    # 5) El import va acá y no arriba a propósito: controladores.Main arrastra
    #    los modelos, que arman la conexión a la base, y eso necesita el
    #    password que acaba de pedir el usuario.
    from controladores.Main import Main

    ex = Main()
    ex.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    inicio()
