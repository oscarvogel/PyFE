# -*- coding: utf-8 -*-
import decimal
import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QVBoxLayout, QTableWidget, QHBoxLayout, QTableWidgetItem, QMainWindow, QApplication, QLabel

from libs import Ventanas
from libs.Botones import BotonAceptar, BotonCerrarFormulario
from libs.busqueda import contiene
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
        self.lblCuenta = QLabel("")
        self.lblCuenta.setObjectName("lblCuenta")
        self.verticalLayout.addWidget(self.lblCuenta)
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
            rows = rows.where(contiene(self.campoBusqueda, textoBusqueda))

        # El limite va antes de contar las filas. Antes se hacia
        # setRowCount(len(rows)), y len() de una consulta de peewee la ejecuta
        # entera: con una tabla grande eso traia miles de filas a memoria en
        # cada tecla, sin usar el `limite` que la clase declaraba y nunca
        # aplicaba.
        total = rows.count()
        filas = list(rows.limit(self.limite))

        self.tableView.setColumnCount(len(self.campos))
        self.tableView.setRowCount(len(filas))

        if not filas:
            self.lblCuenta.setText("Sin resultados para {!r}".format(textoBusqueda))
        elif total > len(filas):
            self.lblCuenta.setText(
                "Mostrando {} de {} coincidencias".format(len(filas), total))
        else:
            self.lblCuenta.setText("{} coincidencia{}".format(
                total, "" if total == 1 else "s"))

        logging.info("SQL de condiciones de busqueda {}".format(self.condiciones))
        #self.tableView.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

        # `campos` puede venir como nombres ("idcliente") o como campos de
        # peewee (Cliente.idcliente). Hoy todos los que llaman pasan nombres, y
        # por eso el .capitalize() de abajo no se rompio nunca: un campo de
        # peewee no tiene capitalize(). El detalle es que esto corre DENTRO de
        # un slot de Qt (textChanged), y una excepcion ahi no se muestra: PyQt5
        # aborta el proceso entero sin dejar traza. Un error en un buscador no
        # puede llevarse la aplicacion por delante, asi que los dos formatos
        # entran igual.
        nombres = [c if isinstance(c, str) else c.column_name for c in self.campos]

        for col in range(0, len(nombres)):
            if nombres[col] == self.campoRetorno.column_name:
                self.colRetorno = col
            if nombres[col] == self.campoBusqueda.column_name:
                self.colBusqueda = col

            self.tableView.setHorizontalHeaderItem(col, QTableWidgetItem(nombres[col].capitalize()))

        fila = 0
        for row in filas:
            for col in range(0, len(nombres)):
                if isinstance(row[nombres[col]], (int, decimal.Decimal,)):
                    item = QTableWidgetItem(str(row[nombres[col]]))
                else:
                    item = QTableWidgetItem(QTableWidgetItem(row[nombres[col]]))

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
