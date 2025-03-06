# coding=utf-8
from turtle import title
from controladores.ControladorBase import ControladorBase
from controladores.Emailcliente import EmailClienteController
from libs import Ventanas
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Clientes import Cliente, FichaCliente
from vistas.Clientes import ClientesView, FichaClienteView, ListaFichaClienteView


class ClientesController(ControladorBase):

    def __init__(self):
        super(ClientesController, self).__init__()
        self.view = ClientesView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnEmail.clicked.connect(self.CargaEmailCliente)
        self.view.controles['dni'].editingFinished.connect(self.onDNIEditingFinished)
        self.view.btn_ficha.clicked.connect(self.CargaFichaCliente)

    def CargaEmailCliente(self):
        controllerEmail = EmailClienteController()
        controllerEmail.idcliente = self.view.tableView.ObtenerItem(
            fila=self.view.tableView.currentRow(), col=0
        )
        controllerEmail.CargaEmail()
        controllerEmail.exec_()

    def onDNIEditingFinished(self):
        if not self.view.controles['dni'].text():
            self.view.controles['dni'].setText('0')
        if not self.view.controles['tipodocu'].text():
            self.view.controles['tipodocu'].setText('0')
            
    def CargaFichaCliente(self):
        row = self.view.tableView.currentRow()
        if row == -1:
            Ventanas.showAlert('Sistema', 'Debe seleccionar un cliente')
            return
        
        id = self.view.tableView.ObtenerItem(fila=row, col=0)
        controlador = ListaFichaClientesController()
        controlador.id_cliente = id
        controlador.CargaDatos()
        controlador.exec_()
    
class ListaFichaClientesController(ControladorBase):
    
    id_cliente = 0
    def __init__(self):
        super().__init__()
        self.view = ListaFichaClienteView()
        self.conectarWidgets()
    
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_agregar.clicked.connect(self.AgregarFicha)
        self.view.btn_editar.clicked.connect(self.EditarFicha)
        self.view.btn_borrar.clicked.connect(self.BorrarFicha)
        self.view.btn_impresion.clicked.connect(self.Imprimir)
        
    def CargaDatos(self):
        self.view.grid_datos.setRowCount(0)
        saldo_inicial = FichaCliente.calcular_saldo(self.id_cliente, self.view.layout_fechas.desde_fecha.toPyDate())
        if saldo_inicial > 0:
            self.view.grid_datos.AgregaItem(
                [self.view.layout_fechas.desde_fecha.toPyDate(), 'Saldo Inicial', 0, 0, saldo_inicial, 0]
            )
            
        fichas = FichaCliente.select().where(
            FichaCliente.cliente == self.id_cliente,
            FichaCliente.fecha.between(
                lo=self.view.layout_fechas.desde_fecha.toPyDate(),
                hi=self.view.layout_fechas.hasta_fecha.toPyDate()
            )
        ).order_by(FichaCliente.fecha)
        
        saldo = 0
        for ficha in fichas:
            saldo += ficha.debe - ficha.haber
            self.view.grid_datos.AgregaItem(
                [ficha.fecha, ficha.detalle, ficha.debe, ficha.haber, saldo, ficha.id]
            )
    
    @inicializar_y_capturar_excepciones
    def AgregarFicha(self, *args, **kwargs):
        controlador = FichaClienteController()
        controlador.id_ficha = 0
        controlador.view.txtCliente.setText(str(self.id_cliente))
        controlador.exec_()
        self.CargaDatos()
        
    @inicializar_y_capturar_excepciones
    def EditarFicha(self, *args, **kwargs):
        row = self.view.grid_datos.currentRow()
        if row == -1:
            Ventanas.showAlert('Sistema', 'Debe seleccionar una ficha')
            return
        id = self.view.grid_datos.ObtenerItem(fila=row, col='id')
        controlador = FichaClienteController()
        controlador.id_ficha = id
        controlador.CargaDatos()
        controlador.exec_()
        self.CargaDatos()
    
    @inicializar_y_capturar_excepciones
    def BorrarFicha(self, *args, **kwargs):
        row = self.view.grid_datos.currentRow()
        if row == -1:
            Ventanas.showAlert('Sistema', 'Debe seleccionar una ficha')
            return
        id = self.view.grid_datos.ObtenerItem(fila=row, col='id')
        ficha = FichaCliente.get_by_id(id)
        ficha.delete_instance()
        self.CargaDatos()
    
    @inicializar_y_capturar_excepciones
    def Imprimir(self, *args, **kwargs):
        cliente = Cliente.get_by_id(self.id_cliente)
        self.view.grid_datos.ExportaExcel(
            titulo=f'Ficha de cliente {cliente.nombre}', 
            archivo='ficha_cliente'
        )

class FichaClienteController(ControladorBase):
    
    id_ficha = 0
    
    def __init__(self):
        super().__init__()
        self.view = FichaClienteView()
        self.conectarWidgets()
    
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_guardar.clicked.connect(self.Guardar)
        
    def Guardar(self):
        if self.id_ficha:
            ficha = FichaCliente.get_by_id(self.id_ficha)
        else:
            ficha = FichaCliente()
            ficha.cliente = self.view.txtCliente.text()
        ficha.fecha = self.view.fecha.toPyDate()
        ficha.detalle = self.view.txtDetalle.valor()
        ficha.debe = self.view.txtDebe.valor()
        ficha.haber = self.view.txtHaber.valor()
        ficha.save()
        self.view.Cerrar()
        
    def CargaDatos(self):
        ficha = FichaCliente.get_by_id(self.id_ficha)
        self.view.txtCliente.setText(str(ficha.cliente))
        self.view.fecha.setDate(ficha.fecha)
        self.view.txtDetalle.setText(ficha.detalle)
        self.view.txtDebe.setText(ficha.debe)
        self.view.txtHaber.setText(ficha.haber)