import base64
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from libs import secretos
from libs.secretos import SecretoIlegible


# --- DPAPI: roundtrip y fallos -------------------------------------------
solo_si_dpapi = pytest.mark.skipif(
    not secretos.disponible_dpapi(), reason="DPAPI solo existe en Windows"
)


@solo_si_dpapi
def test_dpapi_roundtrip():
    valor = secretos.cifrar("clave-de-prueba")
    assert valor.startswith(secretos.PREFIXO_DPAPI)
    assert secretos.descifrar(valor) == "clave-de-prueba"


@solo_si_dpapi
def test_dpapi_sobrevive_acentos_y_largo():
    texto = "contraseña con acentos: áéíóú ñ ¿? " * 20
    assert secretos.descifrar(secretos.cifrar(texto)) == texto


@pytest.mark.parametrize("basura", [
    "",
    "   ",
    "no soy un blob",
    "dpapi:v1:",
    "dpapi:v1:!!!!no-es-base64!!!!",
    "dpapi:v1:" + base64.b64encode(b"\x00" * 64).decode(),
    "dpapi:v1:" + base64.b64encode(b"corto").decode(),
])
def test_valores_basura_no_revientan(basura):
    # Regla 1: un valor roto nunca puede tumbar la app.
    assert secretos.esta_legible(basura) is False
    with pytest.raises(SecretoIlegible):
        secretos.descifrar(basura)


@solo_si_dpapi
def test_payload_corrupto_se_detecta():
    valor = secretos.cifrar("secreto")
    bruto = bytearray(base64.b64decode(valor[len(secretos.PREFIXO_DPAPI):]))
    # al final esta el payload autenticado
    bruto[-1] ^= 0xFF
    corrupto = secretos.PREFIXO_DPAPI + base64.b64encode(bytes(bruto)).decode()
    assert secretos.esta_legible(corrupto) is False


def test_none_no_revienta():
    assert secretos.esta_legible(None) is False
    with pytest.raises(SecretoIlegible):
        secretos.descifrar(None)


# --- Versionado gradual: el esquema viejo sigue funcionando ---------------
def test_esquema_historico_sigue_leyendose():
    # Exactamente lo que hay instalado hoy: 'password' cifrado + 'key' al lado.
    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    cifrado = Fernet(clave).encrypt(b"root")
    assert secretos.descifrar(cifrado.decode(), clave) == "root"
    assert secretos.esta_legible(cifrado.decode(), clave) is True


def test_fernet_con_prefijo_nuevo():
    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    bruto = Fernet(clave).encrypt(b"root")
    valor = secretos.PREFIXO_FERNET + base64.b64encode(bruto).decode()
    assert secretos.descifrar(valor, clave) == "root"


def test_fernet_sin_clave_falla_limpiamente():
    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    valor = secretos.PREFIXO_FERNET + base64.b64encode(
        Fernet(clave).encrypt(b"root")).decode()
    assert secretos.esta_legible(valor) is False


def test_clave_incorrecta_no_devuelve_el_secreto():
    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    otra = Fernet.generate_key()
    valor = secretos.PREFIXO_FERNET + base64.b64encode(
        Fernet(clave).encrypt(b"root")).decode()
    with pytest.raises(SecretoIlegible):
        secretos.descifrar(valor, otra)


# --- El error nunca incluye el secreto ------------------------------------
def test_el_error_no_filtra_el_secreto():
    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    valor = secretos.PREFIXO_FERNET + base64.b64encode(
        Fernet(clave).encrypt(b"clave-muy-secreta")).decode()
    with pytest.raises(SecretoIlegible) as ex:
        secretos.descifrar(valor, Fernet.generate_key())
    assert "clave-muy-secreta" not in str(ex.value)


# --- Cache de sesion ------------------------------------------------------
def test_cache_de_sesion():
    secretos.limpiar_sesion()
    assert secretos.obtener_de_sesion("password") is None
    secretos.guardar_en_sesion("password", "root")
    assert secretos.obtener_de_sesion("password") == "root"
    secretos.limpiar_sesion()
    assert secretos.obtener_de_sesion("password") is None


# --- Regla 2: DPAPI no se puede llamar por lectura ------------------------
@solo_si_dpapi
def test_dpapi_no_es_lento_en_cantidad():
    # Si esto se llamara por cada LeerIni (171 por operacion) se sentiria
    # como un cuelgue. Se mide para que un cambio futuro lo detecte.
    import time

    t = time.perf_counter()
    for _ in range(200):
        secretos.descifrar(secretos.cifrar("x"))
    elapsed = (time.perf_counter() - t) * 1000
    assert elapsed < 3000, "200 roundtrip tardaron {:.0f} ms".format(elapsed)
