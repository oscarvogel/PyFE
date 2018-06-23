# coding=utf-8
import sys

from PyQt4.QtGui import QMessageBox, QApplication, QWidget, QPushButton


def showAlert(titulo, mensaje):

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(mensaje)
    msg.setWindowTitle(titulo)
    msg.setStandardButtons(QMessageBox.Ok)

    retval = msg.exec_()

    return retval

def showConfirmation(titulo, mensaje):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setText(mensaje)
    msg.setWindowTitle(titulo)
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    retval = msg.exec_()

    return retval

def window():
   app = QApplication(sys.argv)
   w = QWidget()
   b = QPushButton(w)
   b.setText("Show message!")

   b.move(50,50)
   b.clicked.connect(showdialog)
   w.setWindowTitle("PyQt Dialog demo")
   w.show()
   sys.exit(app.exec_())

def showdialog():
    retval = showConfirmation("Sistema", "Desea imprimir el presupuesto?")
    if retval == QMessageBox.Ok:
        print("Valor de retorno {}".format(retval))


if __name__ == "__main__":
    window()