# coding=utf-8
import logging
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
    from libs.instalacion import es_primer_arranque, guardar_config_inicial

    if not es_primer_arranque():
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


def _asegurar_iniciosistema():
    """Deja iniciosistema apuntando a una carpeta escribible.

    El instalador lo setea, pero si alguien corre la app sin instalar (o
    si el instalador no lo hizo) queda vacio y los logs se intentan
    escribir en el directorio de trabajo, que en Program Files no tiene
    permiso de escritura.
    """
    import os

    from libs.Utiles import GrabarIni, LeerIni

    actual = LeerIni(clave="iniciosistema")
    if actual and os.path.isdir(actual):
        return actual

    if getattr(sys, "frozen", False):
        carpeta = os.path.dirname(os.path.abspath(sys.executable))
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))

    carpeta = carpeta.rstrip("/\\") + "/"
    try:
        GrabarIni(clave="iniciosistema", key="param", valor=carpeta)
    except Exception as e:
        print("No se pudo guardar iniciosistema: {}".format(type(e).__name__))
    return carpeta


def inicio():
    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)

    # 1) Instalacion nueva: asistente. Va primero porque escribe la config
    #    que todo lo demas necesita.
    if not _configurar_instalacion_nueva():
        return

    # 2) Carpeta de trabajo, antes de tocar el logger.
    carpeta = _asegurar_iniciosistema()

    # 3) Logger
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
