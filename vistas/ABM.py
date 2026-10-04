# coding=utf-8
import decimal

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QWidget, QGridLayout, QHBoxLayout, QLineEdit, QCheckBox, QComboBox

from libs import Ventanas
from libs.Botones import Boton
from libs.busqueda import contiene
from libs.Checkbox import CheckBox
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.Grillas import Grilla
from libs.Spinner import Spinner
from libs.Utiles import EsVerdadero, inicializar_y_capturar_excepciones, imagen, icono
from vistas.VistaBase import VistaBase


class ABM(VistaBase):

    #diccionario que guarda los controles que se agreguen al abm
    controles = {}

    #modelo sobre el que se hace el abm
    model = None

    #indica si es un alta o una modificacion
    tipo = "A"

    #campos a mostrar en la grilla
    camposAMostrar = None

    #condicion para filtrar la tabla
    condicion = None

    #limite de registros
    limite = 100

    #orden de busqueda
    ordenBusqueda = None

    #campo
    campoClave = None

    #campo clave autoincremental
    autoincremental = True

    #campo para el foco
    campoFoco = None

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.controles = {}
        self.initUi()

    @inicializar_y_capturar_excepciones
    def initUi(self, *args, **kwargs):
        self.resize(906, 584)
        nombre_tabla = self.model._meta.table_name.title() if self.model else ''
        # El titulo va solo en la barra de la ventana. Antes se repetia tambien
        # como etiqueta adentro, y con dos lineas que dicen lo mismo arriba de
        # la pantalla queda como un tital sin proposito. El prefijo "ABM de"
        # tambien sobra: la pantalla se abre desde la barra lateral, donde ya
        # se sabe que es un alta-baja-modificacion.
        self.setWindowTitle(nombre_tabla)
        self.verticalLayout = QVBoxLayout(self)

        self.tabWidget = QTabWidget()
        self.tabLista = QWidget()
        self.gridLayout = QGridLayout(self.tabLista)

        # "Buscar" y no "Buscar por nombre": hay ABMs que filtran por otra cosa
        # (los parametros del sistema, por parametro; los impuestos, por
        # detalle), y un cartel que miente sobre lo que busca es peor que uno
        # que no precisa.
        self.lineEditBusqueda = EntradaTexto(self.tabLista, placeholderText="Buscar")
        self.lineEditBusqueda.setObjectName("lineEditBusqueda")
        self.gridLayout.addWidget(self.lineEditBusqueda, 0, 0, 1, 1)

        self.tableView = Grilla(self.tabLista)
        self.tableView.setObjectName("tableView")
        self.tableView.enabled = True

        # extraigo los nombres de las columnas
        if self.camposAMostrar:
            self.tableView.cabeceras = [x.verbose_name.capitalize() if x.verbose_name else x.column_name.capitalize()
                                        for x in self.camposAMostrar]
        else:
            self.tableView.cabeceras = []
        # Y sus tipos, que salen del campo del modelo y no de adivinar con la
        # primera fila: ver _formatos_de_campos.
        self.tableView.ArmaCabeceras(formatos=self._formatos_de_campos())
        self.gridLayout.addWidget(self.tableView, 1, 0, 1, 1)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.BotonesAdicionales()

        # Jerarquia de la barra: "Nuevo" es la accion que se usa casi siempre,
        # "Borrar" es la que no se quiere tocar por error y "Cerrar" es salir
        # sin hacer nada. Con los cuatro con el mismo peso, nada indicaba cual
        # era cual. Como esta clase es la base de todos los ABM (grupos,
        # impuestos, localidades, tipos de documento...), el cambio se ve en
        # todas esas pantallas de una.
        self.btnAgregar = Boton(self.tabLista, texto='Nuevo', imagen=icono('nuevo'), tamanio=QSize(32,32),
                                tooltip='Agrega nuevo registro', estilo='primario')
        self.btnAgregar.setObjectName("btnAgregar")
        self.horizontalLayout.addWidget(self.btnAgregar)

        self.btnEditar = Boton(self.tabLista, imagen=icono('editar'), tamanio=QSize(32,32),
                               tooltip='Modifica registro', texto='Editar')
        self.btnEditar.setObjectName("btnEditar")
        self.horizontalLayout.addWidget(self.btnEditar)

        self.btnBorrar = Boton(self.tabLista, imagen=icono('borrar'), tamanio=QSize(32,32),
                               tooltip='Borrar registro', texto='Borrar', estilo='peligro')
        self.btnBorrar.setObjectName("btnBorrar")
        self.horizontalLayout.addWidget(self.btnBorrar)

        self.btnCerrar = Boton(self.tabLista, imagen=icono('cerrar'), tamanio=QSize(32,32),
                               tooltip='Cerrar ABM', texto='Cerrar')

        self.btnCerrar.setObjectName("btnCerrar")
        self.horizontalLayout.addWidget(self.btnCerrar)
        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.tabWidget.addTab(self.tabLista, "Lista")
        self.tabDetalle = QWidget()
        self.tabWidget.addTab(self.tabDetalle, "Detalle")
        self.tabDetalle.setEnabled(False)

        self.verticalLayout.addWidget(self.tabWidget)

        self.ArmaDatos()
        self.ArmaTabla()
        self.ConectaWidgets()

    def BotonesAdicionales(self):
        pass

    # Que tipo de columna le corresponde a cada campo de peewee. La grilla
    # formatea y alinea segun esto.
    TIPOS_DE_CAMPO = {
        'AutoField': 'Entero',
        'BigAutoField': 'Entero',
        'IntegerField': 'Entero',
        'SmallIntegerField': 'Entero',
        'BigIntegerField': 'Entero',
        'ForeignKeyField': 'Entero',
        'DecimalField': 'Moneda',
        'FloatField': 'Decimal',
        'BooleanField': 'Bool',
        'DateField': 'Date',
        'DateTimeField': 'Date',
        'CharField': 'String',
        'FixedCharField': 'String',
        'TextField': 'String',
    }

    def _formatos_de_campos(self):
        """El tipo de cada columna, deducido del campo del modelo.

        Sin esto la grilla no sabe que "Idcliente" es un codigo: se lo deduce
        con la primera fila, y hasta entonces elige que columna se estira por
        la longitud del encabezado, que es justo como el id se quedaba con
        732 de 959 px. Y el id, ya deducido como numero, se mostraba como
        "1,00" con dos decimales que no significan nada.

        Un tipo que no se reconoce no se declara (queda vacio): mejor que la
        grilla lo descubra sola con la primera fila, como antes, a que
        declararlo mal y formatear un importe como un codigo.
        """
        if not self.camposAMostrar:
            return []
        return [self.TIPOS_DE_CAMPO.get(type(campo).__name__, '')
                for campo in self.camposAMostrar]

    def ArmaTabla(self):
        self.tableView.setRowCount(0)
        if not self.model: #si no esta establecido el modelo no hago nada
            return

        data = self.model.select().dicts()
        if self.condicion:
            for c in self.condicion:
                data = data.where(c)

        if self.lineEditBusqueda.text():
            if self.ordenBusqueda:
                data = data.where(contiene(self.ordenBusqueda, self.lineEditBusqueda.text()))
            else:
                Ventanas.showAlert("Sistema", "Orden no establecido y no se puede realizar la busqueda")

        data = data.limit(self.limite)
        for d in data:
            if self.camposAMostrar:
                item = [d[x.column_name] for x in self.camposAMostrar]
            else:
                item = [d[x] for x in d]
            self.tableView.AgregaItem(item)

    def ArmaDatos(self):
        self.verticalLayoutDatos = QVBoxLayout(self.tabDetalle)
        self.verticalLayoutDatos.setObjectName("verticalLayoutDatos")
        self.ArmaCarga()
        fila = 0

        self.grdBotones = QGridLayout()
        self.grdBotones.setObjectName("grdBotones")
        self.btnAceptar = Boton(self.tabDetalle, texto='Guardar', imagen=icono('guardar'), tamanio=QSize(32, 32),
                                tooltip="Guardar cambios", estilo='primario')
        self.btnAceptar.setObjectName("btnAceptar")
        self.grdBotones.addWidget(self.btnAceptar, 0, 0, 1, 1)

        self.btnCancelar = Boton(self.tabDetalle, texto='Cerrar', imagen=icono('cerrar'), tamanio=QSize(32, 32),
                                 tooltip="Cerrar sin guardar")
        self.btnCancelar.setObjectName("btnCancelar")
        self.grdBotones.addWidget(self.btnCancelar, 0, 1, 1, 1)
        self.verticalLayoutDatos.addLayout(self.grdBotones)
        self.verticalLayout.addWidget(self.tabWidget)
        self.btnCancelar.clicked.connect(self.btnCancelarClicked)
        self.btnAceptar.clicked.connect(self.btnAceptarClicked)
        self.verticalLayoutDatos.addStretch(1)

    def Busqueda(self):
        self.ArmaTabla()

    def ConectaWidgets(self):
        self.lineEditBusqueda.textChanged.connect(self.Busqueda)
        self.btnCerrar.clicked.connect(self.cerrarformulario)
        self.btnBorrar.clicked.connect(self.Borrar)
        self.btnEditar.clicked.connect(self.Modifica)
        self.btnAgregar.clicked.connect(self.Agrega)

    @inicializar_y_capturar_excepciones
    def Borrar(self, *args, **kwargs):
        if not self.tableView.currentRow() != -1:
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No tenes establecido el campo clave y no podemos continuar")

        id = self.tableView.ObtenerItem(fila=self.tableView.currentRow(), col=self.campoClave.column_name.capitalize())
        data = self.model.get_by_id(id)
        data.delete_instance()
        self.ArmaTabla()

    def Modifica(self):

        self.tipo = 'M'
        if not self.tableView.currentRow() != -1:
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No tenes establecido el campo clave y no podemos continuar")

        id = self.tableView.ObtenerItem(fila=self.tableView.currentRow(), col=self.campoClave.column_name.capitalize())
        data = self.model.select().where(self.campoClave == id).dicts()
        self.tabDetalle.setEnabled(True)
        self.tabWidget.setCurrentIndex(1)
        self.CargaDatos(data)
        if self.campoFoco:
            self.campoFoco.setFocus()
        self.PostModifica()

    def CargaDatos(self, data=None):
        # self.tipo = 'A'
        if not data:
            return
        for d in data:
            for k in d:
                if k in self.controles:
                    if k == self.campoClave.column_name:
                        self.controles[k].setEnabled(False)
                    if isinstance(self.controles[k], QLineEdit):
                        if isinstance(d[k], (int, decimal.Decimal)):
                            self.controles[k].setText(str(d[k]))
                        else:
                            self.controles[k].setText(d[k])
                    elif isinstance(self.controles[k], Spinner):
                        self.controles[k].setText(d[k])
                    elif isinstance(self.controles[k], (QCheckBox, CheckBox)):
                        if EsVerdadero(d[k]) or d[k]:
                            self.controles[k].setChecked(True)
                        else:
                            self.controles[k].setChecked(False)
                    elif isinstance(self.controles[k], QComboBox):
                        if isinstance(d[k], (bytes,)):
                            if EsVerdadero(self.cursor[k]):
                                self.controles[k].setCurrentIndex(self.controles[k].findData('Si'))
                            else:
                                self.controles[k].setCurrentIndex(self.controles[k].findData('No'))
                        else:
                            self.controles[k].setCurrentIndex(self.controles[k].findData(d[k]))
                    # El dato ya se cargo, asi que el estado de validacion del
                    # campo deja de aplicar. Antes se "limpiaba" poniendo el
                    # fondo blanco a mano, lo que ademas pisaba cualquier
                    # estilo del tema sobre ese control.
                    from libs.tema import limpiar_estado
                    limpiar_estado(self.controles[k])

    def ArmaEntrada(self, nombre="", boxlayout=None, texto='', *args, **kwargs):
        if not nombre:
            return
        if not boxlayout:
            boxlayout = QHBoxLayout()
            lAgrega = True
        else:
            lAgrega = False

        if not texto:
            if isinstance(nombre, str):
                texto = nombre.capitalize()
            else:
                texto = nombre.verbose_name if nombre.verbose_name else nombre.name.capitalize()

        if not isinstance(nombre, str): #si no es un campo texto intento convertir de un campo de pewee
            nombre = nombre.name

        labelNombre = Etiqueta(texto=texto)
        labelNombre.setObjectName("labelNombre")
        boxlayout.addWidget(labelNombre)

        if 'control' in kwargs:
            lineEditNombre = kwargs['control']
        else:
            lineEditNombre = EntradaTexto()

        if 'relleno' in kwargs:
            lineEditNombre.relleno = kwargs['relleno']

        if 'inputmask' in kwargs:
            lineEditNombre.setInputMask(kwargs['inputmask'])

        #print(type(lineEditNombre))
        lineEditNombre.setObjectName(nombre)
        boxlayout.addWidget(lineEditNombre)
        if 'enabled' in kwargs:
            lineEditNombre.setEnabled(kwargs['enabled'])

        self.controles[nombre] = lineEditNombre

        if lAgrega:
            self.verticalLayoutDatos.addLayout(boxlayout)
        return boxlayout

    def btnCancelarClicked(self):
        self.tabWidget.setCurrentIndex(0)
        self.tabDetalle.setEnabled(False)

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        # data = self.model.get_by_id(self.controles[self.campoClave.column_name].text())
        # data.nombre = self.controles['nombre'].text()
        self.ArmaTabla()
        self.btnCancelarClicked()

    def ArmaCarga(self):
        pass

    def Agrega(self):
        self.tipo = 'A'
        for x in self.controles:
            if self.autoincremental:
                if x == self.campoClave.column_name:
                    self.controles[x].setEnabled(False)
            self.controles[x].setText('')
            # Campo vacio para un alta nueva: se saca el estado de validacion
            # del registro anterior. Ver la nota en Carga().
            from libs.tema import limpiar_estado
            limpiar_estado(self.controles[x])
        self.tabDetalle.setEnabled(True)
        self.tabWidget.setCurrentIndex(1)
        if self.campoFoco:
            self.campoFoco.setFocus()
        self.PostAgrega()

    def PostModifica(self):
        pass

    def PostAgrega(self):
        pass