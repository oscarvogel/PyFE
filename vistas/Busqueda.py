# -*- coding: utf-8 -*-
import decimal
import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QVBoxLayout, QTableWidget, QHBoxLayout, QTableWidgetItem, QMainWindow, QApplication

from libs import Ventanas
from libs.Botones import BotonAceptar, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Formulario import Formulario
from libs.Utiles import LeerIni


class UiBusqueda(Formulario):

    modelo = None #modelo sobre la que se realiza la busqueda
    cOrden = "" #orden de busqueda
    limite = 100 #maximo registros a mostrar
    campos = [] #campos a mostrar
    campoBusqueda = "nombre" #campo sobre el cual realizar la busqueda
    lRetval = False #indica si presiono en aceptar o cancelar
    ValorRetorno = '' #valor que selecciono el usuario
    camposTabla = None #los campos de la tabla
    campoRetorno = None #campo del cual obtiene el dato para retornar el codigo/valor
    colRetorno = 0 #la columna de donde retorna el valor
    colBusqueda = 0 #la columno que establece la busqueda
    campoRetornoDetalle = '' #campo que retorna el detalle
    condiciones = '' #condiciones de filtrado

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)
        #self.CargaDatos()

    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(829, 556)
        Dialog.setWindowTitle("Busqueda de datos en {}".format(self.modelo._meta.name if self.modelo else ""))
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lineEdit = EntradaTexto(Dialog, tooltip='Ingresa tu busqueda',
                                     placeholderText="Ingresa tu busqueda")
        self.lineEdit.setObjectName("lineEdit")
        self.verticalLayout.addWidget(self.lineEdit)
        self.tableView = QTableWidget(Dialog)
        self.tableView.setObjectName("tableView")
        font = QFont()
        font.setPointSize(12)
        self.tableView.setFont(font)
        self.verticalLayout.addWidget(self.tableView)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnAceptar = BotonAceptar(textoBoton="&Seleccionar")
        self.btnAceptar.setObjectName("btnAceptar")
        self.horizontalLayout.addWidget(self.btnAceptar)
        self.btnCancelar = BotonCerrarFormulario()
        self.btnCancelar.setObjectName("btnCancelar")
        self.horizontalLayout.addWidget(self.btnCancelar)
        self.verticalLayout.addLayout(self.horizontalLayout)

        #self.retranslateUi(Dialog)
        self.btnCancelar.clicked.connect(self.Cerrar)
        self.lineEdit.textChanged.connect(self.CargaDatos)
        self.btnAceptar.clicked.connect(self.Aceptar)
        self.tableView.cellClicked.connect(self.cell_was_clicked)
        self.tableView.doubleClicked.connect(self.Aceptar)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Busqueda en " + self.tabla))
        self.btnAceptar.setText(_translate("Dialog", "Aceptar"))
        self.btnCancelar.setText(_translate("Dialog", "Cerrar"))

    def Aceptar(self):
        self.lRetval = True
        if self.tableView.currentItem():
            self.ValorRetorno = self.tableView.currentItem().text()
            self.ValorRetorno = self.tableView.item(self.tableView.currentRow(), self.colRetorno).text()
            self.campoRetornoDetalle  = self.tableView.item(self.tableView.currentRow(), self.colBusqueda).text()
            print("Seleccionado {} columna {} fila {}".format(self.ValorRetorno,
                                                              self.tableView.currentColumn(),
                                                              self.tableView.currentRow()) )
            self.close()

    def cell_was_clicked(self, row, column):
        item = self.tableView.item(row, column)

        self.ValorRetorno = item.text()
        logging.info("Row {} and Column {} was clicked value {} item {}"
                     .format(row, column, self.tableView.currentItem().text(), item))

    def CargaDatos(self):
        if not self.modelo:
            Ventanas.showAlert(LeerIni('nombre_sistema'), "No se ha establecido el modelo para la busqueda")
            return

        textoBusqueda = self.lineEdit.text()

        rows = self.modelo.select().dicts()

        if self.condiciones:
            for c in self.condiciones:
                rows = rows.where(c)

        if textoBusqueda:
            rows = rows.where(self.campoBusqueda.contains(textoBusqueda))

        self.tableView.setColumnCount(len(self.campos))
        self.tableView.setRowCount(len(rows))

        logging.info("SQL de condiciones de busqueda {}".format(self.condiciones))
        #self.tableView.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

        for col in range(0, len(self.campos)):
            if self.campos[col] == self.campoRetorno.column_name:
                self.colRetorno = col
            if self.campos[col] == self.campoBusqueda.column_name:
                self.colBusqueda = col

            self.tableView.setHorizontalHeaderItem(col, QTableWidgetItem(self.campos[col].capitalize()))

        fila = 0
        for row in rows:
            for col in range(0, len(self.campos)):
                if isinstance(row[self.campos[col]], (int, decimal.Decimal,)):
                    item = QTableWidgetItem(str(row[self.campos[col]]))
                else:
                    item = QTableWidgetItem(QTableWidgetItem(row[self.campos[col]]))

                item.setFlags(QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled)
                self.tableView.setItem(fila, col, item)

            fila += 1
        self.tableView.resizeRowsToContents()
        self.tableView.resizeColumnsToContents()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Down:
            self.tableView.setFocus()
        elif event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.btnAceptar.click()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = UiBusqueda()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
