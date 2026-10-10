# coding=utf-8
import contextlib
from decimal import Decimal, InvalidOperation

from peewee import Case, fn
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialog, QShortcut

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, aplicar_forma_pago, calcular_totales
from libs import Ventanas
from libs import stock
from libs.Grillas import _a_numero_texto, _formato_importe
from libs.busqueda import contiene as buscar_texto
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones, a_entero
from modelos.Articulos import Articulo
from modelos.Clientes import Cliente
from vistas.VentaSimple import VentaSimpleAltaArticuloDialog, VentaSimpleAltaClienteDialog, \
    VentaSimpleCantidadPrecioDialog, VentaSimpleSeleccionArticuloDialog, \
    VentaSimpleSeleccionClienteDialog, VentaSimpleView


# Cuantos clientes se traen a la lista. Es un tope, no un filtro: por abajo el
# total, asi que el dialogo puede decir cuantos hay en total y el operador
# sigue acotando. 100 es lo que entra comodo en la pantalla sin scroll.
LIMITE_BUSQUEDA_CLIENTES = 100

# Igual que el de clientes: es un tope, no un filtro, por abajo esta el
# total asi que el dialogo puede decir cuantos hay en total.
LIMITE_BUSQUEDA_ARTICULOS = 100

# Lo que va en la columna Stock cuando el articulo no controla stock. Un
# guion y no un 0: el cero dice "hay cero", y para un servicio la
# verdad es que no hay nada que contar. Ponerlo en 0 haria que el operador
# busque mercaderia que no existe.
SIN_STOCK = '-'

# Los colores del renglon que no alcanza. Los dos salen de temas/pyfe.css:
# el rojo de peligro (#C62F35) y el fondo de error (#FDF3F2), que ya son la
# forma que tiene la app de decir "esto esta mal". Poner otros aca hacia
# que la venta rapiga se vea distinta de todo el resto.
COLOR_FALTANTE_FONDO = '#FDF3F2'
COLOR_FALTANTE_TEXTO = '#C62F35'


class VentaSimpleController(ControladorBase):
    _atajos_creados = []

    def __init__(self):
        super(VentaSimpleController, self).__init__()
        self.cliente = None
        # Ver cargar_cliente_desde_busqueda().
        self._resolviendo_cliente = False
        self.view = VentaSimpleView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self._cerrar)
        self.view.btnAgregar.clicked.connect(self.agregar_articulo)
        self.view.btnEmitir.clicked.connect(self.emitir_factura)
        self.view.btnBorrar.clicked.connect(self.borrar_renglon)
        self.view.textArticulo.returnPressed.connect(self.agregar_articulo)
        self.view.textCantidad.returnPressed.connect(self.agregar_articulo)
        # Solo editingFinished, y no las dos senales: QLineEdit emite
        # returnPressed Y editingFinished cuando se presiona Enter, asi que
        # con las dos conectadas la busqueda corria dos veces y el selector de
        # cliente se abria dos veces (se elige en el primero y aparece el
        # segundo encima). editingFinished alcanza para los dos casos que
        # importan: Enter y salir del campo con el mouse.
        self.view.textCliente.editingFinished.connect(self.cargar_cliente_desde_busqueda)
        # Enter con el campo vacio abre el buscador, igual que el campo de
        # producto abre el catalogo. Va por returnPressed y NO por
        # editingFinished: al salir del campo con el mouse/tabulador con el
        # campo vacio no hay que abrir nada, solo molesta.
        self.view.textCliente.returnPressed.connect(self.buscar_cliente_con_enter)
        self.view.checkConsumidorFinal.stateChanged.connect(self.on_consumidor_final_changed)
        try:
            self.view.cboFormaPago.currentIndexChanged.connect(
                self._on_forma_pago_changed)
            self.view.cboCuotas.currentIndexChanged.connect(
                lambda *args: self.recalcular_total())
            self._cargar_cuotas()
        except Exception:
            pass
        # Editar una celda de la grilla recalcula el renglon. Antes no habia
        # ninguna conexion: la cantidad se podia cambiar a mano y el SubTotal,
        # el total y el color del stock se quedaban con los de antes.
        #
        # `cellChanged`, y NO `itemChanged`. Las dos existen en QTableWidget y
        # no son la misma: `itemChanged` entrega el QTableWidgetItem y
        # `cellChanged` entrega (fila, columna). Con la primera, el handler
        # recibe un item donde espera un int, y como la excepcion sube desde
        # un slot que Qt llama desde C++, el proceso muere con 0xC0000409 y sin
        # backtrace: un crash que no dice nada del TypeError que lo causa.
        #
        # Tampoco `currentItemChanged`, que es lo que usa la grilla de compras:
        # esa avisa de la seleccion, y editar una celda sin mover el cursor no
        # la cambia.
        #
        # Con esto hay que evitar la reentrada: pintar la columna Stock escribe
        # en la grilla, y eso dispara otra vez la misma senal. De ahi el
        # candado de `_escribiendo`.
        self._pintando = False
        self.view.gridVenta.cellChanged.connect(self.on_celda_editada)
        self.atajos()

    # Atajos del flujo frecuente. Cargar una venta es escribir, buscar y
    # agregar, una linea por producto: si hay que ir al mouse entre renglones,
    # el atajo es lo que hace que la pantalla sea rapida. El tooltip de cada
    # boton los muestra, asi que no hay que acordarse.
    # (secuencia, metodo, boton donde se anuncia, texto del tooltip)
    ATAJOS = [
        ("Ctrl+Return", "agregar_articulo", "btnAgregar",
         "Agregar el producto (Ctrl+Return)"),
        ("Ctrl+E", "emitir_factura", "btnEmitir",
         "Emitir la factura (Ctrl+E)"),
        ("Ctrl+B", "borrar_renglon", "btnBorrar",
         "Borrar el renglón (Ctrl+B)"),
        ("Delete", "borrar_renglon", "btnBorrar", None),
        ("F2", "_ir_al_producto", "textArticulo",
         "Ir al producto (F2)"),
        ("Esc", "_cerrar", "btnCerrar", "Cerrar sin guardar (Esc)"),
    ]

    def atajos(self):
        self._atajos_creados = []
        for secuencia, metodo, atributo, texto in self.ATAJOS:
            atajo = QShortcut(QKeySequence(secuencia), self.view)
            atajo.setContext(Qt.WindowShortcut)
            atajo.activated.connect(getattr(self, metodo))
            # Sin referencia propia el atajo se garbage-collectea y deja de
            # funcionar sin que se vea ningun error.
            self._atajos_creados.append(atajo)
            if texto:
                getattr(self.view, atributo).setToolTip(texto)

    def _ir_al_producto(self):
        self.view.textArticulo.setFocus()
        self.view.textArticulo.selectAll()

    def _cerrar(self):
        """Cerrar pidiendo confirmacion si hay una venta a medio cargar.

        No hace falta que Cerrar() pregunte siempre: si la venta esta vacia no
        hay nada que perder. Pero con renglones cargados, cerrar sin avisar tira
        el trabajo de tipeo a la basura sin dejar rastro.
        """
        if self.view.gridVenta.rowCount() and not Ventanas.showConfirmation(
                "Descartar la venta",
                "La venta tiene productos cargados y todavia no se emitio.\n\n"
                "Si cierra ahora se pierde.",
                textoOk="Descartar", textoCancelar="Seguir cargando"):
            return
        self.view.Cerrar()

    def on_consumidor_final_changed(self):
        if self.view.checkConsumidorFinal.isChecked():
            self.cliente = None
            self.view.textCliente.setText("")
            self.view.textDocumento.setText("")

    def buscar_cliente_con_enter(self):
        """Enter abre el buscador si el campo esta vacio y no es CF.

        Con texto, no hace nada: el editingFinished que Qt emite justo
        despues del returnPressed resuelve lo escrito (exacto, selector o
        alta). Con consumidor final tampoco: no hay cliente que buscar.

        El candado es el mismo de cargar_cliente_desde_busqueda: al abrirse
        el dialogo modal, Qt le saca el foco al campo y eso emite
        editingFinished con este metodo todavia en la pila. Ver ahi.
        """
        if self.view.checkConsumidorFinal.isChecked():
            return
        if self.view.textCliente.text().strip():
            return
        if self._resolviendo_cliente:
            return

        self._resolviendo_cliente = True
        try:
            cliente = self.seleccionar_cliente("")
            if cliente is not None:
                self.cargar_cliente_en_vista(cliente)
        finally:
            self._resolviendo_cliente = False

    def cargar_cliente_desde_busqueda(self):
        """Busca el cliente escrito y lo carga en la venta.

        El candado de `_resolviendo_cliente` esta porque esta funcion se puede
        volver a entrar en si misma mientras ya esta corriendo. Al abrirse el
        dialogo modal de seleccion, Qt le quita el foco al campo de cliente, y
        eso emite editingFinished con este mismo handler todavia en la pila
        adentro de dialogo.exec_(). La segunda entradaTodavia ve el texto sin
        cambiar, encuentra las mismas coincidencias, y abre un segundo dialogo
        encima del primero: el operador elige en el de adelante, este se
        cierra, y aparece el de atras, que parece que no acepta la
        seleccion.

        El candado va ACA y no adentro de seleccionar_cliente por una razon
        concreta: si solo estuviera en el ultimo, la entrada anidada recibiria
        None como resultado y seguiria de largo, abriendo el "¿desea agregar
        el cliente?" por encima del dialogo que ya esta en pantalla.

        Va con try/finally porque en una app de escritorio un candado que se
        traba por una excepcion deja la pantalla de venta inservible hasta
        reiniciar.
        """
        if self._resolviendo_cliente:
            return

        busqueda = self.view.textCliente.text().strip()
        if not busqueda or self.view.checkConsumidorFinal.isChecked() and busqueda == "Consumidor Final":
            return

        self._resolviendo_cliente = True
        try:
            cliente = self.resolver_cliente_desde_busqueda(busqueda)
            if not cliente:
                if not self.confirmar_alta("Venta", "Cliente no encontrado. Desea agregarlo?"):
                    return
                cliente = self.solicitar_alta_cliente(busqueda)
                if not cliente:
                    return

            self.cargar_cliente_en_vista(cliente)
        finally:
            self._resolviendo_cliente = False

    def confirmar_alta(self, titulo, mensaje, textoOk="Crear cliente"):
        """Pregunta si se crea lo que no se encontro, y el boton lo nombra.

        El texto del boton lo pasa quien pregunta, y no un valor fijo: esta
        misma funcion se usa para el cliente y para el producto, y con un
        texto fijo el boton decia "Crear cliente" encima de un mensaje que
        decia "Producto no encontrado". Un boton que contradice el mensaje
        hace dudar de toda la pantalla.

        El boton por defecto sigue siendo cancelar, como antes.
        """
        return Ventanas.showConfirmation(
            titulo, mensaje, textoOk=textoOk, textoCancelar="Cancelar")

    def cargar_cliente_en_vista(self, cliente):
        self.cliente = cliente
        self.view.checkConsumidorFinal.setChecked(False)
        self.view.textCliente.setText("{} - {}".format(cliente.idcliente, cliente.nombre))
        documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
        self.view.textDocumento.setText(documento)

    def solicitar_alta_cliente(self, busqueda):
        dialogo = VentaSimpleAltaClienteDialog(busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        datos = dialogo.valores()
        nombre = datos["nombre"]
        if not nombre:
            Ventanas.showAlert("Venta", "Ingrese el nombre del cliente")
            return None

        documento = datos["documento"].replace("-", "").replace(" ", "")
        cuit = ""
        dni = 0
        if documento:
            if len(documento) == 11:
                cuit = datos["documento"]
            elif documento.isdigit():
                dni = int(documento)

        return Cliente.create(
            nombre=nombre,
            domicilio=datos["domicilio"],
            localidad=1,
            cuit=cuit,
            dni=dni,
            tipodocu=0,
            tiporesp=3,
            formapago=1,
            percepcion=1,
        )

    def resolver_cliente_desde_busqueda(self, busqueda):
        clientes = self.buscar_clientes(busqueda)
        if not clientes:
            return None
        if len(clientes) == 1:
            return clientes[0]
        return self.seleccionar_cliente(busqueda)

    def seleccionar_cliente(self, busqueda):
        # El dialogo recibe como buscar, no una lista ya armada: si se le
        # pasaran las coincidencias, no habria forma de acotar sin cerrar y
        # volver a escribir, que es justo lo que duele cuando la lista son
        # 800 clientes.
        #
        # Este dialogo no se puede abrir anidado: al abrirse le quita el foco
        # al campo de cliente, y eso vuelve a entrar en
        # cargar_cliente_desde_busqueda() mientras este metodo sigue en la
        # pila. El candado que lo evita esta ahi, no aca. Ver ahi.
        dialogo = VentaSimpleSeleccionClienteDialog(self._coincidencias_clientes,
                                                    busqueda=busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None
        return dialogo.cliente

    def _cliente_exacto(self, texto):
        """Si el texto identifica a un solo cliente, lo devuelve.

        Codigo, CUIT (con o sin guiones) y DNI se buscan con igualdad exacta:
        son indices, y ademas no tienen sentido "con contiene", porque
        "3067" matchearia cualquier CUIT que arranque con 3067.
        """
        posible_id = texto.split(" - ", 1)[0]
        if posible_id.isdigit():
            try:
                return Cliente.get_by_id(posible_id)
            except Exception:
                pass

        cuit = texto.replace("-", "").replace(" ", "")
        try:
            cliente = Cliente.select().where(Cliente.cuit == texto).first()
            if cliente:
                return cliente
            cliente = Cliente.select().where(fn.REPLACE(Cliente.cuit, "-", "") == cuit).first()
            if cliente:
                return cliente
        except Exception:
            pass

        if texto.isdigit():
            try:
                return Cliente.select().where(Cliente.dni == int(texto)).first()
            except Exception:
                pass
        return None

    def _coincidencias_clientes(self, busqueda, limite=None):
        """(coincidencias, total) para el buscador del dialogo.

        Devuelve el total ademas de la lista porque con miles de clientes la
        lista viene recortada: sin el total, ver 100 filas y no saber si hay
        100 o 5.000 deja al operador creyendo que ya los vio todos.
        """
        texto = str(busqueda or "").strip()
        exacto = self._cliente_exacto(texto)
        if exacto:
            return [exacto], 1
        if not texto:
            return [], 0

        consulta = Cliente.select().where(buscar_texto(Cliente.nombre, texto))
        total = consulta.count()
        if limite is None:
            limite = LIMITE_BUSQUEDA_CLIENTES
        return list(consulta.order_by(Cliente.nombre).limit(limite)), total

    def buscar_clientes(self, busqueda, limite=None):
        texto = str(busqueda).strip()
        if not texto:
            return []
        return self._coincidencias_clientes(texto, limite=limite)[0]

    @inicializar_y_capturar_excepciones
    def agregar_articulo(self, *args, **kwargs):
        """Agrega un renglon, segun lo que haya escrito en el campo.

        Campo vacio: se abre el catalogo. Con el cliente, Enter abre un
        selector; con el producto decia "Ingrese un producto", que deja al
        operador sin salida si no se acuerda el nombre exacto. El selector
        deja seguir escribiendo para acotar, que es lo que hace falta con un
        catalogo de verdad.

        Campo con texto: se busca. Si lo escrito coincide con mas de un
        articulo NO se elige el primero: se abre el catalogo ya acotado para
        que el operador elija. Antes `buscar_articulo` hacia `.first()` y con
        dos productos parecidos (dos "WHEY CUTTER ...", que difieren en el
        sabor) se agregaba el que salia primero en la base, sin preguntar.

        Si no aparece ninguno, se ofrece darlo de alta. Ese camino no se toca,
        porque es el que permite cargar algo nuevo sin salir de la pantalla.
        """
        busqueda = self.view.textArticulo.text().strip()
        if not busqueda:
            articulo = self.seleccionar_articulo("")
            if not articulo:
                return
            return self._agregar_este_articulo(articulo)

        if self._articulo_es_ambiguo(busqueda):
            articulo = self.seleccionar_articulo(busqueda)
            if not articulo:
                return
            return self._agregar_este_articulo(articulo)

        articulo = self.buscar_articulo(busqueda)
        if not articulo:
            if not self.confirmar_alta(
                    "Venta", "Producto no encontrado. Desea agregarlo?",
                    textoOk="Crear producto"):
                return
            articulo = self.solicitar_alta_articulo(busqueda)
            if not articulo:
                return

        return self._agregar_este_articulo(articulo)

    def _articulo_es_ambiguo(self, busqueda):
        """True si lo escrito puede ser mas de un articulo.

        Se pregunta antes de agregar, y solo con dos o mas coincidencias: con
        una sola no hay nada que decidir y el camino rápido de antes sirve.
        """
        try:
            _, total = self._coincidencias_articulo(busqueda, limite=2)
        except Exception:
            # Si no se puede contar, se sigue como antes: agregar el producto
            # es menos grave que dejar al operador sin poder cargar la venta.
            return False
        return total > 1

    def _agregar_este_articulo(self, articulo):
        """Pide cantidad y precio y agrega la linea.

        Aca convergen los dos caminos: el que viene del selector del catalogo
        y el que viene de haber escrito el nombre. La linea se arma igual, y
        con la misma validacion de cantidad.
        """
        try:
            cantidad = Decimal(self.view.textCantidad.text() or "1")
        except Exception:
            Ventanas.showAlert("Venta", "La cantidad debe ser numerica")
            return

        if cantidad <= 0:
            Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
            return

        datos_renglon = self.solicitar_cantidad_y_precio(articulo, cantidad)
        if not datos_renglon:
            return

        cantidad, precio = datos_renglon
        iva = Decimal(str(articulo.tipoiva.iva))
        subtotal = cantidad * precio

        with self._escribiendo():
            self.view.gridVenta.AgregaItem(items=[
                str(cantidad),
                str(articulo.idarticulo),
                articulo.nombre,
                SIN_STOCK,  # lo calcula _pinta_el_stock
                str(precio),
                str(iva),
                str(subtotal),
            ])
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
        self._pinta_el_stock()
        self.recalcular_total()
        # El foco vuelve al producto: cargar una venta es agregar linea por
        # linea, y volver al mouse entre renglones es lo que hace lenta la
        # pantalla.
        self.view.textArticulo.setFocus()

    def solicitar_cantidad_y_precio(self, articulo, cantidad):
        dialogo = VentaSimpleCantidadPrecioDialog(
            articulo=articulo,
            cantidad=cantidad,
            precio=Decimal(str(articulo.preciopub)),
        )
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        cantidad_texto, precio_texto = dialogo.valores()
        try:
            cantidad = Decimal(cantidad_texto or "1")
            precio = Decimal(precio_texto or "0")
        except Exception:
            Ventanas.showAlert("Venta", "Cantidad y precio deben ser numericos")
            return None

        if cantidad <= 0:
            Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
            return None
        if precio < 0:
            Ventanas.showAlert("Venta", "El precio no puede ser negativo")
            return None

        return cantidad, precio

    def solicitar_alta_articulo(self, busqueda):
        dialogo = VentaSimpleAltaArticuloDialog(busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        datos = dialogo.valores()
        nombre = datos["nombre"]
        if not nombre:
            Ventanas.showAlert("Venta", "Ingrese el nombre del articulo")
            return None

        try:
            precio = Decimal(datos["precio"] or "0")
            iva = Decimal(datos["iva"] or "21")
        except Exception:
            Ventanas.showAlert("Venta", "Precio e IVA deben ser numericos")
            return None

        if precio < 0:
            Ventanas.showAlert("Venta", "El precio no puede ser negativo")
            return None

        tipoiva = "01" if iva == Decimal("21") else "01"
        return Articulo.create(
            nombre=nombre,
            nombreticket=nombre[:30],
            preciopub=precio,
            costo=precio,
            tipoiva=tipoiva,
            codbarra=datos["codbarra"],
        )

    def _articulo_exacto(self, texto):
        """Si el texto identifica a un solo articulo, lo devuelve.

        Codigo, codigo de barras y nombre exacto se buscan con igualdad: son
        indices, y con "contiene" el codigo 1 encontraria el 10, el 11 y el
        100.
        """
        try:
            return Articulo.get_by_id(texto)
        except Exception:
            pass

        try:
            return Articulo.get(Articulo.codbarra == texto)
        except Exception:
            pass

        return Articulo.get_or_none(Articulo.nombre == texto)

    def _coincidencias_articulo(self, texto, limite=None):
        """Los articulos que coinciden con lo escrito, y cuantos hay en total.

        El total va aparte del recorte a proposito: sin el, una lista de 100
        filas no dice si se ve todo el catalogo o solo una parte.
        """
        texto = str(texto or "").strip()

        if not texto:
            # El catalogo entero, recortado. Es lo que muestra el selector
            # cuando se abre sin escribir nada: uno quiere ver que hay.
            consulta = Articulo.select()
            total = consulta.count()
            if limite is None:
                limite = LIMITE_BUSQUEDA_ARTICULOS
            return list(consulta.order_by(Articulo.nombre).limit(limite)), total

        exacto = self._articulo_exacto(texto)
        if exacto:
            return [exacto], 1

        # Nombre O codigo de barras, con el codigo de barras primero.
        #
        # El campo de producto promete "Codigo, nombre o codigo de barras"
        # (placeholder de la vista) y antes solo buscaba por nombre. El
        # barcode COMPLETO ya entraba, por `_articulo_exacto`, que compara con
        # igualdad; el PARCIAL no. Y el parcial es el caso del dia a dia: con
        # un lector en la mano se teclean los primeros digitos.
        #
        # Lo que se ordena primero es lo que arranca con lo escrito, no lo que
        # es igual: sin esto, teclear "10487" devuelve los parciales y el
        # producto escaneado aparece en algun lugar de la lista, y el operador
        # con la compra en la mano tiene que leer 20 filas para encontrarlo.
        condicion = (buscar_texto(Articulo.nombre, texto) |
                     buscar_texto(Articulo.codbarra, texto))
        consulta = Articulo.select().where(condicion)
        total = consulta.count()
        if limite is None:
            limite = LIMITE_BUSQUEDA_ARTICULOS

        # Los codigos son numeros: `contiene` los ordena por texto y no por
        # largo, asi que sin esto el "1048" buscado aparecia despues del
        # "10487123".
        orden = Case(None, [
            (Articulo.codbarra.startswith(texto), 0),
        ], 1)
        return list(consulta.order_by(orden, Articulo.nombre).limit(limite)), total

    def seleccionar_articulo(self, busqueda):
        """Abre el catalogo y devuelve el articulo elegido, o None.

        A diferencia del selector de clientes, este no lleva candado: no
        necesita, porque el campo de producto no tiene editingFinished
        conectado, solo returnPressed. O sea que abrir el dialogo modal no
        vuelve a disparar la entrada que lo abrio. El del cliente si lo
        necesita, y por eso lleva el suyo.
        """
        dialogo = VentaSimpleSeleccionArticuloDialog(
            self._coincidencias_articulo, busqueda=busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None
        return dialogo.articulo

    def buscar_articulo(self, busqueda):
        """El articulo que corresponde a lo escrito, o None.

        DELIGA en `_coincidencias_articulo` a proposito, y no reimplementa la
        busqueda. Antes hacia sus propias tres cosas por separado
        (`get_by_id`, `codbarra == texto`, `nombre.contains().first()`), y eso
        era la mitad del bug del codigo de barras: `agregar_articulo` pregunta
        primero por la ambiguedad (que va por `_coincidencias_articulo`) y despues
        busca el articulo con ESTE metodo. Con un fragmento de barcode, el
        primero contaba 1 coincidencia y este daba 0, asi que caia en el camino
        de "Producto no encontrado. Desea agregarlo?" de un producto que ya
        existia.

        Dos caminos que buscan distinto no se pueden revisar de a uno: el que
        falta siempre parece un detalle del otro.

        Con texto vacio devuelve None a proposito: `_coincidencias_articulo("")`
        devuelve el catalogo entero recortado, y el primero de esa lista seria
        un articulo arbitrario. Quien llama con el campo vacio abre el selector
        (`seleccionar_articulo`), no esto.
        """
        texto = str(busqueda or "").strip()
        if not texto:
            return None

        encontrados, _total = self._coincidencias_articulo(texto, limite=1)
        return encontrados[0] if encontrados else None

    def obtener_renglones(self):
        renglones = []
        for fila in range(self.view.gridVenta.rowCount()):
            renglones.append(RenglonVenta(
                codigo=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Codigo")),
                detalle=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Detalle")),
                cantidad=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Cant."))),
                precio_unitario=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Unitario"))),
                iva=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="IVA"))),
            ))
        return renglones


    # -- La columna Stock ------------------------------------------------------

    @contextlib.contextmanager
    def _escribiendo(self):
        """Marca que la propia app esta escribiendo en la grilla.

        Existe por el `itemChanged`: escribir una celda dispara la senal, y
        el handler que esta atado a ella escribiria otra vez, sin fin. Con
        este candado, todo camino que escribe por su cuenta se envuelve
        aqui y la senal se ignora.

        Va como contextmanager y no como dos lineas porque un `return` en el
        medio del camino sin limpiar el flag deja la grilla muda para el resto
        de la vida de la ventana, que es un fallo que no se ve hasta que
        alguien edita una celda y pasa lo que no tiene que pasar.
        """
        self._pintando = True
        try:
            yield
        finally:
            self._pintando = False

    def on_celda_editada(self, *args, **kwargs):
        """Recalcula el renglon editado: subtotal, total y color del stock.

        Sin esto, cambiar la cantidad a mano dejaba el SubTotal con el valor
        viejo y el color del stock diciendo que la fila entra cuando ya no
        entra. Peor que no tener columna: es informacion que miente.
        """
        if self._pintando:
            return

        # cellChanged pasa la fila y la columna. El numero de fila no se
        # busca con currentRow(): esa es la que esta SELECCIONADA, que con
        # el mouse en otro lado es otra celda, y el renglon recalculado
        # seria uno que el operador no toco.
        fila = args[0] if args else -1
        if fila < 0 or fila >= self.view.gridVenta.rowCount():
            return

        # Antes de recalcular: la celda editada quedo solo con el texto.
        col = args[1] if len(args) > 1 else -1
        self._normaliza_celda(fila, col)

        self._recalcula_el_renglon(fila)
        self.recalcular_total()

    def _normaliza_celda(self, fila, col):
        """Le vuelve a dejar el numero crudo a la celda recien editada.

        Sin esto, editar una celda deja la pantalla y los calculos
        diciendo cosas distintas: `AgregaItem` guarda el numero en
        `UserRole` y `ObtenerItem` lo devuelve crudo, pero editar la celda
        solo cambia el texto. Quedaria "la pantalla muestra 4 y la
        factura dice 2", que es un cobro erroneo y no un detalle de
        colores.

        Se usa `setData` sobre la MISMA celda y no `ModificaItem`, que
        reemplaza el item: reemplazar una celda que se esta editando hace
        que Qt la dibuje avanzando a la fila siguiente mientras se tipea
        (mismo motivo que en Facturas._normaliza_celda).

        Un texto que no es numero se deja como estaba: puede ser el nombre
        del producto o el codigo, y esas columnas no son numericas.
        """
        if col < 0 or col >= self.view.gridVenta.columnCount():
            return

        celda = self.view.gridVenta.item(fila, col)
        if celda is None:
            return

        texto = celda.text()
        if not str(texto).strip():
            return

        try:
            numero = _a_numero_texto(texto)
        except (ValueError, TypeError, InvalidOperation):
            return

        celda.setData(QtCore.Qt.UserRole, numero)

    def _recalcula_el_renglon(self, fila):
        """Vuelve a calcular el SubTotal de una fila a partir de su cantidad.

        Cantidad por Unitario. Es la misma cuenta que hace la venta cuando se
        agrega el producto, escrita otra vez porque no hay otro lugar donde
        quede: `calcular_totales` trabaja sobre una lista de RenglonVenta,
        no sobre la grilla.
        """
        with self._escribiendo():
            col_sub = self._columna("SubTotal")
            col_cant = self._columna("Cant.")
            col_unit = self._columna("Unitario")
            if None in (col_sub, col_cant, col_unit):
                return

            cantidad = self._numero_de_la_celda(fila, col_cant)
            precio = self._numero_de_la_celda(fila, col_unit)
            if cantidad is None or precio is None:
                return

            # El numero, no `str(numero)`: `ModificaItem` solo formatea
            # cuando recibe un int, float o Decimal. Con un string lo
            # escribe tal cual, y el SubTotal salia "150000.0" al lado
            # de un Unitario que decia "1.500,00". Ademas asi se guarda
            # tambien el UserRole, que con el string no pasaba.
            self.view.gridVenta.ModificaItem(cantidad * precio, fila,
                                             col_sub)

        self._pinta_el_stock()

    def _pinta_el_stock(self, *args, **kwargs):
        """Escribe el stock de cada renglon y pinta los que no alcanzan.

        Compara por producto ACUMULADO y no renglon por renglon, por la misma
        razon que `faltantes_de_la_venta`: el mismo producto puede estar en
        dos renglones de la misma venta, y mirando fila por fila las dos
        parecen entrar cuando juntas se llevan mas de lo que hay.

        Esa coincidencia no es casualidad sino un requisito: si la grilla dice
        "estas bien" y el aviso de emitir dice "no alcanza", el operador deja
        de mirar el aviso por desconfianza. Las dos tienen que decir lo mismo.

        Reconstruye la columna entera en vez de tocar solo la fila que cambio:
        el acumulado depende de TODOS los renglones, as que cambiar el
        criterio de uno obliga a recalcular los demas.
        """
        with self._escribiendo():
            col_stock = self._columna("Stock")
            col_cant = self._columna("Cant.")
            col_codigo = self._columna("Codigo")
            if None in (col_stock, col_cant, col_codigo):
                return

            # Una sola consulta para toda la venta, no una por renglon.
            stocks = stock.stock_de_todos(controlados=False)

            pedido = {}
            for fila in range(self.view.gridVenta.rowCount()):
                codigo = self._codigo_de_la_fila(fila, col_codigo)
                if codigo is None:
                    continue
                cantidad = self._numero_de_la_celda(fila, col_cant) or 0
                pedido[codigo] = pedido.get(codigo, 0) + cantidad

            for fila in range(self.view.gridVenta.rowCount()):
                codigo = self._codigo_de_la_fila(fila, col_codigo)
                articulo = Articulo.get_or_none(
                    Articulo.idarticulo == codigo) if codigo else None

                if articulo is None or not stock.controla(articulo):
                    # None, no False: False significa "no alcanza" y un
                    # servicio no es un producto al que le falte nada.
                    self._pinta_celda(fila, col_stock, SIN_STOCK, None)
                    continue

                hay = stocks.get(articulo.idarticulo, stock.CERO)
                alcanza = hay - pedido.get(articulo.idarticulo, 0) >= 0
                # El Decimal crudo, no `str(hay)`: ver `_pinta_celda`.
                self._pinta_celda(fila, col_stock, hay, alcanza)

    def _pinta_celda(self, fila, col, valor, alcanza):
        """Escribe una celda de la columna Stock.

        `alcanza` tiene TRES valores y no dos:

        - True: hay stock. Sin color.
        - False: no hay stock para lo que se lleva. En rojo.
        - None: el stock no aplica (un servicio). Sin color.

        Con un solo booleano, el servicio caia en el caso de "no alcanza" y
        salia en rojo, que le grita al operador que le falta mercaderia que
        no existe. Un color de mas es un color que ya no significa nada.

        El texto se escribe SIEMPRE y el color va aparte: si solo se pintara la
        celda cuando falta, al corregir la cantidad quedaria el numero viejo con
        el color viejo, que es un estado que la app nunca tiene que mostrar.

        El item se busca primero y se reusa. Si no esta, `setItem` lo crea con
        los flags por defecto, que son editables: el stock pasaria a ser una
        celda mas que el operador puede escribir, y escribir ahi no cambia el
        stock de nada.
        """
        item = self.view.gridVenta.item(fila, col)
        if item is None:
            from PyQt5.QtWidgets import QTableWidgetItem
            from PyQt5.QtCore import Qt
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.view.gridVenta.setItem(fila, col, item)

        # `valor` es un numero o el guion de SIN_STOCK. Si es numero se
        # formatea con el tipo que declaro la columna (Moneda, Cantidad,
        # Entero...), que es lo que hace `AgregaItem`.
        #
        # Con `str(hay)` la celda salia "85.0000": el `str` de un Decimal
        # con cuatro decimales. Era el unico numero de la fila que no se
        # leia como los demas.
        if isinstance(valor, (int, float, Decimal)):
            item.setData(QtCore.Qt.UserRole, valor)
            item.setText(self.view.gridVenta._texto_celda(col, valor))
        else:
            # El guion no es un numero: no lleva UserRole ni formato.
            item.setData(QtCore.Qt.UserRole, None)
            item.setText(valor)

        if alcanza is False:
            item.setBackground(QtGui.QBrush(
                QtGui.QColor(COLOR_FALTANTE_FONDO)))
            item.setForeground(QtGui.QColor(COLOR_FALTANTE_TEXTO))
        else:
            # Brush vacio y no un color: es lo que hace la celda transparente
            # y deja ver el color alternado de la fila que define el tema.
            item.setBackground(QtGui.QBrush())
            item.setForeground(QtGui.QBrush())

    def _columna(self, nombre):
        """El indice de la columna con ese encabezado, o None."""
        for c in range(self.view.gridVenta.columnCount()):
            item = self.view.gridVenta.horizontalHeaderItem(c)
            if item is not None and item.text() == nombre:
                return c
        return None

    def _numero_de_la_celda(self, fila, col):
        """El numero de una celda, o None si no se puede leer.

        None y no 0 a proposito: una cantidad vacia o con letras tiene que ser
        distinguible de un cero, porque con 0 no hay venta que hacer y con un
        numero roto tampoco.

        Sale de `ObtenerItem`, que ya devuelve el numero crudo (gracias a
        `_normaliza_celda` cuando la celda fue editada). El parseo del texto
        con replace a mano queda en `libs/Grillas._a_numero_texto`, que es el
        unico que distingue "1.234,56" de "1,234".
        """
        try:
            return Decimal(str(self.view.gridVenta.ObtenerItem(
                fila=fila, col=col)))
        except (InvalidOperation, ValueError, TypeError,
                ArithmeticError):
            return None

    def _codigo_de_la_fila(self, fila, col):
        """El id de articulo de una fila, o None si no es un numero.

        La columna Codigo es editable, asi que puede tener cualquier cosa. Un
        texto ahi no es un producto: se ignora la fila en vez de romper la
        pantalla con un error de base.
        """
        texto = str(self.view.gridVenta.ObtenerItem(fila=fila, col=col)).strip()
        return int(texto) if texto.isdigit() else None

    def _on_forma_pago_changed(self, *args):
        try:
            self._cargar_cuotas()
        finally:
            # El total se recalcula SIEMPRE, aunque recargar los planes
            # falle: dejar el total viejo con otra forma elegida es cobrar
            # con el recargo de la tarjeta anterior.
            self.recalcular_total()

    def _cargar_cuotas(self):
        """Llena el selector de cuotas con los planes de la forma elegida.

        Si no hay planes (EFECTIVO, CTA CTE), el selector queda escondido y
        vale el recargo base (#9). Con tarjeta muestra "3 pagos (15%)".

        La cuota elegida se conserva si la nueva forma tambien la ofrece
        (VISA 6 pagos -> MASTERCARD 6 pagos): antes volvia a 1 pago y el
        total caia a la base, que se lee como que el cambio de forma no
        recalculo nada.
        """
        try:
            anteriores = self._cuotas_elegidas()
        except Exception:
            anteriores = 1
        from controladores.forma_pago_cuotas import planes_de_forma_pago
        try:
            fp_id = self.view.cboFormaPago.text()
            planes = planes_de_forma_pago(fp_id)
        except Exception:
            planes = []
        combo = self.view.cboCuotas
        try:
            combo.blockSignals(True)
            combo.clear()
            if not planes:
                self.view.lblCuotas.setVisible(False)
                combo.setVisible(False)
                return
            for cant, rec in planes:
                etiqueta = ("{} pago".format(cant) if cant == 1
                            else "{} pagos".format(cant))
                if rec:
                    etiqueta += " ({}%)".format(rec)
                combo.addItem(etiqueta, int(cant))
            try:
                idx = combo.findData(int(anteriores or 1))
            except Exception:
                idx = -1
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self.view.lblCuotas.setVisible(True)
            combo.setVisible(True)
        finally:
            try:
                combo.blockSignals(False)
            except Exception:
                pass

    def _cuotas_elegidas(self):
        try:
            return int(self.view.cboCuotas.currentData()
                       or self.view.cboCuotas.currentText().split()[0] or 1)
        except Exception:
            return 1

    def _forma_pago_pct(self):
        """(descuento %, recargo %) de la forma elegida, o (0, 0).

        Con tarjeta y plan elegido, el recargo del plan manda sobre el
        recargo base (issue #37). El descuento sigue siendo el de la forma.
        """
        try:
            from modelos.Formaspago import Formapago
            from controladores.forma_pago_cuotas import recargo_de_plan
            fp_id = self.view.cboFormaPago.text()
            fp = Formapago.get_by_id(int(str(fp_id).strip()))
            rec = recargo_de_plan(fp.idformapago, self._cuotas_elegidas(),
                                  fp.recargo or 0)
            return fp.descuento or 0, rec
        except Exception:
            return 0, 0

    def recalcular_total(self):
        responsable_inscripto = a_entero(LeerIni(clave="cat_iva", key="WSFEv1"), 0) == 1
        totales = calcular_totales(self.obtener_renglones(), responsable_inscripto)
        descuento_pct, recargo_pct = self._forma_pago_pct()
        total_final, _, _ = aplicar_forma_pago(
            totales.total, descuento_pct, recargo_pct)
        # Con el formateador de importes de la app, no con `str(Decimal)`.
        # `str` de un Decimal sale "250100.00": sin punto de miles, con
        # punto decimal, y con la coma cambiada. Al lado de los SubTotal
        # de la grilla, que salen con el formato argentino, el total se ve
        # como si fuera de otra pantalla.
        #
        # El numero en si no cambia: es el mismo `totales.total`. Lo que
        # cambia es como se lee.
        # Si la forma de pago tiene recargo/descuento %, se muestra el
        # total final (issue #9). Con EFECTIVO 0/0 es el mismo numero.
        self.view.textTotal.setText(_formato_importe(total_final))

    def borrar_renglon(self):
        fila = self.view.gridVenta.currentRow()
        if fila >= 0:
            with self._escribiendo():
                self.view.gridVenta.removeRow(fila)
            self.recalcular_total()

    def faltantes_de_la_venta(self, renglones):
        """Los productos de esta venta que se van a quedar en negativo.

        Devuelve lineas de texto para el aviso, no ids. Y acumula por
        articulo antes de comparar: el mismo producto puede estar en dos
        renglones de la misma venta (dos veces 3 unidades con 5 en stock), y
        mirando renglon por renglon uno de los dos parece que entra y solo
        avisaria por el otro. Y peor: avisaria mostrando "quedan 5" cuando en
        realidad quedan -1.
        """
        pedido = {}
        for renglon in renglones:
            pedido[renglon.codigo] = pedido.get(renglon.codigo, Decimal(0)) \
                + Decimal(str(renglon.cantidad))

        lineas = []
        for codigo, cantidad in pedido.items():
            articulo = Articulo.get_or_none(Articulo.idarticulo == codigo)
            if articulo is None or not stock.controla(articulo):
                continue
            hay = stock.stock_de(articulo)
            if hay - cantidad < 0:
                lineas.append("{}: hay {}, se venden {}".format(
                    articulo.nombre, hay, cantidad))
        return lineas

    def emitir_factura(self):
        renglones = self.obtener_renglones()
        if not renglones:
            Ventanas.showAlert("Venta", "Agregue al menos un producto")
            return

        # Avisa antes de emitir, y deja emitir igual. Bloquear la venta por un
        # dato de stock que puede estar mal es peor que el faltante: en un
        # comercio real, quedarse sin poder cobrar le cuesta mas plata al que
        # se esta equivocando de inventario. El boton del aviso dice
        # "Emitir igual" y no "Aceptar", para que quede claro que la app no
        # esta decidiendo.
        faltantes = self.faltantes_de_la_venta(renglones)
        if faltantes and not Ventanas.showConfirmation(
                "Venta sin stock suficiente",
                "Estos productos quedan por debajo de lo que hay:\n\n{}\n\n"
                "¿Emitir la factura igual?".format("\n".join(faltantes)),
                textoOk="Emitir igual", textoCancelar="Volver a la venta"):
            return

        # Primero se resuelve el cliente, y recien despues se arma el
        # FacturaController: construirlo es caro (levanta la vista entera con
        # sus combos y pestanas) y para eso ya se sabe que va a servir.
        if self.view.checkConsumidorFinal.isChecked():
            # La factura B necesita un cliente real en la base (cabfact
            # guarda el id y Validacion() lo exige): se emite al generico
            # CONSUMIDOR FINAL. Sin el, antes caia en "No se ha
            # especificado un cliente valido" con el tilde puesto.
            from controladores.venta_simple_cliente import id_cliente_consumidor_final
            cliente_id = id_cliente_consumidor_final()
            if cliente_id is None:
                Ventanas.showAlert(
                    "Venta",
                    "No hay un cliente CONSUMIDOR FINAL en la base.\n\n"
                    "Cree uno con tipo Consumidor Final para emitir "
                    "sin elegir cliente.")
                return
        else:
            if not self.cliente:
                self.cargar_cliente_desde_busqueda()
            if not self.cliente:
                Ventanas.showAlert("Venta", "Seleccione un cliente válido")
                return
            cliente_id = self.cliente.idcliente

        from controladores.Facturas import FacturaController

        factura = FacturaController()
        factura.cargar_venta_simple(
            cliente_id=cliente_id,
            renglones=renglones,
            forma_pago_id=self.view.cboFormaPago.text(),
            cuotas=self._cuotas_elegidas(),
        )

        # Se emite desde aca y NO mostrando el formulario de emision. El
        # FacturaController de arriba ES esa pantalla: cargar los datos y
        # llamar a exec_() hacia que el operador apretara Emitir aca, se le
        # abriera el formulario grande ya cargado, y tuviera que apretar
        # Emitir otra vez ahi. Es exactamente el rodeo que la venta rapida
        # existe para evitar.
        #
        # El unico planteo que se abre es la barra de progreso de la emision,
        # que hace falta contra ARCA porque tarda.
        #
        # Devolver el resultado permite limpiar la pantalla cuando salio bien
        # y dejarla con los renglones cuando salio mal, para revisar.
        emitida = factura.GrabaFactura()
        if emitida:
            self._limpiar_para_la_siguiente()
        return emitida

    def _limpiar_para_la_siguiente(self):
        """Deja la pantalla vacia para cargar la venta que sigue.

        Solo cuando la factura quedo autorizada. Si no se limpio nada, la
        venta se pierde y no hay forma de recuperarla desde la app.
        """
        with self._escribiendo():
            while self.view.gridVenta.rowCount():
                self.view.gridVenta.removeRow(0)
        self.cliente = None
        self.view.textCliente.setText("")
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
        self.recalcular_total()
