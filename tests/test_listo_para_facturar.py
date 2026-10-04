"""El chequeo de 'listo para facturar'.

Por que importa
---------------
Con una instalación recién hecha el usuario se iba con la app en verde y sin
poder emitir. El CUIT emisor era un relleno que el diagnóstico no detectaba
porque no estaba vacío, y los maestros podían estar vacíos si la carpeta
`data/` no había viajado con el ejecutable. Este chequeo es local (no habla con
ARCA) justamente para poder correr al terminar de instalar.

Cada test parte de una base sembrada de verdad con los CSV del repo, y después
rompe una sola cosa. Así no se prueba un caso imaginario: se prueba que el
chequeo ve la rotura que se acaba de hacer. Y corre en un subproceso con el
cwd en la instalación, porque el chequeo resuelve la base y los certificados
con rutas relativas.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs import listo_para_facturar as lpf  # noqa: E402


GUION_SIEMBRA = (
    "import os, sys\n"
    "os.chdir({c!r})\n"
    "sys.path.insert(0, {r!r})\n"
    "sys.argv = [sys.argv[0]]\n"
    "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
    "from modelos.ParametrosSistema import ParamSist\n"
    "from controladores.MigracionBaseDatos import MigracionBaseDatos\n"
    "ParamSist.create_table(safe=True)\n"
    "MigracionBaseDatos.__new__(MigracionBaseDatos).Migrar()\n"
)

GUION_CHECQUEO = (
    "import json, os, sys\n"
    "os.chdir({c!r})\n"
    "sys.path.insert(0, {r!r})\n"
    "sys.argv = [sys.argv[0]]\n"
    "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
    "from libs import listo_para_facturar as lpf\n"
    "pasos = lpf.chequear_instalacion()\n"
    "datos = [{{'nombre': p.nombre, 'ok': p.ok, 'detalle': p.detalle,\n"
    "          'que_hacer': p.que_hacer}} for p in pasos]\n"
    "with open({salida!r}, 'w', encoding='utf-8') as f:\n"
    "    json.dump(datos, f, ensure_ascii=False)\n"
)


def _instalar(nombre, cuit="20-12345678-6", con_cert=False):
    """Crea una carpeta de instalación y siembra la base con el código real."""
    carpeta = tempfile.mkdtemp(prefix="pyfe_listo_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    if con_cert:
        os.makedirs(os.path.join(carpeta, "certificados"), exist_ok=True)
        for archivo in ("certificado_homologacion.crt", "clave_privada_homo.key"):
            with open(os.path.join(carpeta, "certificados", archivo), "w") as f:
                f.write("x")

    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write(
            "[param]\nbase = sqlite\nusa_nombre_db = S\n"
            "basedatos = {}\nhomo = S\nconfigurado = S\n"
            "\n[FACTURA]\nempresa = Mi Empresa\n"
            "cuit = {}\n"
            "\n[WSFEv1]\ncat_iva = 1\npto_vta = 1\ncuit = 00000000000\n"
            "\n[WSAA]\n"
            "cert_homo = certificados/certificado_homologacion.crt\n"
            "privatekey_homo = certificados/clave_privada_homo.key\n".format(
                nombre, cuit))

    subprocess.run(
        [sys.executable, "-c", GUION_SIEMBRA.format(c=carpeta, r=RAIZ)],
        cwd=carpeta, capture_output=True, check=True)
    return carpeta


def _chequear(carpeta):
    salida = os.path.join(carpeta, "_pasos.json")
    subprocess.run(
        [sys.executable, "-c", GUION_CHECQUEO.format(
            c=carpeta, r=RAIZ, salida=salida)],
        cwd=carpeta, capture_output=True, check=True)
    with open(salida, encoding="utf-8") as f:
        datos = json.load(f)
    return {d["nombre"]: d for d in datos}


def _romper_sql(carpeta, nombre, sql):
    base = os.path.join(carpeta, nombre + ".db")
    c = sqlite3.connect(base)
    c.execute(sql)
    c.commit()
    c.close()


@pytest.fixture(scope="module")
def instalada():
    """Installación completa. module scope porque ningún test la modifica.

    Sembrar cuesta un subproceso y una base entera, y repetirlo por test
    multiplicaba por cinco el costo de la suite sin agregar cobertura.
    """
    carpeta = _instalar("ok", con_cert=True)
    yield carpeta
    shutil.rmtree(carpeta, ignore_errors=True)


# -- El camino feliz --------------------------------------------------------

def test_una_instalacion_completa_no_tiene_pendientes(instalada):
    pasos = _chequear(instalada)
    fallan = {n: d["detalle"] for n, d in pasos.items() if not d["ok"]}
    assert not fallan, "una instalación con todo cargado reporta: {}".format(fallan)


def test_el_chequeo_mira_todo_lo_que_importa(instalada):
    """Si un paso deja de mirarse, desaparece en silencio del chequeo."""
    pasos = _chequear(instalada)
    for nombre in ("Base de datos", "Datos maestros", "Cliente consumidor final",
                   "Condición de IVA del receptor", "CUIT del emisor",
                   "Categoría de IVA", "Punto de venta",
                   "Certificado de homologación"):
        assert nombre in pasos, "el chequeo no mira {}".format(nombre)


# -- Cada rotura se ve ------------------------------------------------------

def test_maestros_vacios():
    """El caso de data/ sin viajar con el ejecutable."""
    carpeta = _instalar("vacia", con_cert=True)
    try:
        _romper_sql(carpeta, "vacia", "delete from tipoiva")
        _romper_sql(carpeta, "vacia", "delete from formapago")
        pasos = _chequear(carpeta)
        assert pasos["Datos maestros"]["ok"] is False
        assert "Tipoiva" in pasos["Datos maestros"]["detalle"]
        assert "Formapago" in pasos["Datos maestros"]["detalle"]
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_sin_clientes():
    carpeta = _instalar("sinclientes", con_cert=True)
    try:
        _romper_sql(carpeta, "sinclientes", "delete from clientes")
        pasos = _chequear(carpeta)
        assert pasos["Cliente consumidor final"]["ok"] is False
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_una_condicion_de_iva_colgada():
    """La fila que quedó en el default y no le corresponde."""
    carpeta = _instalar("colgada", con_cert=True)
    try:
        _romper_sql(carpeta, "colgada",
                    "update tiporesp set condicion_iva_receptor_id = 5 "
                    "where nombre = 'RESP. INSCRIPTO'")
        pasos = _chequear(carpeta)
        assert pasos["Condición de IVA del receptor"]["ok"] is False
        assert "RESP. INSCRIPTO" in pasos["Condición de IVA del receptor"]["detalle"]
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_cuit_que_falta():
    carpeta = _instalar("sincuit", cuit="", con_cert=True)
    try:
        pasos = _chequear(carpeta)
        assert pasos["CUIT del emisor"]["ok"] is False
        assert "Configuracion" in pasos["CUIT del emisor"]["que_hacer"]
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_certificado_que_no_esta_en_disco():
    """El certificado es opcional, pero si se cargo y no esta, es un problema."""
    carpeta = _instalar("sincert", con_cert=False)
    try:
        pasos = _chequear(carpeta)
        assert pasos["Certificado de homologación"]["ok"] is False
        assert "Certificados" in pasos["Certificado de homologación"]["que_hacer"]
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_punto_de_venta_que_falta():
    carpeta = _instalar("sintp", con_cert=True)
    try:
        ini = os.path.join(carpeta, "sistema.ini")
        with open(ini, encoding="utf-8") as f:
            texto = f.read()
        with open(ini, "w", encoding="utf-8") as f:
            f.write(texto.replace("pto_vta = 1", "pto_vta ="))
        pasos = _chequear(carpeta)
        assert pasos["Punto de venta"]["ok"] is False
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


# -- La parte pura ----------------------------------------------------------

def test_formatear_sin_pendientes_dice_que_esta_lista():
    paso = lpf.PasoInstalacion("CUIT del emisor", True, "20123456786")
    assert "completa" in lpf.formatear([paso])


def test_formatear_incluye_el_que_hacer():
    pasos = [lpf.PasoInstalacion("Base de datos", False, "no se pudo leer",
                                 "Revise Configuracion")]
    texto = lpf.formatear(pasos)
    assert "Base de datos" in texto
    assert "Revise Configuracion" in texto


def test_pendientes_filtra_lo_que_falla():
    pasos = [lpf.PasoInstalacion("a", True, ""),
             lpf.PasoInstalacion("b", False, "")]
    assert [p.nombre for p in lpf.pendientes(pasos)] == ["b"]


def test_que_hacer_siempre_dice_donde_ir():
    """Un pendiente sin acción concreta no le sirve de nada al usuario."""
    carpeta = _instalar("sinaccion", cuit="")
    try:
        pasos = _chequear(carpeta)
        for nombre, paso in pasos.items():
            if not paso["ok"]:
                assert paso["que_hacer"].strip(), \
                    "{} falla pero no dice qué hacer".format(nombre)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
