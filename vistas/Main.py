# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import BotonMain
from libs.Etiquetas import EtiquetaTitulo
from libs.GroupBox import Agrupacion
from vistas.VistaBase import VistaBase


class MainView(VistaBase):

    def initUi(self):
        self.setGeometry(150, 150, 500, 150)
        self.setWindowTitle('Vogel Gestion Simple')
        self.layoutPpal = QVBoxLayout(self)
        self.lblTitulo = EtiquetaTitulo(texto="Vogel Gestion Simple")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.groupBoxBotones = Agrupacion()
        self.layoutBotones = QHBoxLayout()

        self.btnVentaSimple = BotonMain(texto='&Nueva venta', imagen='imagenes/if_bill_416404.png')
        self.layoutBotones.addWidget(self.btnVentaSimple)

        self.btnClientes = BotonMain(texto='&Clientes', imagen='imagenes/if_kuser_1400.png')
        self.layoutBotones.addWidget(self.btnClientes)

        self.btnArticulo = BotonMain(texto='&Productos', imagen='imagenes/if_product-sales-report_49607.png')
        self.layoutBotones.addWidget(self.btnArticulo)

        self.btnFactura = BotonMain(texto='&Comprobantes', imagen='imagenes/if_bill_416404.png')
        self.layoutBotones.addWidget(self.btnFactura)

        self.btnCuentas = BotonMain(texto='C&uentas', imagen='imagenes/clipboard-paste-document-text.png')
        self.layoutBotones.addWidget(self.btnCuentas)

        self.btnReportes = BotonMain(texto='&Reportes', imagen='imagenes/excel.png')
        self.layoutBotones.addWidget(self.btnReportes)

        self.btnSeteo = BotonMain(texto='&Configuracion', imagen='imagenes/if_Settings-2_379349.png')
        self.layoutBotones.addWidget(self.btnSeteo)

        self.btnSalir = BotonMain(texto='&Salir', imagen='imagenes/if_Log Out_27856.png')
        self.layoutBotones.addWidget(self.btnSalir)

        # self.layoutPpal.addLayout(self.layoutBotones)
        self.groupBoxBotones.setLayout(self.layoutBotones)
        self.layoutPpal.addWidget(self.groupBoxBotones)
