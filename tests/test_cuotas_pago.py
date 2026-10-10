"""Issue #37: planes de cuotas por tarjeta.

Cada tarjeta define sus planes (cuotas + recargo %). Sin planes vale el
recargo base de la forma (#9).
"""
import os
import sys
from decimal import Decimal

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.ayuda_stock import base_memoria  # noqa: E402

from controladores.forma_pago_cuotas import (es_tarjeta, planes_de_forma_pago,  # noqa: E402
                                             recargo_de_plan)
from controladores.venta_simple_totales import aplicar_forma_pago  # noqa: E402
from modelos.CuotasPago import CuotaPago  # noqa: E402
from modelos.Formaspago import Formapago  # noqa: E402


def _sembrar_tarjetas():
    # base_memoria ya trae EFECTIVO id 1: solo se agregan las tarjetas.
    Formapago.insert_many([
        {"idformapago": 3, "detalle": "VISA", "tarjeta": True},
        {"idformapago": 4, "detalle": "MASTERCARD", "tarjeta": True},
    ]).execute()
    CuotaPago.insert_many([
        {"formapago": 3, "cuotas": 1, "recargo": 0},
        {"formapago": 3, "cuotas": 3, "recargo": 15},
        {"formapago": 3, "cuotas": 6, "recargo": 25},
        {"formapago": 4, "cuotas": 1, "recargo": 0},
    ]).execute()


def test_efectivo_no_tiene_planes():
    with base_memoria():
        _sembrar_tarjetas()
        assert planes_de_forma_pago(1) == []
        assert not es_tarjeta(1)


def test_visa_tiene_sus_tres_planes_ordenados():
    with base_memoria():
        _sembrar_tarjetas()
        assert planes_de_forma_pago(3) == [
            (1, Decimal("0")), (3, Decimal("15")), (6, Decimal("25")),
        ]
        assert es_tarjeta(3)


def test_el_recargo_sale_del_plan_y_no_del_base():
    with base_memoria():
        _sembrar_tarjetas()
        assert recargo_de_plan(3, 3, recargo_base=0) == Decimal("15")
        assert recargo_de_plan(3, 6, recargo_base=0) == Decimal("25")
        assert recargo_de_plan(3, 1, recargo_base=0) == Decimal("0")


def test_sin_plan_para_esa_cuota_vale_el_base():
    with base_memoria():
        _sembrar_tarjetas()
        # VISA no tiene plan de 12: no se inventa un 0, vale el base.
        assert recargo_de_plan(3, 12, recargo_base=10) == Decimal("10")
        # Y sin base tampoco revienta.
        assert recargo_de_plan(1, 3, recargo_base=0) == Decimal("0")


def test_mil_pesos_en_3_pagos_de_visa_da_1150():
    with base_memoria():
        _sembrar_tarjetas()
        rec = recargo_de_plan(3, 3, recargo_base=0)
        total, _, importe = aplicar_forma_pago(Decimal("1000.00"), 0, rec)
        assert importe == Decimal("150.00")
        assert total == Decimal("1150.00")


def test_cuota_rara_no_rompe_el_total():
    with base_memoria():
        _sembrar_tarjetas()
        rec = recargo_de_plan(3, None, recargo_base=0)
        total, _, _ = aplicar_forma_pago(Decimal("1000.00"), 0, rec)
        assert total == Decimal("1000.00")


# -- Desde Formas de pago se abre una grilla, no un ABM --------------------
# El exec_() modal no se puede probar (bloquea), asi que se prueba lo que
# decide a donde ir (la forma actual) y el dialogo por separado: carga,
# guardado conjunto y validacion.
#
# OJO: la QApplication tiene que quedar REFERENCIADA mientras dure el modulo
# (fixture con scope module). Si se crea en una funcion y se suelta, CPython
# garbage-collectea el wrapper aunque el objeto C++ siga vivo, y la proxima
# construccion de una vista muere con 0xC0000409 sin backtrace.

import pytest as _pytest


@_pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    aplicacion = QApplication.instance() or QApplication([])
    try:
        from libs.tema import aplicar_tema
        aplicar_tema(aplicacion)
    except Exception:
        pass
    return aplicacion


def test_boton_cuotas_esta_en_la_fila_de_la_lista(app):
    with base_memoria():
        _sembrar_tarjetas()
        from controladores.ABMFormasPago import ABMFormasPagoController
        c = ABMFormasPagoController()
        assert c.view.btnCuotas.text() == "Cuotas"
        c.view.close()


def test_relacion_toma_la_forma_del_detalle_en_edicion(app):
    with base_memoria():
        _sembrar_tarjetas()
        from controladores.ABMFormasPago import ABMFormasPagoController
        c = ABMFormasPagoController()
        c.view.tableView.setCurrentCell(1, 0)  # VISA
        c.view.Modifica()
        assert c._forma_actual() == 3
        c.view.close()


def test_relacion_toma_la_fila_seleccionada_de_la_lista(app):
    with base_memoria():
        _sembrar_tarjetas()
        from controladores.ABMFormasPago import ABMFormasPagoController
        c = ABMFormasPagoController()
        c.view.tableView.setCurrentCell(2, 0)  # MASTERCARD
        assert c._forma_actual() == 4
        c.view.close()


def test_relacion_sin_forma_no_abre_nada(app):
    with base_memoria():
        _sembrar_tarjetas()
        from controladores.ABMFormasPago import ABMFormasPagoController
        c = ABMFormasPagoController()
        assert c._forma_actual() is None
        c.view.close()


def test_dialogo_carga_tarjeta_y_planes(app):
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.CuotasTarjeta import CuotasTarjetaDialog
        dlg = CuotasTarjetaDialog(3)
        assert "VISA" in dlg.windowTitle()
        assert dlg.textDetalle.text() == "VISA"
        assert dlg.gridPlanes.rowCount() == 3
        assert dict((int(dlg.gridPlanes.ObtenerItem(fila=f, col=0)),
                     dlg.gridPlanes.ObtenerItem(fila=f, col=1))
                    for f in range(3)) == {1: Decimal("0"),
                                           3: Decimal("15"),
                                           6: Decimal("25")}
        dlg.close()


def test_dialogo_guarda_tarjeta_y_planes_juntos(app):
    from PyQt5.QtCore import Qt
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.CuotasTarjeta import CuotasTarjetaDialog
        dlg = CuotasTarjetaDialog(3)
        dlg.textDetalle.setText("VISA NUEVA")
        dlg.spinRecargo.setValue(5)
        # El plan de 6 se desactiva, el de 3 cambia de % y se agrega el de 12.
        dlg.gridPlanes.item(2, 2).setCheckState(Qt.Unchecked)
        dlg.gridPlanes.ModificaItem(18, 1, 1)
        dlg.gridPlanes.AgregaItem(items=[12, Decimal("35"), True])
        assert dlg.guardar() is True
        forma = Formapago.get_by_id(3)
        assert forma.detalle == "VISA NUEVA"
        assert float(forma.recargo) == 5
        assert planes_de_forma_pago(3) == [(1, Decimal("0")),
                                           (3, Decimal("18")),
                                           (12, Decimal("35"))]
        dlg.close()


def test_dialogo_fila_rota_no_guarda_nada(app, monkeypatch):
    avisos = []
    import libs.Ventanas as Ventanas
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda *a, **k: avisos.append(a))
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.CuotasTarjeta import CuotasTarjetaDialog
        dlg = CuotasTarjetaDialog(3)
        dlg.gridPlanes.ModificaItem(0, 0, 0)  # 0 cuotas no es un plan
        assert dlg.guardar() is False
        assert avisos, "la fila rota tiene que avisar"
        # No se toco ni la tarjeta ni los planes.
        assert Formapago.get_by_id(3).detalle == "VISA"
        assert planes_de_forma_pago(3) == [(1, Decimal("0")),
                                           (3, Decimal("15")),
                                           (6, Decimal("25"))]
        dlg.close()


def test_plan_inactivo_no_se_ofrece(app):
    with base_memoria():
        _sembrar_tarjetas()
        (CuotaPago.update(activo=False)
         .where((CuotaPago.formapago == 3) & (CuotaPago.cuotas == 3))
         ).execute()
        assert planes_de_forma_pago(3) == [(1, Decimal("0")),
                                           (6, Decimal("25"))]
        # Sin plan vigente para 3 pagos, vale el base (0): el total no cambia.
        rec = recargo_de_plan(3, 3, recargo_base=0)
        total, _, _ = aplicar_forma_pago(Decimal("1000.00"), 0, rec)
        assert total == Decimal("1000.00")


# -- La venta recalcula al cambiar la forma de pago ------------------------
# Con MASTERCARD 6 pagos (28%) el total es la base + 28%; al volver a
# CONTADO tiene que volver a la base sin tocar nada mas. Y entre tarjetas
# se conserva la cuota elegida (VISA 6 -> MASTER 6), con el % de la nueva.

def _venta_con_renglon_base():
    from controladores.VentaSimple import VentaSimpleController
    controller = VentaSimpleController()
    with controller._escribiendo():
        controller.view.gridVenta.AgregaItem(items=[
            "1", "466", "NOTEBOOK", "-", "992333.25", "21", "992333.25",
        ])
    controller.recalcular_total()
    return controller


def _elegir_forma(controller, forma_id):
    idx = controller.view.cboFormaPago.findData(str(forma_id))
    assert idx >= 0, "sin forma {} en el combo".format(forma_id)
    controller.view.cboFormaPago.setCurrentIndex(idx)


def test_cambiar_forma_de_pago_recalcula_el_total(app):
    with base_memoria():
        _sembrar_tarjetas()
        CuotaPago.insert_many([
            {"formapago": 4, "cuotas": 3, "recargo": 18},
            {"formapago": 4, "cuotas": 6, "recargo": 28},
        ]).execute()
        controller = _venta_con_renglon_base()
        try:
            _elegir_forma(controller, 1)
            assert controller.view.textTotal.text() == "992.333,25"

            _elegir_forma(controller, 4)
            idx6 = controller.view.cboCuotas.findData(6)
            assert idx6 >= 0
            controller.view.cboCuotas.setCurrentIndex(idx6)
            assert controller.view.textTotal.text() == "1.270.186,56"

            # Volver a CONTADO: el total vuelve a la base solo.
            _elegir_forma(controller, 1)
            assert controller.view.textTotal.text() == "992.333,25"
        finally:
            controller.view.Cerrar()


def test_cambiar_entre_tarjetas_conserva_la_cuota(app):
    with base_memoria():
        _sembrar_tarjetas()
        CuotaPago.insert_many([
            {"formapago": 4, "cuotas": 3, "recargo": 18},
            {"formapago": 4, "cuotas": 6, "recargo": 28},
        ]).execute()
        controller = _venta_con_renglon_base()
        try:
            _elegir_forma(controller, 3)
            controller.view.cboCuotas.setCurrentIndex(
                controller.view.cboCuotas.findData(6))
            assert controller.view.textTotal.text() == "1.240.416,56"

            # A MASTERCARD: sigue en 6 pagos pero con el 28 % de MASTER.
            _elegir_forma(controller, 4)
            assert controller.view.cboCuotas.currentData() == 6
            assert controller.view.textTotal.text() == "1.270.186,56"
        finally:
            controller.view.Cerrar()


def test_el_total_se_recalcula_aunque_falle_la_carga_de_cuotas(app):
    with base_memoria():
        _sembrar_tarjetas()
        controller = _venta_con_renglon_base()
        try:
            _elegir_forma(controller, 1)
            controller.view.textTotal.setText("0,00")
            controller._cargar_cuotas = lambda: 1 / 0
            # El error sigue visible, pero el total ya quedo recalculado.
            with _pytest.raises(ZeroDivisionError):
                controller._on_forma_pago_changed()
            assert controller.view.textTotal.text() == "992.333,25"
        finally:
            controller.view.Cerrar()


# -- Emitir a consumidor final usa el cliente generico ---------------------
# La factura B necesita un cliente real: con el tilde puesto, la venta
# rapida emite al CONSUMIDOR FINAL de la base en vez de pasar None (que
# caia en "No se ha especificado un cliente valido").

def test_el_generico_es_el_de_la_siembra(app):
    with base_memoria():
        from controladores.venta_simple_cliente import id_cliente_consumidor_final
        assert id_cliente_consumidor_final() == 1


def test_si_el_uno_no_es_cf_busca_por_nombre(app):
    with base_memoria():
        from controladores.venta_simple_cliente import id_cliente_consumidor_final
        from modelos.Clientes import Cliente
        Cliente.update(nombre="OTRO").where(Cliente.idcliente == 1).execute()
        otro = Cliente.create(nombre="CONSUMIDOR FINAL", domicilio="S/N",
                              localidad=1, dni=22222222, tipodocu=0,
                              tiporesp=1, formapago=1, percepcion=1)
        try:
            assert id_cliente_consumidor_final() == otro.idcliente
        finally:
            otro.delete_instance()


def test_sin_generico_no_hay_id(app):
    with base_memoria():
        from controladores.venta_simple_cliente import id_cliente_consumidor_final
        from modelos.Clientes import Cliente
        Cliente.delete_by_id(1)
        assert id_cliente_consumidor_final() is None
