# coding=utf-8
from libs.Checkbox import CheckBox
from libs.ComboBox import ComboConceptoFacturacion
from libs.Etiquetas import Etiqueta
from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from libs.ganancia import margen_activo, precio_desde_incre1
from modelos import Unidades, Grupos, Proveedores, Tipoiva
from modelos.Articulos import Articulo
from modelos.Tipoiva import ComboIVA
from vistas.ABM import ABM


class ArticulosView(ABM):

    model = Articulo()
    camposAMostrar = [Articulo.idarticulo, Articulo.nombre, Articulo.preciopub]
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
        self.layoutUnidad = self.ArmaEntrada(nombre='unidad', control=Unidades.ComboUnidad())
        self.ArmaEntrada('grupo', boxlayout=self.layoutUnidad, control=Grupos.ComboGrupo())
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
        self.ArmaEntrada('modificaprecios', boxlayout=self.layoutProvedor, control=CheckBox(), texto="Modifica precios?")
        self.layoutCosto = self.ArmaEntrada('costo', texto='Costo', control=Spinner())
        # El porcentaje va entre el costo y el precio porque es el puente entre
        # los dos: es lo que convierte el primero en el segundo. Con ganancia
        # cargada el precio se calcula solo y el campo queda en solo lectura;
        # en cero el precio se tipea a mano, como siempre. Ver libs/ganancia.py.
        self.ArmaEntrada('incre1', boxlayout=self.layoutCosto,
                                     control=Spinner(decimales=2),
                                     texto="Ganancia %")
        # ArmaEntrada devuelve el LAYOUT, no el widget: el tooltip se le pone al
        # control ya guardado en self.controles. Con el valor de retorno tiraba
        # 'QHBoxLayout has no attribute setToolTip' y, como ArmaCarga esta
        # dentro de inicializar_y_capturar_excepciones, el formulario se
        # armaba a medias: sin precio, sin concepto y sin los controles de
        # stock.
        self.controles['incre1'].setToolTip(
            "Porcentaje de ganancia sobre el costo: 40 significa 40%.\n"
            "Con ganancia cargada el precio al publico se calcula solo y el "
            "campo de precio queda en solo lectura.\n"
            "En 0 el precio se carga a mano.")
        self.ArmaEntrada('preciopub', boxlayout=self.layoutCosto, control=Spinner(), texto="Precio al publico")
        self.ArmaEntrada('concepto', boxlayout=self.layoutCosto, control=ComboConceptoFacturacion())
        # El control de stock va en la misma linea que el precio y no en una
        # pantalla aparte: es una propiedad del producto, como el precio, y
        # si estuviera escondida el operador la busca una vez y despues
        # nunca mas. El minimo va al lado y no mas lejos porque siempre van
        # juntos: un control sin minimo no avisa de nada.
        self.ArmaEntrada('controlastock', boxlayout=self.layoutCosto, control=CheckBox(),
                         texto="Controla stock?")
        self.ArmaEntrada('stockminimo', boxlayout=self.layoutCosto, control=Spinner(),
                         texto="Stock minimo")

        # Los dos que mandan sobre el precio. El precio NO se conecta: es
        # destino, no origen, y escucharlo haria que cambiar el costo se pise
        # a si mismo.
        self.controles['costo'].valueChanged.connect(self.RecalculaPrecio)
        self.controles['incre1'].valueChanged.connect(self.RecalculaPrecio)

    def RecalculaPrecio(self, *args, **kwargs):
        """El precio sale del costo mientras haya ganancia cargada.

        Con 0 el precio queda a mano, que es el estado en el que estan todos los
        articulos que ya existian. Con ganancia, el precio se pone en solo
        lectura: si se pudiera editar, el precio y el costo dejarian de
        caminar juntos sin que nadie lo note, que es justo lo que un porcentaje
        de ganancia promete.
        """
        incre1 = self.controles['incre1'].valor()
        spn_precio = self.controles['preciopub']
        if not margen_activo(incre1):
            spn_precio.setEnabled(True)
            return

        spn_precio.setEnabled(False)
        precio = precio_desde_incre1(self.controles['costo'].valor(), incre1)
        if precio is not None:
            spn_precio.setValue(float(precio))

    @inicializar_y_capturar_excepciones
    def PostModifica(self):
        # Al abrir un articulo el precio tiene que quedar consistente con su
        # margen. Si no, el operador ve un precio guardado que no sale de la
        # cuenta que tiene escrita al lado, en solo lectura.
        self.RecalculaPrecio()

    @inicializar_y_capturar_excepciones
    def PostAgrega(self):
        # Agrega vacia los controles pero no toca setEnabled, asi que el precio
        # queda en solo lectura si el articulo que se estaba editando tenia
        # ganancia, y con valor 0. El operador no podria cargarlo. Con incre1
        # en cero, RecalculaPrecio lo vuelve a habilitar.
        self.RecalculaPrecio()

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        # for x in self.controles:
        #     print("Control {} Valor {} tipo {}".format(x, self.controles[x].text(), type(self.controles[x].text())))
        if self.tipo == 'M':
            articulo = Articulo.get_by_id(self.controles[Articulo.idarticulo.column_name].text())
            articulo.idarticulo = int(self.controles['idarticulo'].text())
        else:
            articulo = Articulo()
        articulo.nombre = self.controles['nombre'].text()[:100]
        articulo.nombreticket = self.controles['nombreticket'].text()[:30]
        articulo.unidad = self.controles['unidad'].text() or 'UN'
        articulo.grupo = self.controles['grupo'].text() or 1
        articulo.costo = self.controles['costo'].value()
        articulo.provppal = int(str(self.controles['provppal'].text()) or 0)
        articulo.tipoiva = str(self.controles['tipoiva'].text()).zfill(2)
        articulo.modificaprecios = self.controles['modificaprecios'].text()
        # El precio se recalcula al guardar y no se confia en lo que quedo
        # escrito en el control. El recalculo en vivo es para que el operador
        # vea la cuenta; esto es para que lo que se persiste SEA la cuenta, y
        # no dependa de que un valueChanged haya llegado a dispararse.
        incre1 = self.controles['incre1'].valor()
        articulo.incre1 = incre1
        if margen_activo(incre1):
            precio = precio_desde_incre1(self.controles['costo'].valor(), incre1)
            articulo.preciopub = precio if precio is not None else 0
        else:
            articulo.preciopub = self.controles['preciopub'].value()
        articulo.concepto = self.controles['concepto'].text()
        articulo.codbarra = self.controles['codbarra'].text()
        # Se guardan siempre, no solo en el alta: si se omitieran, editar un
        # producto para cambiarle el nombre pondria controlastock en False y
        # el producto dejaria de descontar stock sin que nadie lo tocara.
        articulo.controlastock = self.controles['controlastock'].text()
        articulo.stockminimo = self.controles['stockminimo'].value()
        articulo.save()
        ABM.btnAceptarClicked(self)
