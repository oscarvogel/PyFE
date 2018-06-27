# coding=utf-8
from libs.Checkbox import CheckBox
from libs.Etiquetas import Etiqueta
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos import Unidades, Grupos, Proveedores, Tipoiva
from modelos.Articulos import Articulo
from vistas.ABM import ABM


class ArticulosView(ABM):

    model = Articulo()
    camposAMostrar = [Articulo.idarticulo, Articulo.nombre]
    ordenBusqueda = Articulo.nombre
    campoClave = Articulo.idarticulo

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('idarticulo', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)
        self.layoutNombreTicket = self.ArmaEntrada('nombreticket', texto='Nombre Ticket')
        self.layoutUnidad = self.ArmaEntrada(nombre='unidad', control=Unidades.Valida())
        self.ArmaEntrada('grupo', boxlayout=self.layoutUnidad, control=Grupos.Valida())
        self.lblNombreGrupo = Etiqueta()
        self.layoutUnidad.addWidget(self.lblNombreGrupo)
        self.controles['grupo'].widgetNombre = self.lblNombreGrupo
        self.layoutProvedor = self.ArmaEntrada('provppal', texto='Proveedor principal', control=Proveedores.Valida())
        self.lblNombreProveedor = Etiqueta()
        self.layoutProvedor.addWidget(self.lblNombreProveedor)
        self.controles['provppal'].widgetNombre = self.lblNombreProveedor
        self.ArmaEntrada('tipoiva', boxlayout=self.layoutProvedor, control=Tipoiva.Valida())
        self.lblNombreTipoiva = Etiqueta()
        self.layoutProvedor.addWidget(self.lblNombreTipoiva)
        self.controles['tipoiva'].widgetNombre = self.lblNombreTipoiva
        self.ArmaEntrada('modificaprecios', boxlayout=self.layoutProvedor, control=CheckBox())
        self.layoutCosto = self.ArmaEntrada('costo', texto='Costo')
        self.ArmaEntrada('preciopub', boxlayout=self.layoutCosto)

    def btnAceptarClicked(self):
        if self.tipo == 'M':
            articulo = Articulo.get_by_id(self.controles[Articulo.idarticulo.column_name].text())
            articulo.idarticulo = self.controles['idarticulo'].text()
        else:
            articulo = Articulo()
        articulo.nombre = self.controles['nombre'].text()
        articulo.nombreticket = self.controles['nombreticket'].text()
        articulo.unidad = self.controles['unidad'].text()
        articulo.grupo = self.controles['grupo'].text()
        articulo.costo = self.controles['costo'].text()
        articulo.provppal = self.controles['provppal'].text()
        articulo.tipoiva = self.controles['tipoiva'].text()
        articulo.modificaprecios = self.controles['modificaprecios'].text()
        articulo.preciopub = self.controles['preciopub'].text()
        articulo.save()
        ABM.btnAceptarClicked(self)
