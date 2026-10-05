# coding=utf-8
"""Pantalla de importacion de articulos desde el Excel del proveedor.

Que se pregunta y por que
-------------------------
La pantalla es una lista de preguntas y un boton. Lo que se pregunta es
exactamente lo que el archivo NO puede decir:

* **De que proveedor es la lista.** El archivo trae PROVEEDOR en texto libre
  ("NORDESTE"), pero la base lo guarda como id, y resolver por nombre un
  proveedor que todavia no esta cargado no es seguro: se puede crear un
  "NORDESTE" duplicado con el "Nordeste" que ya estaba. Se elige de los que ya
  estan cargados.
* **El margen.** El archivo trae GANANCIA por renglon y se usa. Pero un
  renglon sin ganancia necesita un valor de respaldo, y ese valor es una
  decision comercial, no algo que se pueda deducir de una planilla.
* **El IVA.** La columna IVA del archivo trae 0 en todas las filas, y eso no
  es "exento": es "no lo se". Ver libs/importararticulos.py.
* **Unidad, concepto y control de stock.** Defaults razonables que el
  operador puede cambiar, y que se cambian para toda la carga.

Lo que NO se pregunta
---------------------
El grupo. Sale de la columna GRUPO del archivo y se crea si no existe.
Preguntar de que grupo va cada producto duplicaria un dato que ya esta en la
planilla, y el operador tiene cientos de filas para responder.

Nada se importa sin confirmacion
--------------------------------
Antes de escribir se muestra cuantas filas tiene el archivo, porque una lista
de precios que pisa costos a ciegas es el peor resultado posible de una
pantalla asi. Y despues se muestra que se creo, que se actualizo y que filas
quedaron afuera, con el numero de fila del Excel.
"""

from PyQt5.QtWidgets import (QApplication, QFormLayout, QHBoxLayout, QLabel,
                             QVBoxLayout, QWidget)

from libs import Ventanas
from libs import importararticulos
from libs.BarraProgreso import Avance
from libs.Botones import Boton
from libs.Checkbox import CheckBox
from libs.ComboBox import ComboConceptoFacturacion
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.GroupBox import Agrupacion
from libs.Spinner import Spinner
from libs.Utiles import (icono, inicializar_y_capturar_excepciones,
                         openFileNameDialog)
from modelos.Grupos import ComboGrupo
from modelos.Proveedores import ComboProveedor
from modelos.Tipoiva import ComboIVA, Tipoiva
from modelos.Unidades import ComboUnidad
from vistas.VistaBase import VistaBase


class ImportarArticulosView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.revisarCatalogos()

    # -- Armado --------------------------------------------------------------

    def setupUi(self, Form):
        self.setWindowTitle("Importar artículos desde Excel")
        layout = QVBoxLayout(Form)

        lblIntro = QLabel(
            "Trae nombre, costo, grupo y ganancia de cada producto.\n"
            "El precio al público sale de costo × ganancia.")
        lblIntro.setWordWrap(True)
        layout.addWidget(lblIntro)

        # -- Planilla
        cajaArchivo = Agrupacion(titulo="Planilla")
        layArchivo = QHBoxLayout()
        self.txtArchivo = EntradaTexto(placeholderText="Archivo .xlsx del proveedor")
        self.txtArchivo.setReadOnly(True)
        self.btnBuscar = Boton(texto="Buscar...", imagen=icono('buscar'))
        layArchivo.addWidget(self.txtArchivo)
        layArchivo.addWidget(self.btnBuscar)
        cajaArchivo.setLayout(layArchivo)
        layout.addWidget(cajaArchivo)

        # -- Datos de la carga
        cajaDatos = Agrupacion(titulo="Datos de la carga")
        layDatos = QFormLayout()

        self.cboProveedor = ComboProveedor()
        layDatos.addRow("Proveedor", self.cboProveedor)

        # El rotulo dice "ganancia por defecto" y no "margen" a proposito: el
        # archivo trae una GANANCIA por renglon y se usa esa. Este campo es el
        # plan B para los renglones que llegan sin ella, y llamarlo "margen"
        # al lado de una columna que dice GANANCIA hace pensar que compiten.
        self.spnGanancia = Spinner(decimales=4)
        self.spnGanancia.setToolTip(
            "Se usa solo en los renglones que vienen sin ganancia. Si la "
            "planilla trae la suya, manda la de la planilla.")
        layDatos.addRow("Ganancia por defecto", self.spnGanancia)

        self.cboTipoIva = ComboIVA()
        layDatos.addRow("IVA", self.cboTipoIva)

        self.cboUnidad = ComboUnidad()
        layDatos.addRow("Unidad", self.cboUnidad)

        self.cboGrupo = ComboGrupo()
        self.cboGrupo.setToolTip(
            "Solo si la planilla NO trae la columna GRUPO. Si la trae, cada "
            "artículo va al grupo que dice su fila, y los grupos que falten "
            "se crean.")
        layDatos.addRow("Grupo por defecto", self.cboGrupo)

        self.cboConcepto = ComboConceptoFacturacion()
        layDatos.addRow("Concepto de facturación", self.cboConcepto)

        # El control de stock y el mínimo van juntos en una fila: uno sin el
        # otro no avisa de nada (ver vistas/Articulos.py).
        layStock = QHBoxLayout()
        self.chkControla = CheckBox(texto="Controla stock?")
        self.chkControla.setChecked(True)
        self.spnMinimo = Spinner(decimales=2)
        layStock.addWidget(self.chkControla)
        layStock.addWidget(Etiqueta(texto="Stock mínimo"))
        layStock.addWidget(self.spnMinimo)
        layStock.addStretch()
        cajaStock = QWidget()
        cajaStock.setLayout(layStock)
        layDatos.addRow("Stock", cajaStock)

        cajaDatos.setLayout(layDatos)
        layout.addWidget(cajaDatos)

        self.lblResumen = QLabel("")
        self.lblResumen.setWordWrap(True)
        layout.addWidget(self.lblResumen)

        self.avance = Avance()
        self.avance.setVisible(False)
        layout.addWidget(self.avance)

        layBotones = QHBoxLayout()
        self.btnImportar = Boton(texto="Importar", imagen=icono('importar'),
                                 estilo='primario')
        self.btnCerrar = Boton(texto="Cerrar", imagen=icono('cerrar'))
        layBotones.addStretch()
        layBotones.addWidget(self.btnImportar)
        layBotones.addWidget(self.btnCerrar)
        layout.addLayout(layBotones)

        self.declara_tamano(660, 560)

    def _poner_el_iva_general_por_defecto(self):
        """Deja el IVA general (01) elegido, no el primero de la lista.

        `ComboIVA` ordena por descripcion, y "10.5" ordena antes que "IVA
        GENERAL", asi que el primer elemento de la lista es el 10.5%. Si esta
        pantalla quedara con ese, TODO articulo importado entraria con el
        impuesto bajo y nadie se enteraria hasta ver la factura: el dato
        estaria mal en todos lados y pareceria correcto.

        Si la base no tiene el 01 se deja lo que haya: algunos catalogos
        viejos no lo tienen y elegir el primero es mejor que no elegir nada.
        """
        indice = self.cboTipoIva.findData("01")
        if indice >= 0:
            self.cboTipoIva.setCurrentIndex(indice)

    # -- Estado inicial ------------------------------------------------------

    def revisarCatalogos(self):
        """Deja el boton listo o explica por que no.

        Un desplegable vacio no es un dato. Si no hay proveedores cargados,
        `currentData()` devuelve None, que es un id de proveedor invalido, y
        el error aparece recien cuando se escribieron articulos. Mejor al
        abrir: que se vea que hay que cargar el proveedor primero.
        """
        self._poner_el_iva_general_por_defecto()

        falta = []

        if not self.cboProveedor.count():
            falta.append("No hay proveedores cargados.\n\n"
                         "Cada artículo necesita saber de quién es. Cargá al "
                         "menos uno en Proveedores antes de importar.")
        if Tipoiva.select().count() == 0:
            falta.append("No hay tipos de IVA cargados.")

        if falta:
            self.btnImportar.setEnabled(False)
            self.lblResumen.setText("\n\n".join(falta))
            self.lblResumen.setStyleSheet("color: #C62F35;")
            return

        self.btnImportar.setEnabled(False)
        self.mostrarResumenPreliminar()

    # -- Conexiones ----------------------------------------------------------

    def ConectarWidgets(self):
        self.btnBuscar.clicked.connect(self.buscarArchivo)
        self.btnImportar.clicked.connect(self.importar)
        self.btnCerrar.clicked.connect(self.cerrarformulario)
        self.txtArchivo.textChanged.connect(self.mostrarResumenPreliminar)

    # -- Acciones ------------------------------------------------------------

    @inicializar_y_capturar_excepciones
    def buscarArchivo(self, *args, **kwargs):
        archivo = openFileNameDialog(
            self, files="Archivos de Excel (*.xlsx *.xlsm)",
            title="Abrir planilla del proveedor")
        if not archivo:
            return
        self.txtArchivo.setText(archivo)

    @inicializar_y_capturar_excepciones
    def mostrarResumenPreliminar(self, *args, **kwargs):
        """Cuenta las filas del archivo antes de importar nada.

        Es el unico momento en que se descubre que el archivo no es una lista
        de precios. Sin esto, el error sale despues de haber creado cien
        articulos, y el operador ya no sabe si puede seguir.
        """
        archivo = self.txtArchivo.text().strip()
        if not archivo:
            self.lblResumen.setText("")
            self.btnImportar.setEnabled(False)
            return

        try:
            registros = importararticulos.leer_filas(archivo)
        except importararticulos.ErrorImportacion as error:
            self.lblResumen.setText(str(error))
            self.lblResumen.setStyleSheet("color: #C62F35;")
            self.btnImportar.setEnabled(False)
            return

        ilegibles = [r for r in registros if r.get("error")]
        texto = "La planilla tiene {} filas de datos.".format(len(registros))
        if ilegibles:
            texto += " {} tienen un dato ilegible y no se van a importar.".format(
                len(ilegibles))
        self.lblResumen.setText(texto)
        self.lblResumen.setStyleSheet("")
        self.btnImportar.setEnabled(self.cboProveedor.count() > 0)

    @inicializar_y_capturar_excepciones
    def importar(self, *args, **kwargs):
        archivo = self.txtArchivo.text().strip()
        if not archivo:
            Ventanas.showAlert("Importación", "Elegí primero la planilla.")
            return

        proveedor = self.cboProveedor.text()
        if not proveedor:
            Ventanas.showAlert(
                "Importación", "Elegí de qué proveedor es la lista.")
            return

        # Sin ganancia por defecto no es un error: la planilla puede traer la
        # suya en todos los renglones, y el campo es solo el plan B. Si
        # faltara y algun renglon no la trae, lo dice el resumen de esa fila.
        ganancia = self.spnGanancia.valor()
        ganancia = ganancia if ganancia > 0 else None

        if not Ventanas.showConfirmation(
                "Importar artículos",
                "Se van a crear y actualizar artículos del catálogo.\n\n"
                "Las filas que ya existen se actualizan con el costo, el "
                "precio y el proveedor de la planilla.\n\n¿Seguís?",
                textoOk="Importar"):
            return

        self.avance.setVisible(True)
        self.avance.setRange(0, 0)      # indeterminado mientras lee
        QApplication.processEvents()

        try:
            resultado = importararticulos.importa(
                archivo,
                proveedor_id=int(proveedor),
                tipoiva=str(self.cboTipoIva.text()),
                unidad=str(self.cboUnidad.text()),
                ganancia_defecto=ganancia,
                concepto=str(self.cboConcepto.text()),
                controlastock=self.chkControla.isChecked(),
                stockminimo=self.spnMinimo.value(),
            )
        except importararticulos.ErrorImportacion as error:
            self.avance.setVisible(False)
            Ventanas.showAlert("Importación", str(error))
            return
        finally:
            # Sin esto, una lista de 2000 artículos deja la pantalla en blanco
            # con el reloj de arena clavado y el operador la mata.
            QApplication.processEvents()

        self.avance.setVisible(False)
        self.mostrarResultado(resultado)

    def mostrarResultado(self, resultado):
        """El aviso de cómo terminó, con el detalle de lo que quedó afuera.

        El detalle va entero. "3 filas no se importaron" sin decir cuáles
        deja al operador abriendo el Excel a buscar; con el número de fila y
        el motivo, abre el archivo y tiene el dato.
        """
        mensaje = resultado.resumen()

        if resultado.filas_con_error:
            detalle = "\n".join(
                "  fila {}: {}".format(numero, motivo)
                for numero, motivo in resultado.filas_con_error[:15])
            if len(resultado.filas_con_error) > 15:
                detalle += "\n  ... y {} más".format(
                    len(resultado.filas_con_error) - 15)
            mensaje += "\n\nFilas que no entraron:\n" + detalle

        Ventanas.showAlert("Importación", mensaje)
        self.mostrarResumenPreliminar()