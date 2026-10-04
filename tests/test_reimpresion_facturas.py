"""La reimpresion tiene que listar las facturas.

El sintoma
----------
Reimpresion de facturas salia vacia, con la base sembrada y las facturas
guardadas. El motivo no estaba en esa pantalla: el filtro de la linea 37 es
`if c.tipocomp.exporta`, y `exporta` estaba en cero para TODOS los tipos de
comprobante porque BitBooleanField guardaba como False el '1' que viene del
CSV.

Este test arma una factura guardada y comprueba que aparece en la lista. Con
el bug, la grilla queda en 0 filas aunque la factura exista.

Lo que seAgreedo
---------------
Arreglado lo de los bits, la pantalla seguia sin listar nada, y el motivo era
otro: `CargaFacturasCliente` arranca con

    if not self.view.controles['cliente'].text():
        return

El control es un `Validaciones` (el line edit de `Clientes.Valida()`), asi que
`.text()` es lo que el operador escribio a mano. Vacio es el estado en que la
pantalla abre, y vacio es exactamente cuando no listaba nada. Escribiendo el
numero de cliente a mano si aparecian, que es lo que hace creer que la pantalla
anda.

Estos tests fijan las tres cosas que quedaban mal:

1. Sin cliente se listan TODAS las del periodo, que es lo que el operador pide
   cuando todavia no sabe de quien son.
2. La columna `idcabecera` es interna: la usa el boton Imprimir para recuperar
   el comprobante, y no tiene por que estar a la vista.
3. "Reimprimir remito" abria la ventana de "Reimpresion de facturas", porque
   el controlador de remitos se construia con la vista de facturas.
"""

import datetime
import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class _Falso(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


class _Fila(object):
    """Una fila del grid, como las que arma AgregaItem."""

    def __init__(self):
        self.filas = []

    def AgregaItem(self, items=None):
        self.filas.append(items)

    def setRowCount(self, n):
        pass


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _factura_de_prueba(tipo_exporta):
    return _Falso(
        fecha="2026-10-04",
        numero="100100000001",
        total=Decimal("25000"),
        idcabfact=1,
        cliente=_Falso(nombre="CONSUMIDOR FINAL", idcliente=1),
        tipocomp=_Falso(codigo=11, nombre="FACTURA C", exporta=tipo_exporta),
    )


def _controlador(qt, monkeypatch, fecha="04/10/2026", cliente="1"):
    import controladores.ReImprimeFactura as MOD

    c = MOD.ReImprimeFacturaController.__new__(MOD.ReImprimeFacturaController)
    c.view = _Falso()
    c.view.gridDatos = _Fila()
    c.view.controles = {
        "cliente": _Falso(text=lambda: cliente),
        "fecha": _Falso(date=lambda: _Falso(toPyDate=lambda: datetime.date(2026, 10, 4))),
    }
    return c


class _Consulta(object):
    """Registra las condiciones para poder mirarlas despues."""

    def __init__(self, filas):
        self.filas = filas
        self.condiciones = []

    def join(self, *a, **k):
        return self

    def switch(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def where(self, *a, **k):
        self.condiciones.extend(a)
        return self

    def __iter__(self):
        return iter(self.filas)


# El `select` de peewee de cada modelo, guardado antes de que un test lo
# parchee. La cache es por modelo y no por test porque hay un test que parchea
# dos veces en la misma corrida: la segunda guardaria el doble del primero.
_SELECT_REALES = {}


def _monkey(monkeypatch, filas, modelo):
    if modelo not in _SELECT_REALES:
        _SELECT_REALES[modelo] = modelo.select
    consulta = _Consulta(filas)
    consulta.modelo = modelo
    consulta.select_real = _SELECT_REALES[modelo]
    monkeypatch.setattr(modelo, "select",
                        staticmethod(lambda *a, **k: consulta))
    return consulta


def _monkey_facturas(monkeypatch, filas):
    from modelos.Cabfact import Cabfact

    return _monkey(monkeypatch, filas, Cabfact)


def _where_de(consulta):
    """El WHERE de la consulta, no el SELECT entero.

    Dos cosas hacen que esto no sea trivial:

    - `str(una Expression de peewee)` devuelve `<peewee.Expression object at
      0x...>`, no el SQL. Buscar "fecha" ahi no encuentra nunca nada y el test
      pasa (o falla) por una razon que no es la del bug.
    - El SELECT lista las columnas de la tabla, `idCliente` entre ellas, asi
      que buscar el nombre de la columna ahi siempre da true. Lo que importa
      es si esta en el WHERE.

    El `select` que se usa es el de peewee, no el del modelo: en estos tests el
    del modelo esta parcheado con un doble que no sabe responder `.sql()`.
    """
    sql, _params = consulta.select_real(consulta.modelo)\
        .where(*consulta.condiciones).sql()
    return sql.split(" WHERE ", 1)[-1]


# ---------------------------------------------------------------- listado


def test_una_factura_c_aparece_en_la_lista(qt, monkeypatch):
    """El caso que reporto el operador: hay facturas y la lista sale vacia."""
    _monkey_facturas(monkeypatch, [_factura_de_prueba(True)])
    c = _controlador(qt, monkeypatch)
    c.CargaFacturasCliente()

    assert len(c.view.gridDatos.filas) == 1, \
        "la factura no aparece en la reimpresion"
    assert c.view.gridDatos.filas[0][1] == "CONSUMIDOR FINAL"


def test_un_tique_no_aparece(qt, monkeypatch):
    """El filtro existe para eso: los tiques no se reimprimen desde aca."""
    _monkey_facturas(monkeypatch, [_factura_de_prueba(False)])
    c = _controlador(qt, monkeypatch)
    c.CargaFacturasCliente()

    assert c.view.gridDatos.filas == []


def test_sin_cliente_lista_las_del_periodo(qt, monkeypatch):
    """El caso que reporto el operador en la pantalla: campo vacio, nada.

    La pantalla se abre con el cliente en blanco. Antes el metodo volvia
    enseguida y la grilla quedaba en cero filas sin decir por que, que es lo
    que hace parecer que no hay nada guardado.
    """
    _monkey_facturas(monkeypatch, [_factura_de_prueba(True), _factura_de_prueba(True)])
    c = _controlador(qt, monkeypatch, cliente="")
    c.CargaFacturasCliente()

    assert len(c.view.gridDatos.filas) == 2, \
        "con el cliente vacio tiene que listar las comprobantes del periodo"


def test_sin_cliente_no_filtra_por_cliente(qt, monkeypatch):
    """Vacio significa 'todos', no 'el cliente que se llama vazio'."""
    consulta = _monkey_facturas(monkeypatch, [])
    c = _controlador(qt, monkeypatch, cliente="")
    c.CargaFacturasCliente()

    assert "idCliente" not in _where_de(consulta), \
        "sin cliente escrito no se puede filtrar por cliente: %s" % _where_de(consulta)


def test_con_cliente_escrito_sigue_filtrando(qt, monkeypatch):
    """Lo que funcionaba antes tiene que seguir funcionando."""
    consulta = _monkey_facturas(monkeypatch, [_factura_de_prueba(True)])
    c = _controlador(qt, monkeypatch, cliente="1")
    c.CargaFacturasCliente()

    assert "idCliente" in _where_de(consulta)


def test_siempre_filtra_por_fecha(qt, monkeypatch):
    """La fecha es lo unico que acota la lista cuando no hay cliente."""
    for cliente in ("", "1"):
        consulta = _monkey_facturas(monkeypatch, [])
        c = _controlador(qt, monkeypatch, cliente=cliente)
        c.CargaFacturasCliente()

        assert "fecha" in _where_de(consulta), \
            "con cliente %r hay que filtrar por fecha" % cliente


# --------------------------------------------------------------- columnas


def test_la_columna_interna_no_se_muestra(qt):
    """`idcabecera` es para el boton Imprimir, no para el operador.

    A la vista le ocupa una de las cuatro columnas de la pantalla y escribe un
    nombre de campo de la base donde deberia leerse la fecha o el importe.
    """
    from vistas.ReImprimeFactura import ReImprimeFacturaView

    v = ReImprimeFacturaView()
    try:
        g = v.gridDatos
        assert "idcabecera" in g.cabeceras, \
            "el id tiene que seguir en la grilla, si no Imprimir no recupera nada"
        assert g.isColumnHidden(g.cabeceras.index("idcabecera")), \
            "la columna idcabecera se le esta mostrando al operador"
    finally:
        v.close()


def test_la_columna_oculta_sigue_sirviendo_para_imprimir(qt):
    """Ocultar la columna no puede romper lo que la lee.

    `ObtenerItem` lee la celda, no lo que se ve, asi que tiene que devolver el
    id aunque la columna este oculta. Si alguna vez dejara de hacerlo, el
    boton Imprimir pasaria el 0 silenciosamente.
    """
    from vistas.ReImprimeFactura import ReImprimeFacturaView

    v = ReImprimeFacturaView()
    try:
        g = v.gridDatos
        g.AgregaItem(items=["2026-10-04", "CONSUMIDOR FINAL", "100100000001",
                            Decimal("25000"), 7, 1])
        assert g.ObtenerItem(fila=0, col="idcabecera") == 7
    finally:
        v.close()


# ------------------------------------------------------------------- correo


def test_el_correo_va_al_cliente_de_la_fila(qt, monkeypatch):
    """El boton de correo tomaba el cliente del campo de arriba.

    Con la pantalla listando las comprobantes de todos los clientes del
    periodo, ese campo puede estar vacio: la busqueda de mails daba vacia y
    el comprobante se guardaba sin destinatario, sin decir nada. El
    destinatario sale de la fila elegida.
    """
    import controladores.ReImprimeFactura as MOD

    c = MOD.ReImprimeFacturaController.__new__(MOD.ReImprimeFacturaController)
    c.view = _Falso()
    c.view.gridDatos = _Falso(
        currentRow=lambda: 0,
        ObtenerItem=lambda fila, col: {"idcabecera": 7, "idcliente": 42}[col],
    )
    c.view.controles = {"cliente": _Falso(text=lambda: "")}

    pedidos = {}

    class _Factura(object):
        facturaGenerada = r"C:\tmp\factura.pdf"

        def ImprimeFactura(self, idcabecera, mostrar=False):
            pedidos["imprimio"] = idcabecera

    class _Setext(object):
        def __init__(self):
            self.texto = None

        def setText(self, texto):
            self.texto = texto

    class _Controlador(object):
        def __init__(self):
            self.view = _Falso(textAsunto=_Setext(), textPara=_Setext())
            self.cliente = None
            self.adjuntos = None

        def ActualizaListaAdjuntos(self):
            pass

        def exec_(self):
            pedidos["se_abrio"] = True
            pedidos["controlador"] = self

    class _Mails(object):
        def where(self, condicion):
            # `.lhs` y `.rhs` en vez de `str(condicion)`: eso ultimo devuelve
            # la direccion de memoria del objeto, no el valor buscado.
            pedidos["campo"] = str(condicion.lhs)
            pedidos["valor"] = condicion.rhs
            return self

        def __iter__(self):
            return iter([_Falso(email="cliente@example.com")])

    monkeypatch.setattr(MOD, "FacturaController", lambda: _Factura())
    monkeypatch.setattr(MOD, "EnvioEmailController", _Controlador)
    monkeypatch.setattr(MOD.EmailCliente, "select", staticmethod(lambda *a: _Mails()))

    c.EnviarPorCorreo()

    assert pedidos.get("imprimio") == 7, "imprimio otra cosa"
    assert pedidos.get("valor") == 42, \
        "los mails se tienen que buscar por el cliente de la fila: %r" % \
        (pedidos.get("valor"),)
    assert pedidos.get("se_abrio"), "no se abrio la pantalla de envio"
    ctrl = pedidos.get("controlador")
    assert ctrl.cliente == 42, "el cliente del comprobante no es el de la fila"
    assert ctrl.view.textPara.texto == "cliente@example.com", \
        "no se cargo la lista de mails: %r" % ctrl.view.textPara.texto


# ---------------------------------------------------------------- remitos


def test_reimprimir_remito_no_abre_la_pantalla_de_facturas(qt):
    """ElBug reportado en la captura.

    `ReImprimeRemitoController` se construia con `ReImprimeFacturaView()`, asi
    que al tocar "Reimprimir remito" se abria una ventana titulada
    "Reimpresion de facturas", con los botones de correo que en una pantalla
    de remitos no tienen a quien mandarle.
    """
    from controladores.ReImprimeRemito import ReImprimeRemitoController

    c = ReImprimeRemitoController()
    try:
        assert c.view.windowTitle() != "Reimpresión de facturas", \
            "la pantalla de remitos esta mostrando la de facturas"
        assert "remito" in c.view.windowTitle().lower()
    finally:
        c.view.close()


def test_el_boton_cargar_de_remitos_hace_algo(qt):
    """Con la vista de facturas el boton 'Cargar' existe pero no esta conectado.

    `conectarWidgets` del controlador de remitos nunca lo conecto, porque el
    metodo se llamaba distinto al que hay en la vista.
    """
    from controladores.ReImprimeRemito import ReImprimeRemitoController

    c = ReImprimeRemitoController()
    try:
        assert c.view.btnCargar.receivers(c.view.btnCargar.clicked) > 0, \
            "el boton Cargar de remitos no esta conectado a nada"
    finally:
        c.view.close()


def test_los_remitos_sin_cliente_listan_el_periodo(qt, monkeypatch):
    """Mismo problema que en facturas, y sin filtro de fecha encima.

    La consulta era `Remito.cliente == texto()`, con el texto vacio: cero
    remitos para siempre, ni de este ni de ningun otro cliente.
    """
    import modelos.Remitos as MR

    consulta = _monkey(monkeypatch,
                       [_Falso(fecha="2026-10-04", numero=3, total=150,
                               idremito=2, cliente_id=1,
                               cliente=_Falso(nombre="CONSUMIDOR FINAL"))],
                       MR.Remito)

    import controladores.ReImprimeRemito as MOD
    c = MOD.ReImprimeRemitoController.__new__(MOD.ReImprimeRemitoController)
    c.view = _Falso()
    c.view.gridDatos = _Fila()
    c.view.controles = {
        "cliente": _Falso(text=lambda: ""),
        "fecha": _Falso(date=lambda: _Falso(
            toPyDate=lambda: datetime.date(2026, 10, 4))),
    }
    c.CargaRemitosCliente()

    assert "cliente" not in _where_de(consulta), \
        "sin cliente escrito no se puede filtrar por cliente: %s" % _where_de(consulta)
    assert len(c.view.gridDatos.filas) == 1
    assert "fecha" in _where_de(consulta), "los remitos tambien se filtran por fecha"


# ----------------------------------------------------------------- maestros


def test_las_facturas_de_exporta_vienen_por_defecto_del_csv():
    """El '1' del CSV tiene que haber llegado a la base.

    Sin esto, la pantalla de arriba esta bien y la de abajo no, y parece un
    problema de cada una por separado.
    """
    import csv

    ruta = os.path.join(RAIZ, "data", "tipocomprobante.csv")
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = {int(r[0]): int(r[4] or 0)
                 for r in list(csv.reader(f, delimiter=","))[1:] if r and r[0].strip()}

    assert filas[11] == 1, "el CSV no marca FACTURA C como exporta"
    assert filas[1] == 1, "el CSV no marca FACTURA A como exporta"
    assert filas[82] == 0, "el CSV deberia dejar el tique fuera"
