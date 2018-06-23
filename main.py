# coding=utf-8
import logging
import sys
from os.path import join

from PyQt4.QtGui import QApplication

from controladores.Main import Main
from libs.Utiles import LeerIni


def inicio():
    logging.basicConfig(filename=join(LeerIni("InicioSistema"), 'errors.log'), level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    # Instancia para iniciar una aplicación
    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)
    ex = Main()
    ex.run()
    sys.exit(app.exec_())

if __name__ == "__main__":
    inicio()
