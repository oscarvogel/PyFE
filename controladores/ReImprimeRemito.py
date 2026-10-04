from controladores.ControladorBase import ControladorBase
from controladores.Remitos import RemitoController
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Clientes import Cliente
from modelos.Remitos import Remito
from vistas.ReImprimeRemito import ReImprimeRemitoView


class ReImprimeRemitoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ReImprimeRemitoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaRemitosCliente)
        self.view.btnImprimir.clicked.connect(self.Imprimir)
        self.view.btnCargar.clicked.connect(self.CargaRemitosCliente)

    @inicializar_y_capturar_excepciones
    def Imprimir(self, *args, **kwargs):
        row = self.view.gridDatos.currentRow()
        if row >= 0:
            remito = Remito.get(Remito.idremito == self.view.gridDatos.ObtenerItem(fila=row, col='idcabecera'))
            controlador_factura = RemitoController()
            controlador_factura.Imprimir(remito)

    @inicializar_y_capturar_excepciones
    def CargaRemitosCliente(self, *args, **kwargs):
        """Lista los remitos del periodo, de un cliente o de todos.

        Antes la consulta era solo `Remito.cliente == <lo escrito>`, y el
        campo abre vacio: eso es `cliente = ''`, que no trae ni un remito.
        Tampoco filtraba por fecha, asi que escribir un cliente sacaba los
        remitos de cualquier fecha.
        """
        condiciones = [Remito.fecha >= self.view.controles['fecha'].date().toPyDate()]
        cliente = self.view.controles['cliente'].text().strip()
        if cliente:
            condiciones.append(Remito.cliente == cliente)
        remitos = Remito.select(Remito, Cliente).join(Cliente)\
            .where(*condiciones).order_by(Remito.fecha.desc())
        self.view.gridDatos.setRowCount(0)
        for r in remitos:
            self.view.gridDatos.AgregaItem(
                items=[r.fecha, r.cliente.nombre, r.numero, r.total, r.idremito])