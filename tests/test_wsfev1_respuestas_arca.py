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
