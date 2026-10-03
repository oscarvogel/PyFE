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


def test_graba_factura_muestra_error_si_creafe_falla(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas

    errores = []
    monkeypatch.setattr(Facturas.Ventanas, "showConfirmation", lambda *a, **k: True)
    monkeypatch.setattr(
        Facturas.Ventanas, "showError",
        lambda titulo, mensaje, que_hacer=None, detalle=None:
            errores.append((titulo, mensaje, que_hacer, detalle)))

    controller = _controlador_testeable()
    controller.GrabaFactura()

    assert controller.view.btnGrabarFactura.habilitado is True
    assert controller.view.cerrada is False
    assert len(errores) == 1
    titulo, mensaje, que_hacer, detalle = errores[0]
    assert detalle == "TypeError: prueba"
    assert que_hacer, "un error tiene que decir QUE HACER, no solo el codigo"
    assert "Diagnostico" in que_hacer


def test_graba_factura_no_hace_nada_si_se_cancela_la_confirmacion(monkeypatch):
    """La confirmacion es real: cancelar no puede emitir."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas

    errores = []
    monkeypatch.setattr(Facturas.Ventanas, "showConfirmation", lambda *a, **k: False)
    monkeypatch.setattr(
        Facturas.Ventanas, "showError", lambda *a, **k: errores.append(a))

    controller = _controlador_testeable()
    controller.CreaFE = lambda: pytest.fail("no se debe llamar a AFIP si se cancelo")
    controller.GrabaFactura()

    assert controller.view.btnGrabarFactura.habilitado is True
    assert controller.view.cerrada is False
    assert errores == []


def test_graba_factura_avanza_por_las_etapas_de_la_emision(monkeypatch):
    """Cada etapa real de la emision se anuncia, no una barra que gira sola."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores import Facturas
    from libs import Ventanas

    monkeypatch.setattr(Facturas.Ventanas, "showConfirmation", lambda *a, **k: True)
    monkeypatch.setattr(Facturas.Ventanas, "showError", lambda *a, **k: None)

    etapas = []
    progreso_real = Ventanas.Progreso

    class ProgresoEspia(progreso_real):
        def __init__(self, titulo, etaps, cancelable=False):
            super().__init__(titulo, etaps, cancelable)
            etapas.extend(etaps)

        def avanzar(self, etapa=None, detalle=None):
            self.actual = etapa
            super().avanzar(etapa, detalle)

    monkeypatch.setattr(Facturas.Ventanas, "Progreso", ProgresoEspia)

    controller = _controlador_testeable()

    def crea_falso():
        controller._etapa("Autenticando en AFIP")
        controller._etapa("Obteniendo el CAE")
        return True

    controller.CreaFE = crea_falso
    controller.GrabaFactura()

    assert etapas == Facturas.FacturaController.ETAPAS_EMISION
    assert controller.view.cerrada is True
