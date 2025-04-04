from controladores.ControladorBase import ControladorBase
from controladores.Remitos import RemitoController
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Remitos import Remito
from vistas.ReImprimeFactura import ReImprimeFacturaView


class ReImprimeRemitoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ReImprimeFacturaView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaRemitosCliente)
        self.view.btnImprimir.clicked.connect(self.Imprimir)
        
    @inicializar_y_capturar_excepciones
    def Imprimir(self, *args, **kwargs):
        row = self.view.gridDatos.currentRow()
        if row >= 0:
            remito = Remito.get(Remito.idremito == self.view.gridDatos.ObtenerItem(fila=row, col='idcabecera'))
            controlador_factura = RemitoController()
            controlador_factura.Imprimir(remito)
        
    @inicializar_y_capturar_excepciones
    def CargaRemitosCliente(self, *args, **kwargs):
        remitos = Remito.select().where(Remito.cliente == self.view.controles['cliente'].text())
        self.view.gridDatos.setRowCount(0)
        for r in remitos:
            self.view.gridDatos.AgregaItem(items=[r.fecha, r.numero, r.total, r.idremito])