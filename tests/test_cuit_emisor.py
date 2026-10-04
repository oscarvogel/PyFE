"""El CUIT emisor, en un solo lugar.

Por que esta prueba existe
---------------------------
El CUIT vivia en dos claves: [FACTURA] cuit, que edita el usuario en
Configuracion, y [WSFEv1] cuit, que es la que viaja a ARCA en Auth.Cuit. El
asistente escribia la primera y nadie escribia la segunda, asi que una
instalacion nueva quedaba con '00000000000' y no podia emitir. El diagnostico
tampoco lo detectaba, porque 00000000000 no esta vacio.

Estos tests fijan la regla de decision completa, incluso el caso incomodo: dos
CUIT reales y distintos, donde no se elige uno.
"""

import pytest

from libs import instalacion

# El CUIT del certificado de homologacion que usa tools/probar_emision.py.
REAL = "20233472035"
REAL_2 = "20123456786"
CON_GUIONES = "20-23347203-5"
RELLENO = "00000000000"


def _leer(**valores):
    """Devuelve un LeerIni falso. Sin valor, devuelve '' como el real."""
    def leer(clave=None, key=None, carpeta=""):
        return valores.get("{}.{}".format(key or "param", clave), "")
    return leer


class _Grabo:
    def __init__(self):
        self.escrito = {}

    def __call__(self, clave, key, valor):
        self.escrito["{}.{}".format(key, clave)] = valor


# -- cuit_es_real -----------------------------------------------------------

def test_un_cuit_con_guiones_es_real():
    assert instalacion.cuit_es_real(CON_GUIONES) is True


def test_sin_guiones_tambien_es_real():
    # Asi es como lo guarda la herramienta de pruebas y como lo espera ARCA.
    assert instalacion.cuit_es_real(REAL) is True


def test_ceros_no_es_un_cuit():
    """El caso que rompia todo: 00000000000 tiene digito verificador valido.

    Sin esta comprobacion pasaba por un CUIT real y el diagnostico daba verde
    en una instalacion que no podia emitir.
    """
    assert instalacion.cuit_es_real(RELLENO) is False
    assert instalacion.cuit_es_real("0000000000") is False


@pytest.mark.parametrize("valor", ["", None, "Razon Social", "20-1234", "abcdefghijk"])
def test_texto_que_no_es_cuit_no_pasa(valor):
    assert instalacion.cuit_es_real(valor) is False


def test_cuit_con_digito_verificador_malo_no_pasa():
    assert instalacion.cuit_es_real("20-23347203-4") is False


# -- cuit_emisor ------------------------------------------------------------

def test_devuelve_el_de_la_empresa_solo_digitos():
    leer = _leer(**{"FACTURA.cuit": CON_GUIONES, "WSFEv1.cuit": REAL})
    assert instalacion.cuit_emisor(leer=leer) == REAL


def test_cae_en_el_de_facturacion_cuando_la_empresa_no_tiene():
    """Instalacion vieja: el dato real solo estaba en [WSFEv1]."""
    leer = _leer(**{"FACTURA.cuit": "", "WSFEv1.cuit": REAL})
    assert instalacion.cuit_emisor(leer=leer) == REAL


def test_ignora_el_valor_de_relleno():
    leer = _leer(**{"FACTURA.cuit": CON_GUIONES, "WSFEv1.cuit": RELLENO})
    assert instalacion.cuit_emisor(leer=leer) == REAL


def test_devuelve_vacio_y_no_ceros_si_no_hay_cuit_utilizable():
    leer = _leer(**{"FACTURA.cuit": RELLENO, "WSFEv1.cuit": RELLENO})
    assert instalacion.cuit_emisor(leer=leer) == ""


# -- normalizar_cuit_emisor -------------------------------------------------

def test_completa_wsfe_con_el_cuit_de_la_empresa():
    """El caso de una instalacion nueva: la clave de facturacion es la buena."""
    grabar = _Grabo()
    leer = _leer(**{"FACTURA.cuit": CON_GUIONES, "WSFEv1.cuit": RELLENO})

    r = instalacion.normalizar_cuit_emisor(grabar=grabar, leer=leer)

    assert r["estado"] == "ok"
    assert r["cuit"] == REAL
    assert grabar.escrito["WSFEv1.cuit"] == REAL


def test_completa_factura_con_el_cuit_de_facturacion():
    """Al reves: una base vieja con el dato solo en [WSFEv1]."""
    grabar = _Grabo()
    leer = _leer(**{"FACTURA.cuit": "", "WSFEv1.cuit": REAL})

    r = instalacion.normalizar_cuit_emisor(grabar=grabar, leer=leer)

    assert r["estado"] == "ok"
    assert grabar.escrito["FACTURA.cuit"] == CON_GUIONES


def test_no_toca_nada_si_ya_coinciden():
    grabar = _Grabo()
    leer = _leer(**{"FACTURA.cuit": CON_GUIONES, "WSFEv1.cuit": REAL})

    r = instalacion.normalizar_cuit_emisor(grabar=grabar, leer=leer)

    assert r["estado"] == "nada"
    assert grabar.escrito == {}


def test_dos_cuit_reales_distintos_no_elige_ninguno():
    """Acá no hay forma de saber cual es el bueno.

    Elegir uno seria descartar el otro en silencio, y en un sistema que factura
    eso no se decide solo: se avisa y lo muestra el chequeo de instalacion.
    """
    grabar = _Grabo()
    leer = _leer(**{"FACTURA.cuit": CON_GUIONES, "WSFEv1.cuit": REAL_2})

    r = instalacion.normalizar_cuit_emisor(grabar=grabar, leer=leer)

    assert r["estado"] == "discrepan"
    assert r["cuit"] == REAL
    assert REAL_2 in r["conflicto"]
    assert grabar.escrito == {}


def test_sin_cuit_no_escribe_nada():
    grabar = _Grabo()
    leer = _leer(**{"FACTURA.cuit": RELLENO, "WSFEv1.cuit": ""})

    r = instalacion.normalizar_cuit_emisor(grabar=grabar, leer=leer)

    assert r["estado"] == "falta"
    assert r["cuit"] == ""
    assert grabar.escrito == {}


# -- ida y vuelta con el asistente -----------------------------------------

def test_ida_y_vuelta_por_el_ini_real(tmp_path, monkeypatch):
    """El ciclo completo: escribe de verdad y vuelve a leer.

    Sin esto los tests de arriba prueban el helper con dobles, y no que lo que
    escribe el asistente sea lo que despues lee la app.
    """
    monkeypatch.chdir(tmp_path)
    import libs.Utiles as U

    instalacion.guardar_config_inicial({
        "base": "sqlite", "empresa": "Mi Empresa", "cuit": CON_GUIONES})

    # El asistente escribe [FACTURA] cuit y nada mas.
    assert U.LeerIni(clave="cuit", key="FACTURA") == CON_GUIONES
    # [WSFEv1] cuit sigue con el valor de la plantilla: no lo escribe nadie.
    assert U.LeerIni(clave="cuit", key="WSFEv1") != REAL

    r = instalacion.normalizar_cuit_emisor()
    assert r["estado"] == "ok"
    assert U.LeerIni(clave="cuit", key="WSFEv1") == REAL
    assert instalacion.cuit_emisor() == REAL


def test_el_asistente_no_escribe_la_clave_de_facturacion():
    """La clave vieja se completa en un solo lugar: el normalizador.

    Se comprueban las dos mitades: que [FACTURA] cuit si se escriba (si no,
    el test pasaria en verde porque no encuentra nada que buscar) y que
    [WSFEv1] cuit no.
    """
    grabo = _Grabo()
    instalacion.guardar_config_inicial(
        {"base": "sqlite", "empresa": "Mi Empresa", "cuit": CON_GUIONES},
        escribir=grabo)
    assert grabo.escrito["FACTURA.cuit"] == CON_GUIONES
    assert "WSFEv1.cuit" not in grabo.escrito
