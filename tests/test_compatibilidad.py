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
