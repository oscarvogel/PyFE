"""Regresion del monkeypatch de pyafipws sobre ConfigParser.

pyafipws/utils.py reemplaza, a nivel global, ConfigParser.read por un
metodo que abre en latin1 y que revienta si el archivo no existe. Como
libs.Utiles importa pyafipws, el parche estaba activo en toda la app.

Los tests comparan por igualdad y no por lo que imprime la consola: en
una consola cp1252 los acentos salen como '?' o como caracteres raros y
hacen creer que el dato esta roto cuando no lo esta.
"""

import os
import sys

import pytest

ESPERADO = "José Ñandú S.R.L."


@pytest.fixture
def entorno_limpio(tmp_path, monkeypatch):
    """Directorio temporal como carpeta de trabajo, con pyafipws ya
    importado (o sea, con el parche activo)."""
    import pyafipws.utils  # noqa: F401  activa el parche global
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_el_parche_de_pyafipws_realmente_esta_roto(entorno_limpio):
    """Que quede documentado que el problema existe, para que si alguien
    'simplifica' y vuelve a usar Config.read() se note."""
    import configparser
    ruta = os.path.join(str(entorno_limpio), "sistema.ini")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[FACTURA]\nempresa = " + ESPERADO + "\n")

    c = configparser.ConfigParser()
    c.read(ruta)
    assert c.get("FACTURA", "empresa") != ESPERADO, (
        "el parche de pyafipws ya no rompe la lectura: revisar si hace falta "
        "_leer_config")


def test_leerini_anda_bien_con_el_parche_activo(entorno_limpio):
    from libs.Utiles import LeerIni
    with open(os.path.join(str(entorno_limpio), "sistema.ini"), "w",
              encoding="utf-8") as f:
        f.write("[FACTURA]\nempresa = " + ESPERADO + "\n")
    assert LeerIni(clave="empresa", key="FACTURA") == ESPERADO


def test_leerini_no_falla_si_no_hay_archivo(entorno_limpio):
    """Bug real: con el parche, un sistema.ini ausente tiraba
    FileNotFoundError en vez de devolver vacio."""
    from libs.Utiles import LeerIni
    assert not os.path.exists(os.path.join(str(entorno_limpio), "sistema.ini"))
    assert LeerIni(clave="empresa", key="FACTURA") == ""


@pytest.mark.parametrize("nombre,valor", [
    ("acentos", "José Ñandú S.R.L."),
    ("simbolos", "Ñandú & Cía <S.A.> #1"),
    ("sin acentos", "Empresa Normal"),
    ("vacio", ""),
    ("largo", "Ñ" * 300),
])
def test_ida_y_vuelta_de_escritura(entorno_limpio, nombre, valor):
    """Bug real: GrabarIni escribia con la codificacion por defecto de la
    plataforma (cp1252 en Windows) y al releer en utf-8 no coincidia."""
    from libs.Utiles import GrabarIni, LeerIni
    GrabarIni(clave="empresa", key="FACTURA", valor=valor)
    assert LeerIni(clave="empresa", key="FACTURA") == valor


def test_la_escritura_es_utf8_real(entorno_limpio):
    from libs.Utiles import GrabarIni
    GrabarIni(clave="empresa", key="FACTURA", valor="Ñandú")
    crudo = open(os.path.join(str(entorno_limpio), "sistema.ini"), "rb").read()
    assert b"\xc3\x91" in crudo, "no se guardo en utf-8"


def test_borrar_una_clave(entorno_limpio):
    from libs.Utiles import GrabarIni, LeerIni
    GrabarIni(clave="empresa", key="FACTURA", valor="X")
    GrabarIni(clave="basura", key="FACTURA", valor="Y")
    GrabarIni(clave="basura", key="FACTURA", borrar=True)
    assert LeerIni(clave="basura", key="FACTURA") == ""
    assert LeerIni(clave="empresa", key="FACTURA") == "X"


def test_archivo_corrupto_no_volta_la_app(entorno_limpio):
    from libs.Utiles import LeerIni
    ruta = os.path.join(str(entorno_limpio), "sistema.ini")
    with open(ruta, "wb") as f:
        f.write(b"\xff\xfe\x00binario\x00basura")
    assert LeerIni(clave="empresa", key="FACTURA") == ""
