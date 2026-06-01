# coding=utf-8
import builtins
import hashlib
import ssl


_md5_original = hashlib.md5


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

    wsdl_parse_original = SoapClient.wsdl_parse

    def wsdl_parse_sin_cache_pickle(self, url, cache=False):
        return wsdl_parse_original(self, url, cache=False)

    wsdl_parse_sin_cache_pickle._pyfe_sin_cache_pickle = True
    SoapClient.wsdl_parse = wsdl_parse_sin_cache_pickle
