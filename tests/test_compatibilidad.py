import hashlib


def test_compatibilidad_pysimplesoap_permite_md5_con_texto():
    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

    aplicar_compatibilidad_pysimplesoap()

    assert hashlib.md5("https://wsaahomo.afip.gov.ar/ws/services/LoginCms").hexdigest()


def test_compatibilidad_pysimplesoap_define_basestring():
    import builtins

    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

    aplicar_compatibilidad_pysimplesoap()

    assert builtins.basestring is str


def test_compatibilidad_pysimplesoap_desactiva_cache_pickle_wsdl():
    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap
    from pysimplesoap.client import SoapClient

    aplicar_compatibilidad_pysimplesoap()

    assert getattr(SoapClient.wsdl_parse, "_pyfe_sin_cache_pickle", False) is True


def test_el_shim_de_wsdl_acepta_como_lo_llama_la_version_instalada():
    """El bug que media la app entera: no se podia emitir UNA factura.

    `SoapClient.__init__` de la version instalada llama
    `self.wsdl_parse(wsdl, debug=trace, cache=cache)`, y el shim declaraba
    `(self, url, cache=False)`: TypeError con `debug` inesperado, al construir
    el cliente SOAP, o sea al emitir.

    El test anterior solo miraba que el shim estuviera instalado y por eso la
    suite entera pasaba con la facturacion rota. Este mira que la firma
    aguante la llamada real, sin tocar la red.
    """
    import inspect

    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap
    from pysimplesoap.client import SoapClient

    aplicar_compatibilidad_pysimplesoap()

    # La llamada tal cual la hace SoapClient.__init__.
    inspect.signature(SoapClient.wsdl_parse).bind(
        object(), "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
        debug=True, cache=True)


def test_el_shim_de_wsdl_apaga_el_cache_y_deja_pasar_el_resto():
    """El shim tiene que apagar el cache y no comerse ningun otro argumento.

    Cada version de pysimplesoap mete sus propios keywords; el que no conoce no
    puede romper la facturacion.
    """
    from libs.Compatibilidad import _wsdl_parse_sin_cache_pickle

    recibidos = {}

    def original(self, url, debug=False, cache=False):
        recibidos.update(url=url, debug=debug, cache=cache)
        return "wsdl"

    shim = _wsdl_parse_sin_cache_pickle(original)

    # Cache apagado aunque venga True, y el resto de los argumentos pasan.
    assert shim(None, "https://x?WSDL", debug=True, cache=True) == "wsdl"
    assert recibidos["cache"] is False
    assert recibidos["debug"] is True
    assert recibidos["url"] == "https://x?WSDL"

    # Y con el cache pedido por keyword, que es como lo pasa SoapClient.
    shim(None, "https://x?WSDL", cache=True)
    assert recibidos["cache"] is False


def test_el_shim_aguanta_el_cache_por_posicional():
    """Con una firma como la de antes, el cache llega en posicion y hay que
    sacarlo antes de pasarlo por keyword, o Python se queja de valor
    repetido."""
    from libs.Compatibilidad import _wsdl_parse_sin_cache_pickle

    recibidos = {}

    def original_antigua(self, url, cache=False):
        recibidos.update(url=url, cache=cache)
        return "wsdl"

    shim = _wsdl_parse_sin_cache_pickle(original_antigua)
    assert shim(None, "https://x?WSDL", True) == "wsdl"
    assert recibidos["cache"] is False
    # La url tiene que seguir llegando: si el shim se come el ultimo argumento
    # equivocado, esto se rompe.
    assert recibidos["url"] == "https://x?WSDL"


def test_compatibilidad_pysimplesoap_restaurar_httpsconnection():
    import http.client

    import pysimplesoap.transport as transport
    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

    aplicar_compatibilidad_pysimplesoap()

    if hasattr(transport, "orig__init__"):
        assert http.client.HTTPSConnection.__init__ is transport.orig__init__


def test_compatibilidad_pysimplesoap_corrige_transporte_httplib2():
    import pysimplesoap.transport as transport
    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

    aplicar_compatibilidad_pysimplesoap()

    assert getattr(transport.Httplib2Transport.__init__, "_pyfe_version_httplib2_ok", False) is True


def test_compatibilidad_pysimplesoap_define_ssl_handshake_error():
    import httplib2

    from libs.Compatibilidad import aplicar_compatibilidad_pysimplesoap

    aplicar_compatibilidad_pysimplesoap()

    assert hasattr(httplib2, "SSLHandshakeError")
