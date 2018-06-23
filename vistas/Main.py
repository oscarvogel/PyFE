# coding=utf-8
from PyQt4.QtGui import QHBoxLayout, QApplication

from libs.Botones import BotonMain
from vistas.VistaBase import VistaBase


class MainView(VistaBase):

    def initUi(self):
        self.setGeometry(150, 150, 500, 150)
        self.setWindowTitle('Factura Electronica')
        self.layoutPpal = QHBoxLayout(self)

        self.btnClientes = BotonMain(texto='&Clientes', imagen='imagenes/if_kuser_1400.png')
        self.layoutPpal.addWidget(self.btnClientes)

        self.btnFactura = BotonMain(texto='&Facturacion', imagen='imagenes/if_bill_416404.png')
        self.layoutPpal.addWidget(self.btnFactura)

        self.btnArticulo = BotonMain(texto='&Articulos', imagen='imagenes/if_product-sales-report_49607.png')
        self.layoutPpal.addWidget(self.btnArticulo)

        self.btnSeteo = BotonMain(texto='&Configuracion', imagen='imagenes/if_Settings-2_379349.png')
        self.layoutPpal.addWidget(self.btnSeteo)

        self.btnSalir = BotonMain(texto='&Salir', imagen='imagenes/if_Log Out_27856.png')
        self.layoutPpal.addWidget(self.btnSalir)
