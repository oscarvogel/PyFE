import sys

import pytest


def test_crear_factura_wsfe_envia_condicion_iva_receptor(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.Facturas import FacturaController

    class TipoResp:
        condicion_iva_receptor_id = 5

    class Cliente:
        tiporesp = TipoResp()

    class Wsfe:
        def CrearFactura(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            return True

    controller = object.__new__(FacturaController)
    controller.cliente = Cliente()
    wsfe = Wsfe()

    ok = controller.crear_factura_wsfe(
        wsfe,
        concepto=1,
        tipo_doc=99,
        nro_doc="",
        tipo_cbte=6,
        punto_vta=3,
        cbt_desde=1,
        cbt_hasta=1,
        imp_total="121.00",
        imp_tot_conc="0.00",
        imp_neto="100.00",
        imp_iva="21.00",
        imp_trib="0.00",
        imp_op_ex="0.00",
        fecha_cbte="20260530",
        fecha_venc_pago="",
        fecha_serv_desde="",
        fecha_serv_hasta="",
        moneda_id="PES",
        moneda_ctz="1.000",
    )

    assert ok is True
    assert wsfe.kwargs["cancela_misma_moneda_ext"] == "N"
    assert wsfe.kwargs["condicion_iva_receptor_id"] == 5


def _controlador_testeable():
    from controladores.Facturas import FacturaController

    class Boton:
        habilitado = True

        def setEnabled(self, valor):
            self.habilitado = valor

    class View:
        def __init__(self):
            self.btnGrabarFactura = Boton()
            self.cerrada = False

        def Cerrar(self):
            self.cerrada = True

    controller = object.__new__(FacturaController)
    controller.view = View()
    controller.Excepcion = "TypeError: prueba"
    controller.Traceback = ""
    controller._error_afip = ""
    controller.Validacion = lambda: True
    controller.SumaTodo = lambda: None
    controller.CreaFE = lambda: False
    controller.GrabaFE = lambda: True
    return controller


def _controlador_minimo():
    """Un controlador con lo justo, sin vista real ni base."""
    from controladores.Facturas import FacturaController

    class View(object):
        pass

    c = object.__new__(FacturaController)
    c.view = View()
    c.Excepcion = ""
    c.Traceback = ""
    c._error_afip = ""
    c.SilenciarError = False
    c._progreso = None
    return c


# -- La confirmacion sigue siendo real ---------------------------------------

def test_cancelar_la_confirmacion_no_emite(monkeypatch):
    """Con una factura a medio cargar, cancelar no puede autorizar nada."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas

    controller = _controlador_minimo()
    controller.Validacion = lambda: True
    controller._datos_emision = lambda: pytest.fail(
        "no se puede leer nada si todavia no se confirmo")

    monkeypatch.setattr(Facturas.Ventanas, "showConfirmation",
                        lambda *a, **k: False)

    controller.GrabaFactura()

    assert controller.SilenciarError is False,         "se dejo silenciado el error sin haber empezado"


def test_confirmar_arranca_a_emirir(monkeypatch):
    """Y al confirmar, se leen los datos y entra al hilo."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas

    controller = _controlador_minimo()

    class Boton(object):
        def setEnabled(self, valor):
            self.valor = valor

    controller.view.btnGrabarFactura = Boton()
    controller.Validacion = lambda: True
    leidos = []
    controller._datos_emision = lambda: leidos.append(1) or {"tipo_cbte": 6}
    emitidos = []
    controller._emitir_en_hilo = lambda datos: emitidos.append(datos)

    monkeypatch.setattr(Facturas.Ventanas, "showConfirmation",
                        lambda *a, **k: True)

    controller.GrabaFactura()

    assert leidos, "no se leyeron los datos de la pantalla"
    assert emitidos, "no se entro al hilo de emision"
    assert controller.SilenciarError is False, "quedo silenciado el error"
    assert controller.view.btnGrabarFactura.valor is True, \
        "el boton quedo deshabilitado"


# -- Que cruza al hilo -------------------------------------------------------

def test_lo_que_va_al_hilo_son_datos_planos(monkeypatch):
    """Un dict, no el controlador.

    Si al hilo de trabajo se le pasa el controlador, ese termina tocando
    widgets y base desde alla: Qt no lo permite y peewee no es thread-safe.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.Facturas import FacturaController

    controller = _controlador_minimo()

    class CheckBox(object):
        def __init__(self, valor):
            self.valor = valor

        def isChecked(self):
            return self.valor

    class Campo(object):
        def __init__(self, texto=""):
            self._t = texto

        def text(self):
            return self._t

    class Numero(object):
        def __init__(self, v):
            self.v = v

        def value(self):
            return self.v

    class Fecha(object):
        def getFechaSql(self):
            return "20261003"

    class Seleccion(object):
        numero = ""
        lineEditPtoVta = Campo("0001")
        lineEditNumero = Campo("00000001")

    class Pantalla(object):
        checkBoxProductos = CheckBox(True)
        checkBoxServicios = CheckBox(False)
        lineEditDocumento = Campo("11111111")
        lineEditTotal = Campo("9900.00")
        lineEditTributos = Campo("0.00")
        lineEditTotalIVA = Campo("1718.18")
        lineEditFecha = Fecha()
        layoutFactura = type("L", (), {
            "lineEditPtoVta": Numero(1), "lineEditNumero": Numero(1)})()
        layoutCpbteRelacionado = Seleccion()
        fechaDesde = Fecha()
        fechaHasta = Fecha()

    class TipoResp(object):
        idtiporesp = 3
        condicion_iva_receptor_id = 5

    class Cliente(object):
        tiporesp = TipoResp()

        class percepcion(object):
            detalle = ""
            porcentaje = 0

    controller.view = Pantalla()
    controller.cliente = Cliente()
    controller.netos = {"21.0": 8181.82}
    controller.tipo_cpte = 6

    # El neto depende de si el emisor es responsable inscripto, y eso sale del
    # sistema.ini de la maquina donde corra el test. Se fija aca para no depender
    # de la instalacion. Ojo: LeerIni se llama con clave= y key= por nombre.
    from controladores import Facturas

    def leer_ini(*args, **k):
        if k.get("clave") == "cat_iva" and k.get("key") == "WSFEv1":
            return "1"
        return "S"

    monkeypatch.setattr(Facturas, "LeerIni", leer_ini)

    datos = controller._datos_emision()

    assert isinstance(datos, dict), "tiene que cruzar un dict, no el controlador"
    for clave, valor in datos.items():
        assert type(valor).__name__ in ("dict", "str", "int", "float", "bool", \
                                        "NoneType"), \
            "{} no es un dato plano: {}".format(clave, type(valor).__name__)
    assert "tipo_cbte" in datos
    assert "imp_total" in datos
    # Responsable inscripto: el neto se separa de los tributos y el IVA.
    assert datos["imp_neto"] == "8181.82", datos["imp_neto"]


def test_el_neto_se_calcula_segun_la_categoria_de_iva(monkeypatch):
    """Si el total ya incluye el IVA (monotributo), el neto es el total.

    Es la diferencia entre emitir bien y que ARCA lo rechace por descuadrar.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas

    controller = _controlador_minimo()
    controller.netos = {}
    controller.tipo_cpte = 6

    def pantalla(total, tributos, iva):
        class Campo(object):
            def __init__(self, t):
                self._t = t

            def text(self):
                return self._t
        return type("P", (), {
            "checkBoxProductos": type("C", (), {"isChecked": lambda s: True})(),
            "checkBoxServicios": type("C", (), {"isChecked": lambda s: False})(),
            "lineEditDocumento": Campo("11111111"),
            "lineEditTotal": Campo(total),
            "lineEditTributos": Campo(tributos),
            "lineEditTotalIVA": Campo(iva),
            "lineEditFecha": type("F", (), {"getFechaSql": lambda s: "20261003"})(),
            "layoutFactura": type("L", (), {
                "lineEditPtoVta": type("N", (), {"value": lambda s: 1})(),
                "lineEditNumero": type("N", (), {"value": lambda s: 1})()})(),
            "layoutCpbteRelacionado": type("R", (), {
                "numero": "", "lineEditPtoVta": Campo(""),
                "lineEditNumero": Campo("")})(),
            "fechaDesde": type("F", (), {"getFechaSql": lambda s: "20261003"})(),
            "fechaHasta": type("F", (), {"getFechaSql": lambda s: "20261003"})(),
        })()

    class TipoResp(object):
        idtiporesp = 3
        condicion_iva_receptor_id = 5

    class Cliente(object):
        tiporesp = TipoResp()

        class percepcion(object):
            detalle = ""
            porcentaje = 0

    controller.cliente = Cliente()

    def correr(cat_iva, total, tributos, iva):
        controller.view = pantalla(total, tributos, iva)

        def leer_ini(*args, **k):
            if k.get("clave") == "cat_iva" and k.get("key") == "WSFEv1":
                return cat_iva
            return "S"

        monkeypatch.setattr(Facturas, "LeerIni", leer_ini)
        return controller._datos_emision()["imp_neto"]

    assert correr("1", "9900.00", "0.00", "1718.18") == "8181.82"
    assert correr("6", "9900.00", "0.00", "1718.18") == "9900.0"


def test_el_tipo_de_documento_sale_del_cliente():
    from controladores.Facturas import FacturaController as FC
    assert FC._tipo_documento(True, "11111111") == 96      # consumidor final con DNI
    assert FC._tipo_documento(True, "0") == 99             # sin identificar
    assert FC._tipo_documento(False, "20-12345678-6") == 80  # inscripto con CUIT


# -- Lo que muestra cuando algo sale mal -------------------------------------

def test_el_worker_no_tiene_padre(monkeypatch):
    """El bug que hacia todo esto inutil sin que se notara.

    Qt no deja mover a otro hilo un QObject que tenga padre, y no lanza
    excepcion: escribe en la consola

        QObject::moveToThread: Cannot move objects with a parent

    y sigue. El worker se queda en el hilo principal, las llamadas a ARCA se
    ejecutan aca, y la ventana se sigue congelando. Parece enhebrado y no lo
    esta. Por eso el worker se crea SIN padre.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from PyQt5.QtCore import QThread
    from PyQt5.QtWidgets import QApplication, QWidget
    from controladores.Facturas import _EmisionWorker

    app = QApplication.instance() or QApplication([])

    class Controlador(object):
        def _autorizar(self, datos, avisar=None):
            return True, {"cae": "1", "resultado": "A", "vencimiento": "",
                          "error": ""}

    ventana = QWidget()
    con_padre = _EmisionWorker(Controlador(), {}, parent=ventana)
    sin_padre = _EmisionWorker(Controlador(), {})

    hilo = QThread()
    # Con padre, Qt se queja (o no hace nada) en vez de fallar: por eso el
    # assert es sobre la propiedad del objeto, no sobre una excepcion.
    con_padre.moveToThread(hilo)
    sin_padre.moveToThread(hilo)
    assert sin_padre.thread() is hilo, "el worker sin padre tiene que mudarse"
    assert con_padre.parent() is ventana, "este si lo tiene, y por eso no se muda"
    hilo.deleteLater()
    ventana.deleteLater()


def test_el_worker_avisca_las_etapas_por_senal(monkeypatch):
    """La etapa se emite como senal, no tocando el dialogo de progreso.

    _etapa() toca widgets, y desde el hilo de trabajo eso no se puede: por eso
    el worker recibe la funcion avisar y la conecta a una senal.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.Facturas import _EmisionWorker

    etapas = []

    class Controlador(object):
        def _autorizar(self, datos, avisar=None):
            avisar("Autenticando en ARCA")
            avisar("Obteniendo el CAE")
            return True, {"cae": "864", "resultado": "A", "vencimiento": "",
                          "error": ""}

    worker = _EmisionWorker(Controlador(), {"tipo_cbte": 6})
    worker.etapa.connect(etapas.append)
    worker.run()

    assert etapas == ["Autenticando en ARCA", "Obteniendo el CAE"]
    assert worker.resultado[0] is True


def test_el_cae_rechazado_no_se_escribe_en_la_pantalla(monkeypatch):
    """Si ARCA rechaza, la pantalla no muestra un CAE que no existe."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = _controlador_minimo()

    class Campo(object):
        def __init__(self):
            self.texto = ""

        def setText(self, v):
            self.texto = v

    class Fecha(object):
        def setFecha(self, *a, **k):
            self.llamada = True

    controller.view.lineditCAE = Campo()
    controller.view.lineEditResultado = Campo()
    controller.view.fechaVencCAE = Fecha()

    controller._aplicar_resultado(False, {"error": "rechazada", "cae": "123"})

    assert controller.view.lineditCAE.texto == "", \
        "se escribio un CAE en una factura que ARCA rechazo"
    assert controller._error_afip == "rechazada"


def test_el_cae_bueno_si_se_escribe(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = _controlador_minimo()

    class Campo(object):
        def __init__(self):
            self.texto = ""

        def setText(self, v):
            self.texto = v

    class Fecha(object):
        def setFecha(self, fecha, format=None):
            self.fecha = fecha

    controller.view.lineditCAE = Campo()
    controller.view.lineEditResultado = Campo()
    controller.view.fechaVencCAE = Fecha()

    ok = controller._aplicar_resultado(
        True, {"cae": "86400944641465", "resultado": "A",
               "vencimiento": "20261013", "error": ""})

    assert ok is True
    assert controller.view.lineditCAE.texto == "86400944641465"
    assert controller.view.lineEditResultado.texto == "A"
    assert controller.view.fechaVencCAE.fecha == "20261013"
    assert controller._error_afip == ""
