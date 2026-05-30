import sys


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
