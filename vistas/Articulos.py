# coding=utf-8
from libs.Checkbox import CheckBox
from libs.ComboBox import ComboConceptoFacturacion
from libs.Etiquetas import Etiqueta
from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos import Unidades, Grupos, Proveedores, Tipoiva
from modelos.Articulos import Articulo
from modelos.Tipoiva import ComboIVA
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
        self.ArmaEntrada('codbarra', texto='Codigo de barra', boxlayout=self.layoutNombreTicket)
        self.layoutUnidad = self.ArmaEntrada(nombre='unidad', control=Unidades.Valida())
        self.ArmaEntrada('grupo', boxlayout=self.layoutUnidad, control=Grupos.Valida())
        self.lblNombreGrupo = Etiqueta()
        self.layoutUnidad.addWidget(self.lblNombreGrupo)
        self.controles['grupo'].widgetNombre = self.lblNombreGrupo
        self.layoutProvedor = self.ArmaEntrada('provppal', texto='Proveedor principal', control=Proveedores.Valida())
        self.lblNombreProveedor = Etiqueta()
        self.layoutProvedor.addWidget(self.lblNombreProveedor)
        self.controles['provppal'].widgetNombre = self.lblNombreProveedor
        self.ArmaEntrada('tipoiva', boxlayout=self.layoutProvedor, control=ComboIVA())
        self.lblNombreTipoiva = Etiqueta()
        self.layoutProvedor.addWidget(self.lblNombreTipoiva)
        self.controles['tipoiva'].widgetNombre = self.lblNombreTipoiva
        self.ArmaEntrada('modificaprecios', boxlayout=self.layoutProvedor, control=CheckBox())
        self.layoutCosto = self.ArmaEntrada('costo', texto='Costo', control=Spinner())
        self.ArmaEntrada('preciopub', boxlayout=self.layoutCosto, control=Spinner())
        self.ArmaEntrada('concepto', boxlayout=self.layoutCosto, control=ComboConceptoFacturacion())

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        # for x in self.controles:
        #     print("Control {} Valor {} tipo {}".format(x, self.controles[x].text(), type(self.controles[x].text())))
        if self.tipo == 'M':
            articulo = Articulo.get_by_id(self.controles[Articulo.idarticulo.column_name].text())
            articulo.idarticulo = int(self.controles['idarticulo'].text())
        else:
            articulo = Articulo()
        articulo.nombre = str(self.controles['nombre'].text())
        articulo.nombreticket = str(self.controles['nombreticket'].text())
        articulo.unidad = str(self.controles['unidad'].text())
        articulo.grupo = str(self.controles['grupo'].text())
        articulo.costo = str(self.controles['costo'].text())
        articulo.provppal = int(str(self.controles['provppal'].text()))
        articulo.tipoiva = str(self.controles['tipoiva'].text()).zfill(2)
        articulo.modificaprecios = self.controles['modificaprecios'].text()
        articulo.preciopub = str(self.controles['preciopub'].text())
        articulo.concepto = self.controles['concepto'].text()
        articulo.codbarra = self.controles['codbarra'].text()
        articulo.save()
        ABM.btnAceptarClicked(self)
