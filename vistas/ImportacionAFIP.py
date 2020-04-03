#importaciono de comprobantes emitidos en forma online
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.Checkbox import CheckBox
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.Fechas import Fecha
from libs.Utiles import imagen, InicioMes, FinMes
from vistas.VistaBase import VistaBase


class ImportaAFIPView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Importacion comprobantes AFIP")
        layoutPpal = QVBoxLayout(Form)

        self.avance = Avance()
        layoutPpal.addWidget(self.avance)

        layout_archivo_cab = QHBoxLayout()
        lblArchivo = Etiqueta(texto="Archivo cabecera")
        self.textArchivo = EntradaTexto(placeholderText="Ubicacion cabecera")
        self.btnArchivo = Boton(imagen=imagen("folder_search.png"))
        layout_archivo_cab.addWidget(lblArchivo)
        layout_archivo_cab.addWidget(self.textArchivo)
        layout_archivo_cab.addWidget(self.btnArchivo)
        layoutPpal.addLayout(layout_archivo_cab)

        layout_archivo_det = QHBoxLayout()
        lblArchivo_det = Etiqueta(texto="Archivo IVA")
        self.textArchivo_det = EntradaTexto(placeholderText="Ubicacion IVA")
        self.btnArchivo_det = Boton(imagen=imagen("folder_search.png"))
        layout_archivo_det.addWidget(lblArchivo_det)
        layout_archivo_det.addWidget(self.textArchivo_det)
        layout_archivo_det.addWidget(self.btnArchivo_det)
        layoutPpal.addLayout(layout_archivo_det)

        layoutFechas = QHBoxLayout()
        lblDesdeFecha = Etiqueta(texto="Desde fecha")
        self.textDesdeFecha = Fecha(fecha=InicioMes())
        lblHastaFecha = Etiqueta(texto="Hasta fecha")
        self.textHastaFecha = Fecha(fecha=FinMes())
        layoutFechas.addWidget(lblDesdeFecha)
        layoutFechas.addWidget(self.textDesdeFecha)
        layoutFechas.addWidget(lblHastaFecha)
        layoutFechas.addWidget(self.textHastaFecha)
        layoutPpal.addLayout(layoutFechas)

        layoutParametros = QHBoxLayout()
        self.checkBorra = CheckBox(texto="Borra los movimientos?", checked=True)
        self.consultaAFIP = CheckBox(texto="Consulta datos con AFIP?")
        layoutParametros.addWidget(self.checkBorra)
        layoutParametros.addWidget(self.consultaAFIP)
        layoutPpal.addLayout(layoutParametros)

        layoutBotones = QHBoxLayout()
        self.btnImportar = Boton(texto="Importar", imagen=imagen("importar.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnImportar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)
