# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Utiles import imagen


class EmailClienteView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.resize(650, 350)
        self.setWindowTitle("Email de clientes")
        self.verticalLayoutDatos = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)

        self.gridEmail = Grilla()
        self.gridEmail.enabled = True
        cabeceras = [
            'EMail', 'idemailcliente'
        ]
        self.gridEmail.columnasOcultas = [1,]
        self.gridEmail.OcultaColumnas()
        self.gridEmail.columnasHabilitadas = [0,]
        self.gridEmail.ArmaCabeceras(cabeceras=cabeceras)
        self.verticalLayoutDatos.addWidget(self.gridEmail)

        self.layoutBotones = QHBoxLayout()
        self.btnGraba = Boton(texto='Graba', imagen=imagen('save.png'))
        self.btnCerrar = BotonCerrarFormulario()
        self.btnAgregar = Boton(texto="Agregar", imagen=imagen('new.png'))
        self.btnBorrar = Boton(texto="Borrar", imagen=imagen('delete.png'))
        self.layoutBotones.addWidget(self.btnAgregar)
        self.layoutBotones.addWidget(self.btnGraba)
        self.layoutBotones.addWidget(self.btnBorrar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
