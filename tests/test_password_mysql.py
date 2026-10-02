"""Pruebas de regresion del camino MySQL en procesos limpios.

Se lanzan en un subproceso porque el password se resuelve al importar
modelos.ModeloBase, y en la sesion de pruebas ese modulo ya quedo
importado con otra configuracion.

Cada caso corre desde un directorio temporal propio: LeerIni usa
os.getcwd(), asi que si corrieran desde el repo leerian el sistema.ini
real y el test no probaria nada.
"""

import base64
import os
import subprocess
import sys
import textwrap

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INI_BASE = """[param]
iniciosistema = {dir}
nombre_sistema = Prueba
base = mysql
basedatos = prueba
usuario = root
host = 127.0.0.1
homo = N
"""

SCRIPT = textwrap.dedent("""
    import sys
    sys.argv = [sys.argv[0]]
    import peewee
    # Que no intente conectarse de verdad
    peewee.MySQLDatabase.connect = lambda self, *a, **k: None
    from modelos import ModeloBase
    from libs.secretos import resolver_password_base
    p = resolver_password_base()
    print("RESULTADO|db={}|password={}".format(
        type(ModeloBase.db).__name__, "PIDE" if p is None else "OK"))
""")


def _correr(tmp_path, extra_param):
    tmp = str(tmp_path)
    ini = os.path.join(tmp, "sistema.ini")
    with open(ini, "w", encoding="utf-8") as f:
        f.write(INI_BASE.format(dir=tmp.replace("\\", "/") + "/") + extra_param)

    script = os.path.join(tmp, "c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(SCRIPT)

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO
    env["PYTHONWARNINGS"] = "ignore"
    r = subprocess.run([sys.executable, script], cwd=tmp, env=env,
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    assert "Traceback" not in out, "el import revento:\n" + out
    linea = next((l for l in out.splitlines() if "RESULTADO|" in l), "")
    assert linea, "el proceso no llego al final:\n" + out
    return linea


def test_mysql_sin_password_pide_el_dato(tmp_path):
    # Instalacion nueva: tiene que pedirlo, no romper.
    r = _correr(tmp_path, "")
    assert "db=MySQLDatabase" in r
    assert "password=PIDE" in r


def test_mysql_esquema_viejo_sigue_andando(tmp_path):
    # Lo que hay instalado hoy: una instalacion no puede empezar a pedir
    # la clave si ya la tiene guardada de la forma vieja.
    from cryptography.fernet import Fernet
    clave = Fernet.generate_key()
    cifrado = Fernet(clave).encrypt(b"root").decode()
    r = _correr(tmp_path, "password = {}\nkey = {}\n".format(cifrado, clave.decode()))
    assert "db=MySQLDatabase" in r
    assert "password=OK" in r


def test_mysql_formato_nuevo_sigue_andando(tmp_path):
    from cryptography.fernet import Fernet
    from libs.secretos import PREFIXO_FERNET
    clave = Fernet.generate_key()
    valor = PREFIXO_FERNET + base64.b64encode(Fernet(clave).encrypt(b"root")).decode()
    r = _correr(tmp_path, "password = {}\nkey = {}\n".format(valor, clave.decode()))
    assert "password=OK" in r


def test_mysql_password_corrupto_pide_en_vez_de_romper(tmp_path):
    # Un secreto ilegible no puede voltear la app: se pide de nuevo.
    r = _correr(tmp_path, "password = dpapi:v1:@@@no-es-base64@@@\n")
    assert "password=PIDE" in r
