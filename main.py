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
                                  marcar_instalacion_configurada,
                                  normalizar_cuit_emisor)

    if not es_primer_arranque():
        # Instalacion previa a este cambio: se marca para que el asistente
        # no vuelva a aparecer. No se le pide nada al usuario.
        marcar_instalacion_configurada()
        _avisar_cuit_discrepante(normalizar_cuit_emisor())
        return True

    print("No se encontro una configuracion previa, se inicia el asistente.")
    from vistas.PrimerArranque import DialogoPrimerArranque

    dialogo = DialogoPrimerArranque()
    if dialogo.exec_() != QDialog.Accepted:
        print("Configuracion inicial cancelada. Se sale.")
        return False

    try:
        resultado = guardar_config_inicial(dialogo.datos())
    except OSError as e:
        # Lo normal es que la carpeta de datos este bien. Si tampoco se puede
        # escribir, se dice que paso y que hacer: un PermissionError desnudo
        # mataba el programa con un traceback despues de que el usuario
        # completara el asistente entero.
        from libs.Ventas import showError

        showError("No se pudo guardar la configuracion",
                  "Los datos del asistente no se pudieron guardar.",
                  que_hacer="Copiá la carpeta del programa a una ubicación donde "
                            "puedas escribir (por ejemplo C:\\Asiento) y volvé a "
                            "abrirla. Si el problema sigue, mandale este "
                            "detalle a soporte.",
                  detalle=str(e))
        print("No se pudo guardar la configuracion inicial: {}".format(e))
        return False

    print("Configuracion guardada. Base: {}{}".format(
        resultado["base"],
        " (password protegido con DPAPI)" if resultado.get("modo_secreto") == "dpapi" else ""))

    # El asistente escribe [FACTURA] cuit. Esta llamada deja de acuerdo
    # [WSFEv1] cuit, que es la que viaja a ARCA: sin esto, una instalacion
    # nueva queda con 00000000000 y no puede emitir. Ver libs/instalacion.py.
    normalizado = normalizar_cuit_emisor()
    if normalizado["estado"] == "falta":
        print("El CUIT de la empresa no quedo bien. Hay que corregirlo en "
              "Configuracion antes de emitir.")
    return True


def _avisar_cuit_discrepante(resultado):
    """Dos CUIT reales y distintos en las dos claves: hay que elegir uno.

    No se puede decidir solo: la clave de Configuracion puede ser la buena y
    la de facturacion la de una instalacion vieja, o al reves. Por eso se
    avisa y no se escribe nada.
    """
    if resultado.get("estado") != "discrepan":
        return
    print("AVISO: hay dos CUIT de emisor distintos ({}). Se usa el de "
          "Configuracion. Corregilo desde Configuracion > Datos empresa."
          .format(resultado.get("conflicto", "")))


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


# Referencia global al controlador del actualizador. Vive aca y no en una
# variable local de `inicio()` porque el chequeo arranca un QThread: si nadie
# lo tiene grabbed, Python lo recolecta mientras corre y la app se cae al
# terminar la descarga.
_ACTUALIZADOR = None


def _chequear_actualizaciones(parent):
    """Avisa si hay una version nueva en vogel-releases.

    Va aca, despues de que la ventana esta en pantalla, y no en el
    constructor de `Main`: construir el controlador dispara la red, y
    cualquier test que arme `Main()` (tests/test_componentes.py) se comeria
    una descarga de verdad y quedaria esperando.

    En desarrollo no hace nada: `libs/build_info` tiene app_id 'development'.
    """
    global _ACTUALIZADOR
    try:
        from controladores.Actualizador import ActualizadorController

        controlador = ActualizadorController()
        if not controlador.habilitado():
            # En desarrollo no se guarda nada: no hay hilo que sostener y no
            # hace falta dejar un controlador colgado.
            return
        _ACTUALIZADOR = controlador
        _ACTUALIZADOR.hilo = controlador.chequear_al_arranque(parent=parent)
    except Exception as e:
        # No hay por que dejar de abrir la app por un chequeo de version.
        print("No se pudo chequear actualizaciones: {}".format(
            type(e).__name__))


def _asegurar_carpeta_de_trabajo():
    """Deja el directorio de trabajo apuntando a la instalacion.

    LeerIni y GrabarIni resuelven sistema.ini con el directorio de trabajo. Con
    un ejecutable de una sola pieza, el cwd es desde donde el usuario hizo
    doble clic, que puede ser el escritorio: el sistema.ini terminaria en
    cualquier lado.

    Asi que se cambia el cwd a la carpeta de la app, y ese cambio va PRIMERO,
    antes de tocar la configuracion.

    El orden no es cosmetico: libs/rutas decide donde se escribe mirando si el
    directorio de trabajo se puede escribir. Con un ejecutable de una sola pieza
    el cwd es el escritorio, que SI se puede escribir, asi que si se preguntara
    antes del cambio el sistema.ini de una instalacion nueva se crearia en el
    escritorio.

    Que el cwd sea una carpeta de solo lectura no es problema: entrar en
    'Program Files' se puede, lo que no se puede es escribir. Por eso la
    configuracion, la base y los logs van a la carpeta de datos del usuario
    (libs/rutas.py), mientras que los recursos --plantillas, imagenes, conf-- se
    siguen leyendo de la carpeta de la app, que es donde estan.

    Devuelve la carpeta de datos, que es donde van los logs.
    """
    from libs.Utiles import GrabarIni
    from libs import rutas

    carpeta = _carpeta_de_la_app().rstrip("/\\") + "/"

    try:
        if os.path.abspath(carpeta) != os.path.abspath(os.getcwd()):
            os.chdir(carpeta)
    except OSError as e:
        print("No se pudo cambiar a la carpeta del programa: {}".format(e))

    # El cwd recien cambio: las decisiones de carpeta ya tomadas antes (por
    # ejemplo una importacion que leyo la configuracion) no cuentan.
    rutas.limpiar_cache()

    datos = rutas.carpeta_datos()
    if os.path.normcase(os.path.abspath(datos)) != os.path.normcase(
            os.path.abspath(os.getcwd())):
        print("La carpeta del programa no se puede escribir. La configuracion "
              "y la base quedan en {}".format(datos))

    # Los datos que ya estaban en la carpeta del programa se traen para la
    # carpeta de datos. Sin esto, un cliente que ya venia usando el sistema
    # veria la app como recien instalada y la base VACIA.
    rutas.migrar_desde_instalacion(registrar=print)

    # 'iniciosistema' sigue apuntando a la carpeta del programa: de ahi salen
    # los recursos. Que no se pueda escribir aca no importa para leerlos.
    try:
        GrabarIni(clave="iniciosistema", key="param", valor=carpeta)
    except Exception as e:
        print("No se pudo guardar iniciosistema: {}".format(type(e).__name__))
    return datos


def inicio():
    # 0) Carpeta de trabajo. Tiene que ser lo primero de todo: el cwd es desde
    #    donde el usuario hizo doble clic (el escritorio, con un ejecutable de
    #    una sola pieza) y tanto libs/rutas como libs.recursos lo usan para
    #    decidir donde esta cada cosa. Devuelve la carpeta de DATOS, que es
    #    distinta de la del programa cuando esta no se puede escribir.
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
    _chequear_actualizaciones(ex.view)
    sys.exit(app.exec_())


if __name__ == "__main__":
    inicio()
