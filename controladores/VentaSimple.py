# coding=utf-8
from decimal import Decimal

from peewee import fn
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QDialog, QShortcut

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, calcular_totales
from libs import Ventanas
from libs import stock
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
        self.view.checkConsumidorFinal.stateChanged.connect(self.on_consumidor_final_changed)
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

        Campo con texto: se busca, y si no aparece se ofrece darlo de alta.
        Ese camino no se toca, porque es el que permite cargar algo nuevo sin
        salir de la pantalla.
        """
        busqueda = self.view.textArticulo.text().strip()
        if not busqueda:
            articulo = self.seleccionar_articulo("")
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

        self.view.gridVenta.AgregaItem(items=[
            str(cantidad),
            str(articulo.idarticulo),
            articulo.nombre,
            str(precio),
            str(iva),
            str(subtotal),
        ])
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
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

        consulta = Articulo.select().where(buscar_texto(Articulo.nombre, texto))
        total = consulta.count()
        if limite is None:
            limite = LIMITE_BUSQUEDA_ARTICULOS
        return list(consulta.order_by(Articulo.nombre).limit(limite)), total

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
        try:
            return Articulo.get_by_id(busqueda)
        except Exception:
            pass

        try:
            return Articulo.get(Articulo.codbarra == busqueda)
        except Exception:
            pass

        return Articulo.select().where(Articulo.nombre.contains(busqueda)).first()

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

    def recalcular_total(self):
        responsable_inscripto = a_entero(LeerIni(clave="cat_iva", key="WSFEv1"), 0) == 1
        totales = calcular_totales(self.obtener_renglones(), responsable_inscripto)
        self.view.textTotal.setText(str(totales.total))

    def borrar_renglon(self):
        fila = self.view.gridVenta.currentRow()
        if fila >= 0:
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
        cliente_id = None
        if not self.view.checkConsumidorFinal.isChecked():
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
        while self.view.gridVenta.rowCount():
            self.view.gridVenta.removeRow(0)
        self.cliente = None
        self.view.textCliente.setText("")
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
        self.recalcular_total()
