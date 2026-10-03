from pyafipws.wsfev1 import WSFEv1


def test_analizar_evento_unico_de_arca_no_rompe_ultimo_autorizado():
    wsfe = WSFEv1()
    ret = {
        "PtoVta": 3,
        "CbteTipo": 11,
        "CbteNro": 430,
        "Events": {
            "Evt": {
                "Code": 39,
                "Msg": "Condicion Frente al IVA del receptor obligatoria desde 01/09/2026.",
            }
        },
    }

    wsfe._WSFEv1__analizar_errores(ret)

    assert wsfe.Eventos == [
        "39: Condicion Frente al IVA del receptor obligatoria desde 01/09/2026."
    ]
    assert wsfe.ErrMsg == ""


def test_analizar_errores_acepta_lista_clasica():
    wsfe = WSFEv1()
    ret = {
        "Errors": [
            {
                "Err": {
                    "Code": 602,
                    "Msg": "No existen datos en nuestros registros.",
                }
            }
        ]
    }

    wsfe._WSFEv1__analizar_errores(ret)

    assert wsfe.ErrCode == "602"
    assert wsfe.ErrMsg == "602: No existen datos en nuestros registros."


def test_cae_solicitar_acepta_observacion_unica_de_arca():
    class ClienteFalso:
        xml_request = b""
        xml_response = b""

        def FECAESolicitar(self, **kwargs):
            fedetreq = kwargs["FeCAEReq"]["FeDetReq"]
            assert isinstance(fedetreq, dict)
            assert "FECAEDetRequest" in fedetreq
            detalle = fedetreq["FECAEDetRequest"]
            assert detalle["CbteDesde"] == 434
            assert "Iva" not in detalle
            assert "Tributos" not in detalle
            assert "PeriodoAsoc" not in detalle
            assert "Actividades" not in detalle
            return {
                "FECAESolicitarResult": {
                    "FeCabResp": {
                        "Resultado": "A",
                        "PtoVta": 3,
                    },
                    "FeDetResp": [
                        {
                            "FECAEDetResponse": {
                                "Resultado": "A",
                                "CAE": "86227899642737",
                                "CAEFchVto": "20260614",
                                "CbteFch": "20260604",
                                "CbteDesde": 434,
                                "CbteHasta": 434,
                                "Observaciones": {
                                    "Obs": {
                                        "Code": 39,
                                        "Msg": "Aviso informativo de ARCA.",
                                    }
                                },
                            }
                        }
                    ],
                }
            }

    wsfe = WSFEv1()
    wsfe.client = ClienteFalso()
    wsfe.Token = "token"
    wsfe.Sign = "sign"
    wsfe.Cuit = "20233472035"
    wsfe.CrearFactura(
        concepto=1,
        tipo_doc=80,
        nro_doc="30700000000",
        tipo_cbte=11,
        punto_vta=3,
        cbt_desde=434,
        cbt_hasta=434,
        imp_total="100.00",
        imp_tot_conc="0.00",
        imp_neto="100.00",
        imp_iva="0.00",
        imp_trib="0.00",
        imp_op_ex="0.00",
        fecha_cbte="20260604",
        moneda_id="PES",
        moneda_ctz="1.000",
    )

    cae = wsfe.CAESolicitar()

    assert cae == "86227899642737"
    assert wsfe.Obs == "39: Aviso informativo de ARCA."
    assert wsfe.CbteNro == 434


def test_cae_solicitar_acepta_fedetresp_unico_de_arca():
    class ClienteFalso:
        xml_request = b""
        xml_response = b""

        def FECAESolicitar(self, **kwargs):
            return {
                "FECAESolicitarResult": {
                    "FeCabResp": {
                        "Resultado": "R",
                        "PtoVta": 3,
                    },
                    "FeDetResp": {
                        "FECAEDetResponse": {
                            "Resultado": "R",
                            "CAE": "",
                            "CAEFchVto": "",
                            "CbteFch": "20260604",
                            "CbteDesde": 434,
                            "CbteHasta": 434,
                            "Observaciones": {
                                "Obs": [
                                    {
                                        "Code": 10071,
                                        "Msg": "Para comprobantes tipo C el objeto IVA no debe informarse.",
                                    },
                                    {
                                        "Code": 10024,
                                        "Msg": "Si ImpTrib es igual a 0 el objeto Tributos y Tributo no deben informarse.",
                                    },
                                ]
                            },
                        }
                    },
                }
            }

    wsfe = WSFEv1()
    wsfe.client = ClienteFalso()
    wsfe.Token = "token"
    wsfe.Sign = "sign"
    wsfe.Cuit = "20233472035"
    wsfe.CrearFactura(
        concepto=2,
        tipo_doc=80,
        nro_doc="30711151202",
        tipo_cbte=11,
        punto_vta=3,
        cbt_desde=434,
        cbt_hasta=434,
        imp_total="94682.00",
        imp_tot_conc="0.00",
        imp_neto="94682.00",
        imp_iva="0.00",
        imp_trib="0.00",
        imp_op_ex="0.00",
        fecha_cbte="20260604",
        fecha_venc_pago="20260604",
        fecha_serv_desde="20260601",
        fecha_serv_hasta="20260630",
        moneda_id="PES",
        moneda_ctz="1.000",
    )

    cae = wsfe.CAESolicitar()

    assert cae == ""
    assert wsfe.Resultado == "R"
    assert "10071: Para comprobantes tipo C el objeto IVA no debe informarse." in wsfe.Obs
    assert "10024: Si ImpTrib es igual a 0 el objeto Tributos y Tributo no deben informarse." in wsfe.Obs
