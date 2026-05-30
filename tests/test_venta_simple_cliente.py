from controladores.venta_simple_cliente import cliente_consumidor_final


def test_cliente_consumidor_final_tiene_datos_minimos_para_afip():
    cliente = cliente_consumidor_final()

    assert cliente.nombre == "Consumidor Final"
    assert cliente.documento == ""
    assert cliente.tipo_doc_afip == 99
    assert cliente.es_consumidor_final is True
