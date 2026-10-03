# coding=utf-8
import builtins
import functools
import hashlib
import inspect
import ssl


_md5_original = hashlib.md5


def _wsdl_parse_sin_cache_pickle(original):
    """Envuelve a `wsdl_parse` para que nunca deje el pickle de cache.

    Por que hace falta un envoltorio y no alcanza con llamar con `cache=False`:
    la firma de `wsdl_parse` cambia entre versiones de pysimplesoap, y el
    shim tiene que aguantar la que este instalada.

    La que hay ahora es `(self, url, debug=False, cache=False)`; la que se
    enfrentaba antes no tenia `debug`. Un shim con la firma fija rompia con
    `TypeError` apenas se llamaba, y la llamada ocurre al construir el cliente
    SOAP, o sea al emitir: la app entera no podia facturar. Y no lo
    denunciaba ningun test, porque el test miraba que el shim estuviera
    instalado y no lo llamaba nunca.
    """
    # Si `cache` llega como posicional hay que sacarlo antes de pasarlo por
    # keyword, o Python complains de "valor repetido". En que posicion esta se
    # mira de la firma instalada en vez de suponerlo.
    parametros = list(inspect.signature(original).parameters)
    cache_es_el_ultimo = bool(parametros) and parametros[-1] == "cache"

    @functools.wraps(original)
    def wsdl_parse_sin_cache_pickle(self, url, *args, **kwargs):
        # `url` va declarado, no dentro de *args: si fuera parte de *args,
        # "sacar el ultimo" se llevaria la url en vez del cache.
        kwargs.pop("cache", None)
        if args and cache_es_el_ultimo:
            args = args[:-1]
        kwargs["cache"] = False
        return original(self, url, *args, **kwargs)

    wsdl_parse_sin_cache_pickle._pyfe_sin_cache_pickle = True
    return wsdl_parse_sin_cache_pickle


def aplicar_compatibilidad_pysimplesoap():
    if not hasattr(builtins, "basestring"):
        builtins.basestring = str

    if getattr(hashlib.md5, "_pyfe_acepta_texto", False):
        return

    def md5_compatible(data=b"", *args, **kwargs):
        if isinstance(data, str):
            data = data.encode("utf-8")
        return _md5_original(data, *args, **kwargs)

    md5_compatible._pyfe_acepta_texto = True
    hashlib.md5 = md5_compatible

    try:
        from pysimplesoap.client import SoapClient
        import pysimplesoap.transport as transport
        import httplib2
    except ImportError:
        return

    if not hasattr(httplib2, "SSLHandshakeError"):
        httplib2.SSLHandshakeError = ssl.SSLError

    try:
        import http.client

        if hasattr(transport, "orig__init__"):
            http.client.HTTPSConnection.__init__ = transport.orig__init__
    except Exception:
        pass

    if hasattr(transport, "Httplib2Transport") and not getattr(
        transport.Httplib2Transport.__init__, "_pyfe_version_httplib2_ok", False
    ):
        def httplib2_transport_init(self, timeout, proxy=None, cacert=None, sessions=False):
            kwargs = {
                "timeout": timeout,
                "disable_ssl_certificate_validation": cacert is None,
                "ca_certs": cacert,
            }
            if proxy:
                import socks

                kwargs["proxy_info"] = httplib2.ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP, **proxy)
            httplib2.Http.__init__(self, **kwargs)

        httplib2_transport_init._pyfe_version_httplib2_ok = True
        transport.Httplib2Transport.__init__ = httplib2_transport_init

    if getattr(SoapClient.wsdl_parse, "_pyfe_sin_cache_pickle", False):
        return

    SoapClient.wsdl_parse = _wsdl_parse_sin_cache_pickle(SoapClient.wsdl_parse)
