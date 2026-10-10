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
  es "exento": es "no lo se". Ver libs/importararticulos.py. Si la planilla
  trae una alicuota de verdad (21, 10.5) esa manda renglon por renglon, y lo
  que se pregunta aca es solo el respaldo para los 0 y para las columnas
  ausentes.
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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QFormLayout, QHBoxLayout, QLabel,
                             QTableWidget, QVBoxLayout, QWidget)

from libs import Ventanas
from libs import importararticulos
from libs.BarraProgreso import Avance
from libs.Botones import Boton
from libs.Checkbox import CheckBox
from libs.ComboBox import ComboConceptoFacturacion
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.Grillas import Grilla, _formato_importe
from libs.GroupBox import Agrupacion
from libs.Spinner import Spinner
from libs.Utiles import (icono, inicializar_y_capturar_excepciones,
                         openFileNameDialog)
from modelos.Grupos import ComboGrupo
from modelos.Proveedores import ComboProveedor
from modelos.Tipoiva import ComboIVA, Tipoiva
from modelos.Unidades import ComboUnidad
from vistas.VistaBase import VistaBase

# El fondo de error del tema (pyfe.css), el mismo que usa la grilla de venta
# para marcar un renglón que no tiene stock. Poner otro color aca haria que
# esta pantalla se viera distinta del resto de la app, que es justo lo que
# se vino a arreglar.
COLOR_ERROR_FILA = {'background': '#FDF3F2', 'color': '#C62F35'}


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
        #
        # El campo es un PORCENTAJE (30 = 30%), igual que el "Ganancia %" del
        # ABM de artículos, y no el multiplicador 1.5 de la planilla. Son dos
        # escalas distintas para lo mismo, y tener el mismo numero en los dos
        # lugares de la pantalla es lo que evita que el operador cargar 30
        # esperando 30% y termine escribiendo un factor.
        self.spnGanancia = Spinner(decimales=2)
        self.spnGanancia.setToolTip(
            "Porcentaje para los renglones que vienen sin ganancia: 30 es "
            "30%.\n\nSe usa solo en los que no traen ganancia. Si la planilla "
            "trae la suya, manda la de la planilla.")
        layDatos.addRow("Ganancia por defecto (%)", self.spnGanancia)

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

        # La vista previa. Sin esto, el operador se entera de que el precio
        # quedo mal DESPUES de que se escribieron 69 articulos, y el unico
        # dato que tiene es "se importaron 69". Los dos errores que se
        # encontraron con esto (una columna GANANCIA que en realidad traia
        # porcentajes, y una planilla de varios proveedores atribuidos todos
        # al del desplegable) son invisibles en un resumen y evidentes en una
        # grilla con el precio al lado del costo.
        cajaPrevia = Agrupacion(titulo="Vista previa")
        self.grillaPrevia = Grilla()
        # `enabled` y las cabeceras pasadas POR PARAMETRO a ArmaCabeceras, y
        # no como atributo de instancia: es como lo hacen las grillas que
        # andan (vistas/Stock.py y las de compra).
        #
        # Puestas como atributo, la pantalla se caia con un access violation de
        # Qt al hacer resize (3221225477): sin backtrace, sin exception y sin
        # decir que era esto. `ArmaCabeceras` sin argumento lee la lista de
        # CLASE, que es compartida entre todas las Grillas del proceso, y una
        # grilla que no sabe cuantas columnas tiene se rompe al maquetar.
        self.grillaPrevia.enabled = True
        self.grillaPrevia.ArmaCabeceras(cabeceras=[
            "Fila", "Código", "Nombre", "Proveedor",
            "Costo", "Ganancia %", "Precio", "Estado"])
        self.grillaPrevia.setEditTriggers(QTableWidget.NoEditTriggers)
        self.grillaPrevia.setSelectionBehavior(QTableWidget.SelectRows)
        cajaPrevia.setLayout(QVBoxLayout())
        cajaPrevia.layout().addWidget(self.grillaPrevia)
        layout.addWidget(cajaPrevia, 1)

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

        # Mas alta que antes: la grilla de la vista previa necesita el lugar
        # que antes ocupaba el aire entre el resumen y los botones. Sin esto
        # se ven ocho filas de las 69 y la pantalla sigue pareciendo la misma.
        self.declara_tamano(900, 720)

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

        # La vista previa depende de estos, asi que cambiar cualquiera tiene
        # que repintarla. Sin esto, el operador cambia el proveedor o la
        # ganancia y la grilla sigue mostrando los precios de antes: la
        # pantalla le esta mintiendo justo en el dato que la hace util.
        self.cboProveedor.currentIndexChanged.connect(self.mostrarResumenPreliminar)
        self.spnGanancia.valueChanged.connect(self.mostrarResumenPreliminar)
        self.cboTipoIva.currentIndexChanged.connect(self.mostrarResumenPreliminar)

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
        """Cuenta las filas y las muestra con su precio, antes de importar.

        Es el unico momento en que se descubre que el archivo no es una lista
        de precios. Sin esto, el error sale despues de haber creado cien
        articulos, y el operador ya no sabe si puede seguir.
        """
        archivo = self.txtArchivo.text().strip()
        if not archivo:
            self.lblResumen.setText("")
            self.grillaPrevia.setRowCount(0)
            self.btnImportar.setEnabled(False)
            return

        # `currentData()`, NO `text()`. El ComboProveedor muestra el NOMBRE y
        # guarda el id en el dato, asi que `text()` devuelve el id ("2") y se
        # puede leer por accidente pensando que es el nombre. Con `text()`
        # el chequeo de "no hay proveedor" comparaba contra un texto vacio y
        # la vista previa nunca se armaba sola: habia que tocar otro campo
        # para que apareciera.
        proveedor = self.cboProveedor.currentData()
        if proveedor is None:
            self.grillaPrevia.setRowCount(0)
            self.btnImportar.setEnabled(False)
            return

        ganancia = self.spnGanancia.valor()
        ganancia = ganancia if ganancia > 0 else None

        try:
            previa = importararticulos.previsualiza(
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
            self.lblResumen.setText(str(error))
            self.lblResumen.setStyleSheet("color: #C62F35;")
            self.grillaPrevia.setRowCount(0)
            self.btnImportar.setEnabled(False)
            return

        self.pintar_previa(previa)
        self.lblResumen.setText(self._texto_del_resumen(previa))
        self.lblResumen.setStyleSheet("")
        self.btnImportar.setEnabled(self.cboProveedor.count() > 0)

    def _texto_del_resumen(self, previa):
        """Lo que va arriba de la grilla: cuentas y avisos.

        Los avisos van PRIMERO y en rojo cuando importan. Es lo que el
        operador lee antes de apretar Importar, asi que si tiene que avisar
        que dos filas del archivo se pisan entre si, va aca y no en el
        resumen de despues, que llega tarde para corregir.
        """
        partes = []

        # La escala de la ganancia se lee sola, y es mejor que el operador lo
        # vea: con la planilla de BOTZ (GANANCIA=30) el precio salia 20 veces
        # mas caro y el resumen decia "69 articulos importados" como si
        # estuviera todo bien.
        if previa.escala_ganancia == "porcentaje":
            partes.append(
                "La columna GANANCIA trae PORCENTAJES: se leyó como 30% y no "
                "como multiplicador.")
        elif previa.escala_ganancia == "mixta":
            partes.append(
                "ATENCION: la columna GANANCIA mezcla porcentajes y "
                "multiplicadores. Revisá la columna antes de importar.")

        if previa.proveedores_no_encontrados:
            partes.append(
                "ATENCION: el archivo trae el proveedor {}, que NO está "
                "cargado. Sus artículos entraron con el proveedor de arriba. "
                "Cargalo en Proveedores y volvé a elegir la planilla si "
                "querés que salga bien.".format(
                    ", ".join(previa.proveedores_no_encontrados)))

        if len(previa.proveedores_usados) > 1:
            partes.append("El archivo trae {} proveedores: cada artículo va "
                          "con el de su fila.".format(
                              len(previa.proveedores_usados)))

        if previa.nombres_repetidos:
            detalle = "; ".join(
                "{} (filas {})".format(nombre,
                                       ", ".join(str(n) for n in filas))
                for nombre, filas in previa.detalle_repetidos[:5])
            partes.append(
                "ATENCION: {} nombre(s) se repiten y no hay código de barras "
                "para distinguirlos, así que el último costo pisa al "
                "anterior: {}.".format(len(previa.nombres_repetidos), detalle))

        legible = "{} filas en la planilla".format(previa.total_filas)
        if previa.total_previsualizado:
            legible += ", {} se van a importar".format(previa.total_previsualizado)
        if previa.filas_con_error:
            legible += ", {} no entran".format(len(previa.filas_con_error))
        partes.append(legible + ".")

        return "  ".join(partes)

    def pintar_previa(self, previa):
        """Llena la grilla con lo que `previsualiza` calculo.

        La fila que no entra se pinta en el color de error del tema, que es la
        misma forma que tiene la app de decir "esto esta mal". Es lo que hace
        que un costo en rojo salte a la vista bajando por la lista.
        """
        self.grillaPrevia.setRowCount(0)
        # Sin `ArmaCabeceras()` aca: las cabeceras se armaron UNA vez, en
        # `setupUi`. Volver a armarlas en cada repintado las reinicia con la
        # lista de clase compartida, que es lo que crashaba la pantalla.

        for fila in previa.filas:
            # Sin `insertRow`: `AgregaItem` hace el `setRowCount` él mismo
            # (ver libs/Grillas.py). Con el insertRow de mas, cada fila de
            # datos quedaba con una fila VACIA encima y la grilla mostraba
            # 138 filas para 69 articulos, con renglones en blanco entre uno y
            # otro.
            if fila.estado == "error":
                valores = [str(fila.numero), fila.codbarra, fila.nombre,
                           fila.proveedor, "", "", "", fila.motivo or "error"]
                color = {"backgroundColor": COLOR_ERROR_FILA}
            else:
                estado = {"nuevo": "nuevo", "actualiza": "actualiza",
                          "igual": "sin cambios"}[fila.estado]
                valores = [
                    str(fila.numero),
                    fila.codbarra,
                    fila.nombre,
                    fila.proveedor,
                    _formato_importe(fila.costo),
                    "{}%".format(_formato_importe(fila.margen, 2)),
                    _formato_importe(fila.precio),
                    estado,
                ]
                color = None

            self.grillaPrevia.AgregaItem(valores, backgroundColor=color)

    @inicializar_y_capturar_excepciones
    def importar(self, *args, **kwargs):
        archivo = self.txtArchivo.text().strip()
        if not archivo:
            Ventanas.showAlert("Importación", "Elegí primero la planilla.")
            return

        # `currentData()` y no `text()`: ver `mostrarResumenPreliminar`. El
        # texto del combo es el NOMBRE del proveedor y el id va en el dato;
        # `text()` devuelve el id, que funciona con `int()` pero no sirve
        # para el chequeo de "no hay proveedor elegido".
        proveedor = self.cboProveedor.currentData()
        if proveedor is None:
            Ventanas.showAlert(
                "Importación", "Elegí de qué proveedor es la lista.")
            return

        # Sin ganancia por defecto no es un error: la planilla puede traer la
        # suya en todos los renglones, y el campo es solo el plan B. Si
        # faltara y algun renglon no la trae, lo dice el resumen de esa fila.
        #
        # Va como PORCENTAJE tal cual lo escribio el operador: la conversion a
        # multiplicador, si hay que hacerla, es del modulo, no de la pantalla.
        # Acá se toco justamente para que 30 sea 30% y no 30 veces el costo.
        ganancia = self.spnGanancia.valor()
        ganancia = ganancia if ganancia > 0 else None

        # Lo que se vio en la vista previa. Se reusa en el aviso de
        # confirmacion para que el boton diga las mismas cuentas que la grilla
        # de arriba y no una frase generica que contradiga lo que se ve.
        previa_filas = self.grillaPrevia.rowCount()
        previa_proveedores = []
        for r in range(previa_filas):
            item = self.grillaPrevia.item(r, 3)
            nombre = item.text() if item else ""
            if nombre and nombre not in previa_proveedores:
                previa_proveedores.append(nombre)

        # El aviso va con el numero de filas y los proveedores, y no con un
        # "se van a crear articulos" generico: el operador ya vio el detalle
        # en la grilla de arriba y aca confirma que lo que va a escribir es
        # lo que vio.
        aviso = "Se van a crear y actualizar artículos del catálogo.\n\n"
        if previa_filas:
            aviso += "Filas a procesar: {}.\n\n".format(previa_filas)
        if previa_proveedores:
            aviso += "Proveedores del archivo: {}.\n\n".format(
                ", ".join(previa_proveedores))
        aviso += ("Las filas que ya existen se actualizan con el costo, el "
                  "precio y el proveedor de la planilla.\n\n¿Seguís?")

        if not Ventanas.showConfirmation("Importar artículos", aviso,
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