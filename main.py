# coding=utf-8
import logging
import sys

from PyQt5.QtWidgets import QApplication, QDialog
from os.path import join


from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

aplicar_compatibilidad_pysimplesoap()

from libs.Utiles import LeerIni, initialize_logger


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


def inicio():
    initialize_logger(LeerIni("iniciosistema"))
    # logging.basicConfig(filename=join(LeerIni("iniciosistema"), 'errors.log'), level=logging.DEBUG,
    #                     format='%(asctime)s %(message)s',
    #                     datefmt='%m/%d/%Y %I:%M:%S %p')
    if LeerIni(clave='homo') == 'S':
        print("Sistema en modo homologacion")
    else:
        print("Sistema en modo produccion")
    # Instancia para iniciar una aplicación
    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)

    if not _pedir_password_base():
        print("No se ingreso el password de la base. Se sale.")
        return

    # El import va acá y no arriba a propósito: controladores.Main arrastra los
    # modelos, que arman la conexión a la base, y eso necesita el password que
    # acaba de pedir el usuario.
    from controladores.Main import Main

    ex = Main()
    ex.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    inicio()
