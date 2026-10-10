"""Factura con diseno moderno (HTML + Qt).

Se prueba sin base y sin ARCA: los datos entran como atributos (igual que
la muestra de DisenoComprobante) y el PDF se genera offscreen. Lo que se
fija aca es el contrato: que campos salen, que todo texto va escapado y
que el camino viejo sigue siendo el default.
"""
import datetime
import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class Atributos(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


def _cliente_cf():
    return Atributos(
        idcliente=1, nombre="CONSUMIDOR FINAL", cuit="0", dni=11111111,
        domicilio="S/NOMBRE",
        tiporesp=Atributos(idtiporesp=3, nombre="CONSUMIDOR FINAL",
                           condicion_iva_receptor_id=5),
        localidad=Atributos(nombre="Puerto Rico", provincia="Misiones"),
        percepcion=Atributos(detalle="SIN PERCEPCION", porcentaje=Decimal("0")),
    )


def _cabecera(**cambios):
    datos = dict(
        tipocomp=Atributos(codigo=11, nombre="FACTURA C", letra="C"),
        cliente=_cliente_cf(), numero="00001-00000102",
        fecha=datetime.date(2026, 10, 10), concepto=1, nombre="",
        domicilio="",
        total=Decimal("11141.70"), neto=Decimal("11141.70"),
        iva=Decimal("0.00"), percepciondgr=Decimal("0.00"),
        netoa=Decimal("0"), netob=Decimal("0"),
        descuento=Decimal("0"), recargo=Decimal("0"),
        cae="86410982615987", venccae=datetime.date(2026, 10, 20),
        desde=datetime.date(2026, 10, 10),
        formapago=Atributos(detalle="CONTADO"), cuotapago=1,
    )
    datos.update(cambios)
    return Atributos(**datos)


def _renglon(detalle="CARGADOR 45W", cantidad="2", precio="5570.85"):
    return Atributos(
        idarticulo=Atributos(idarticulo=185), descad=detalle,
        cantidad=Decimal(cantidad), precio=Decimal(precio),
        tipoiva=Atributos(iva=Decimal("21")), montoiva=Decimal("0"))


def test_datos_consumidor_final_llevan_dni():
    from controladores.FacturaHTML import datos_comprobante

    datos = datos_comprobante(_cabecera(), [_renglon()])

    assert datos["letra"] == "C"
    assert datos["recep_doc_label"] == "DNI"
    assert datos["recep_doc"] == "11111111"
    assert datos["tipo_doc"] == 96
    assert datos["forma_pago"] == "CONTADO"
    assert len(datos["items"]) == 1
    assert datos["items"][0]["codigo"] == "185"


def test_datos_con_cuotas_dicen_los_pagos():
    from controladores.FacturaHTML import datos_comprobante

    cab = _cabecera(formapago=Atributos(detalle="VISA"), cuotapago=3)
    datos = datos_comprobante(cab, [_renglon()])

    assert datos["forma_pago"] == "VISA 3 pagos"


def test_datos_sin_tipo_letra_sale_del_codigo():
    from controladores.FacturaHTML import datos_comprobante

    cab = _cabecera(tipocomp=Atributos(codigo=6, nombre="FACTURA B"))
    datos = datos_comprobante(cab, [])

    assert datos["letra"] == "B"


def test_html_resuelve_todo_y_escapa():
    from controladores.FacturaHTML import datos_comprobante, html_comprobante

    cab = _cabecera()
    datos = datos_comprobante(cab, [_renglon(detalle="CABLE <X> $500")])
    contenido = html_comprobante(datos)

    assert "$total" not in contenido
    assert "11.141,70" in contenido
    assert "86410982615987" in contenido
    # El nombre del producto va como texto, no como tag, y el $ queda.
    assert "CABLE &lt;X&gt; $500" in contenido


def test_html_sin_items_no_revienta():
    from controladores.FacturaHTML import datos_comprobante, html_comprobante

    contenido = html_comprobante(datos_comprobante(_cabecera(), []))

    assert "$filas_items" not in contenido


def test_generar_pdf_es_un_pdf_valido(tmp_path):
    from controladores.FacturaHTML import (datos_comprobante, generar_pdf,
                                          html_comprobante)

    datos = datos_comprobante(_cabecera(), [_renglon()])
    salida = str(tmp_path / "moderna.pdf")
    generar_pdf(html_comprobante(datos), salida)

    with open(salida, "rb") as fh:
        assert fh.read(5) == b"%PDF-"


def test_imprimir_html_devuelve_la_ruta(tmp_path, monkeypatch):
    import controladores.FacturaHTML as FH

    # Sin logo ni QR: lo que se prueba es el armado, no los recursos.
    monkeypatch.setattr(FH, "_logo_ruta", lambda: ("", False))
    monkeypatch.setattr(FH, "_qr_ruta", lambda datos: "")

    salida = str(tmp_path / "fc.pdf")
    ok, ruta = FH.imprimir_html(_cabecera(), salida=salida, mostrar=False,
                                renglones=[_renglon()])

    assert ok is True
    assert ruta == salida
    assert os.path.isfile(salida)


def test_imprimir_html_sin_plantilla_cae_al_viejo(tmp_path, monkeypatch):
    import controladores.FacturaHTML as FH

    monkeypatch.setattr(FH, "PLANTILLA", "no-existe.html")

    ok, ruta = FH.imprimir_html(_cabecera(), salida=str(tmp_path / "x.pdf"),
                                mostrar=False, renglones=[_renglon()])

    assert (ok, ruta) == (False, None)


def test_el_diseno_moderno_viene_apagado(monkeypatch):
    from modelos.ParametrosSistema import ParamSist

    import controladores.FacturaHTML as FH

    monkeypatch.setattr(ParamSist, "ObtenerParametro",
                        lambda *a, **k: k.get("valor_defecto", ""))
    assert FH.usar_factura_html() is False

    monkeypatch.setattr(ParamSist, "ObtenerParametro", lambda *a, **k: "S")
    assert FH.usar_factura_html() is True


def test_renglones_desde_base_sin_id_no_revienta():
    from controladores.FacturaHTML import _renglones_desde_base

    assert _renglones_desde_base(None) == []
    assert _renglones_desde_base(999999999) == []


def test_logo_grande_se_encaja_sin_deformar(tmp_path, monkeypatch):
    from PIL import Image

    import controladores.FacturaHTML as FH
    from controladores import FacturaBranding

    # Un logo alto como el real: si entra tal cual se come la hoja.
    origen = str(tmp_path / "logo_alto.png")
    Image.new("RGB", (500, 400), "white").save(origen)
    marca = Atributos(logo=origen)
    monkeypatch.setattr(FacturaBranding, "cargar_config_marca_factura",
                        lambda: marca)

    ruta, borrar = FH._logo_ruta()

    try:
        assert ruta and ruta != origen
        with Image.open(ruta) as copia:
            assert max(copia.size) <= 320
            # Misma proporcion: no se deforma.
            assert abs(copia.size[0] / copia.size[1] - 500 / 400) < 0.01
    finally:
        if borrar:
            os.remove(ruta)


def test_logo_chico_se_usa_tal_cual(tmp_path, monkeypatch):
    from PIL import Image

    import controladores.FacturaHTML as FH
    from controladores import FacturaBranding

    origen = str(tmp_path / "logo_chico.png")
    Image.new("RGB", (200, 100), "white").save(origen)
    marca = Atributos(logo=origen)
    monkeypatch.setattr(FacturaBranding, "cargar_config_marca_factura",
                        lambda: marca)

    ruta, borrar = FH._logo_ruta()

    assert borrar is False
    assert ruta.replace("/", os.sep) == origen
