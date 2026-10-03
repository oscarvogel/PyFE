"""Tests de la migracion gradual del password de la base.

Lo que se verifica aca es que una instalacion existente NO se rompe:
las tres formas de guardar el secreto tienen que seguir leyendose.
"""

import base64
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cryptography.fernet import Fernet

from libs import secretos


def leer_falso(mapa):
    """Devuelve un LeerIni de mentira sobre un dict, para no tocar el ini real."""
    return lambda clave=None, key='param': mapa.get("{}|{}".format(key, clave), "")


class GraboFalso:
    """Registra lo que se escribe y lo que se borra."""

    def __init__(self):
        self.escritos = {}
        self.borrados = []

    def escribir(self, clave, key, valor):
        self.escritos["{}|{}".format(key, clave)] = valor

    def borrar(self, clave, key):
        self.borrados.append("{}|{}".format(key, clave))


@pytest.fixture(autouse=True)
def sesion_limpia():
    secretos.limpiar_sesion()
    yield
    secretos.limpiar_sesion()


# --- 1. Las tres formas se siguen leyendo --------------------------------
def test_esquema_viejo_sigue_leyendose():
    # Exactamente como esta instalado hoy: cifrado + clave al lado.
    clave = Fernet.generate_key()
    mapa = {
        "param|password": Fernet(clave).encrypt(b"root").decode(),
        "param|key": clave.decode(),
    }
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) == "root"


def test_forma_fernet_nueva_sigue_leyendose():
    clave = Fernet.generate_key()
    valor = (secretos.PREFIXO_FERNET
             + base64.b64encode(Fernet(clave).encrypt(b"root")).decode())
    mapa = {"param|password": valor, "param|key": clave.decode()}
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) == "root"


@pytest.mark.skipif(not secretos.disponible_dpapi(),
                    reason="DPAPI solo existe en Windows")
def test_forma_dpapi_sigue_leyendose():
    mapa = {"param|password": secretos.cifrar("root")}
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) == "root"


# --- 2. Casos que tienen que pedir el dato, no romper --------------------
@pytest.mark.parametrize("mapa", [
    {},                                            # no hay nada
    {"param|password": ""},                        # vacio
    {"param|password": "   "},                     # espacios
    {"param|password": "basura"},                  # ilegible
    {"param|password": "dpapi:v1:@@@no-base64@@@"},  # corrupto
])
def test_cuando_no_se_puede_leer_devuelve_none(mapa):
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) is None


# --- 3. La cache de sesion tiene prioridad sobre el ini ------------------
def test_la_sesion_gana_sobre_el_ini():
    clave = Fernet.generate_key()
    mapa = {
        "param|password": Fernet(clave).encrypt(b"viejo").decode(),
        "param|key": clave.decode(),
    }
    secretos.guardar_en_sesion("password_base", "nuevo")
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) == "nuevo"


# --- 4. Guardar migra y BORRA la clave vieja -----------------------------
@pytest.mark.skipif(not secretos.disponible_dpapi(),
                    reason="DPAPI solo existe en Windows")
def test_guardar_migra_a_dpapi_y_borra_la_clave():
    g = GraboFalso()
    resultado = secretos.persistir_password_base(
        "root", escribir=g.escribir, borrar=g.borrar)

    assert resultado == "dpapi"
    assert g.escritos["param|password"].startswith(secretos.PREFIXO_DPAPI)
    # lo importante: la clave Fernet vieja no queda dando vueltas
    assert "param|key" in g.borrados
    assert "param|key" not in g.escritos
    # y lo guardado se puede volver a leer
    assert secretos.descifrar(g.escritos["param|password"]) == "root"


def test_guardar_en_otro_so_deja_fernet_consistente():
    g = GraboFalso()
    resultado = secretos.persistir_password_base(
        "root", escribir=g.escribir, borrar=g.borrar)

    # Con DPAPI disponible queda dpapi; sin el, tiene que quedar coherente.
    if resultado == "dpapi":
        assert g.escritos["param|password"].startswith(secretos.PREFIXO_DPAPI)
    else:
        assert g.escritos["param|password"].startswith(secretos.PREFIXO_FERNET)
        assert g.escritos["param|key"]
        assert "param|key" not in g.borrados

    assert secretos.descifrar(
        g.escritos["param|password"], g.escritos.get("param|key")) == "root"


# --- 5. Ida y vuelta: guardar y volver a leer ---------------------------
@pytest.mark.skipif(not secretos.disponible_dpapi(),
                    reason="DPAPI solo existe en Windows")
def test_ida_y_vuelta_completa():
    g = GraboFalso()
    secretos.persistir_password_base("clave-larga-con-acentos-ñ",
                                     escribir=g.escribir, borrar=g.borrar)
    mapa = {"param|password": g.escritos["param|password"]}
    assert secretos.resolver_password_base(leer=leer_falso(mapa)) == \
        "clave-larga-con-acentos-ñ"


# --- 6. Escribo a un ini real de verdad (integracion) --------------------
# OJO: LeerIni y GrabarIni resuelven la ruta con os.getcwd(), asi que la
# unica forma segura de probar la escritura es correr en un directorio
# temporal. Parchear el argparse NO alcanza: si el parche no aplica, el
# test escribe sobre el sistema.ini de la maquina y no falla, lo pisa.
def _ini_temporal(tmp_path, contenido):
    ruta = tmp_path / "sistema.ini"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_grabarini_borra_la_clave(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini_temporal(tmp_path, "[param]\npassword = x\nkey = y\notra = z\n")

    import libs.Utiles as U
    U.GrabarIni(clave="key", key="param", borrar=True)

    texto = (tmp_path / "sistema.ini").read_text(encoding="utf-8")
    assert "key =" not in texto
    # lo demas sigue intacto
    assert "password = x" in texto
    assert "otra = z" in texto


def test_grabarini_sigue_escribiendo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini_temporal(tmp_path, "[param]\npassword = x\n")

    import libs.Utiles as U
    U.GrabarIni(clave="nuevo", key="param", valor="valor")

    assert "nuevo = valor" in (tmp_path / "sistema.ini").read_text(encoding="utf-8")


def test_los_tests_no_tocan_el_ini_de_la_maquina(tmp_path, monkeypatch):
    """Guardia: escribe en un temporal y comprueba que el archivo real
    de la instalacion quedo exactamente como estaba."""
    from libs.instalacion import ruta_config
    real = ruta_config()
    import os as _os
    antes = _os.path.getmtime(real) if _os.path.exists(real) else None

    monkeypatch.chdir(tmp_path)
    _ini_temporal(tmp_path, "[param]\nbase = sqlite\n")
    import libs.Utiles as U
    U.GrabarIni(clave="base", key="param", valor="otro")

    despues = _os.path.getmtime(real) if _os.path.exists(real) else None
    assert antes == despues, "un test escribio sobre el sistema.ini real"
