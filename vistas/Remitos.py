from email.policy import default
from gc import enable
from libs.Botones import Boton
from libs.EntradaTexto import EntradaTexto, Factura, TextEdit
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Fechas import Fecha
from libs.Grillas import Grilla
from libs.GroupBox import Agrupacion
from libs.Utiles import imagen
from modelos import Clientes
from modelos import Tipocomprobantes
from modelos.Formaspago import ComboFormapago
from vistas.VistaBase import VistaBase
from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QHBoxLayout

class RemitoView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Remito")
        # self.setGeometry(0, 0, 800, 600)
        self.resize(1030, 600)
        layout_ppal = QVBoxLayout(Form)
        # layout_ppal.addWidget(EtiquetaTitulo(texto=self.windowTitle()))
        
        layout_parametros = QGridLayout()
        layout_parametros.addWidget(Etiqueta(texto="Cliente"), 0, 0)
        self.cliente = Clientes.Valida()
        lbl_nombre = Etiqueta()
        self.cliente.widgetNombre = lbl_nombre
        layout_parametros.addWidget(self.cliente, 0, 1)
        layout_parametros.addWidget(lbl_nombre, 0, 2)
        layout_parametros.addWidget(Etiqueta(texto="Fecha"), 0, 3)
        self.fecha = Fecha()
        layout_parametros.addWidget(self.fecha, 0, 3)
        
        layout_parametros.addWidget(Etiqueta(texto="Tipo de Comprobante"), 1, 0)
        self.tipo_comprobante = Tipocomprobantes.Valida()
        self.tipo_comprobante.setText("92")
        self.tipo_comprobante.valida()
        lbl_tipo_cpte = Etiqueta()
        self.tipo_comprobante.widgetNombre = lbl_tipo_cpte
        layout_parametros.addWidget(self.tipo_comprobante, 1, 1)
        layout_parametros.addWidget(lbl_tipo_cpte, 1, 2)
        
        self.numero = Factura()
        layout_parametros.addWidget(Etiqueta(texto="Numero"), 1, 3)
        layout_parametros.addLayout(self.numero, 1, 4)

        self.forma_pago = ComboFormapago()
        layout_parametros.addWidget(Etiqueta(texto="Forma de pago"), 2, 0)
        layout_parametros.addWidget(self.forma_pago, 2, 1, 1, 4)
        
        self.observaciones = TextEdit()
        layout_parametros.addWidget(Etiqueta(texto="Observaciones"), 3, 0)
        layout_parametros.addWidget(self.observaciones, 3, 1, 1, 4)
        
        self.grilla = Grilla()
        cabeceras = ["Producto", "Detalle", "Cantidad", "Unitario", "Total", "_id"]
        self.grilla.ArmaCabeceras(cabeceras)
        self.grilla.columnasHabilitadas = [0, 1, 2, 3]
        self.grilla.enabled = True
        item = [
            1, '', 1, 0, 0
        ]
        self.grilla.AgregaItem(items=item)
        layout_parametros.addWidget(self.grilla, 4, 0, 1, 5)
        
        layout_ppal.addLayout(layout_parametros)
        
        layout_totales = QHBoxLayout()
        lbl_total = Etiqueta(texto="Total")
        self.total = EntradaTexto(enabled=False)
        layout_totales.addWidget(lbl_total)
        layout_totales.addWidget(self.total)
        layout_ppal.addLayout(layout_totales)
        
        layout_botones = QHBoxLayout()
        self.btn_guardar = Boton(texto="Guardar", imagen=imagen("save.png"), autodefault=False)
        self.btn_borrar = Boton(texto="Borrar", imagen=imagen("delete.png"), autodefault=False)
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"), autodefault=False)
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
        
