"""Tests de la configuracion de una instalacion nueva."""

import os
import sys

import pytest

from libs import instalacion


# -- Deteccion del primer arranque ----------------------------------------
# Los tests corren con cwd en tmp_path porque LeerIni resuelve el archivo
# con os.getcwd(). Si se parchea solo ruta_config, la comprobacion de
# existencia y la de valores miran archivos distintos y el test no prueba nada.


def test_sin_archivo_es_primer_arranque(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert instalacion.es_primer_arranque() is True


def _ini(tmp_path, contenido):
    ruta = tmp_path / "sistema.ini"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_base_vacia_es_primer_arranque(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini(tmp_path, "[param]\nnombre_sistema = algo\n")
    assert instalacion.es_primer_arranque() is True


def test_sin_empresa_es_primer_arranque(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini(tmp_path, "[param]\nbase = sqlite\n\n[FACTURA]\ncuit = x\n")
    assert instalacion.es_primer_arranque() is True


def test_configuracion_completa_no_es_primer_arranque(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini(tmp_path,
         "[param]\nbase = sqlite\nconfigurado = S\n\n[FACTURA]\nempresa = Mi Empresa\n")
    assert instalacion.es_primer_arranque() is False


def test_configuracion_mysql_tampoco_es_primer_arranque(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ini(tmp_path,
         "[param]\nbase = mysql\nconfigurado = S\n\n[FACTURA]\nempresa = Mi Empresa\n")
    assert instalacion.es_primer_arranque() is False


def test_una_plantura_recien_instalada_todavia_es_primer_arranque(tmp_path, monkeypatch):
    """Regresion: la plantilla trae 'base = sqlite' y 'empresa = Razon
    Social' de ejemplo. Si la deteccion se guiara por los valores, una
    instalacion nueva creeria que ya estaba configurada y se saltaria el
    asistente. Por eso el marcador 'configurado = S'."""
    import shutil

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shutil.copy(os.path.join(repo, "sistema.ini.example"),
                tmp_path / "sistema.ini")
    monkeypatch.chdir(tmp_path)
    assert instalacion.es_primer_arranque() is True


# -- Guardado ---------------------------------------------------------------
class GraboFalso:
    def __init__(self):
        self.datos = {}
        self.borrados = []

    def __call__(self, clave, key, valor):
        self.datos["{}|{}".format(key, clave)] = valor

    def borrar(self, clave, key):
        self.borrados.append("{}|{}".format(key, clave))


def _datos_minimos():
    return {"base": "sqlite", "empresa": "Mi Empresa", "cuit": "20-12345678-6"}


def test_guarda_lo_minimo_para_que_deje_de_ser_primer_arranque(tmp_path, monkeypatch):
    g = GraboFalso()
    instalacion.guardar_config_inicial(_datos_minimos(), escribir=g)
    assert g.datos["param|base"] == "sqlite"
    assert g.datos["FACTURA|empresa"] == "Mi Empresa"
    assert g.datos["FACTURA|cuit"] == "20-12345678-6"
    # el marcador es lo que hace que no vuelva a pedir la configuracion
    assert g.datos["param|configurado"] == "S"


def test_sqlite_no_escribe_datos_de_servidor(tmp_path, monkeypatch):
    g = GraboFalso()
    instalacion.guardar_config_inicial(_datos_minimos(), escribir=g)
    # con sqlite no hay server ni password
    assert g.datos["param|host"] == "localhost"
    assert "param|password" not in g.datos


def test_mysql_guarda_host_usuario_y_base(tmp_path, monkeypatch):
    g = GraboFalso()
    d = _datos_minimos()
    d.update({"base": "mysql", "basedatos": "mi_base",
              "host": "10.0.0.5", "usuario": "root"})
    instalacion.guardar_config_inicial(d, escribir=g)
    assert g.datos["param|host"] == "10.0.0.5"
    assert g.datos["param|usuario"] == "root"
    assert g.datos["param|basedatos"] == "mi_base"


def test_por_defecto_queda_en_homologacion(tmp_path, monkeypatch):
    g = GraboFalso()
    instalacion.guardar_config_inicial(_datos_minimos(), escribir=g)
    # instalar en produccion por error es el peor default posible
    assert g.datos["param|homo"] == "S"


def test_por_defecto_sqlite(tmp_path, monkeypatch):
    g = GraboFalso()
    d = _datos_minimos()
    del d["base"]
    instalacion.guardar_config_inicial(d, escribir=g)
    assert g.datos["param|base"] == "sqlite"


def test_guarda_url_de_afip_y_certificados(tmp_path, monkeypatch):
    g = GraboFalso()
    instalacion.guardar_config_inicial(_datos_minimos(), escribir=g)
    assert "wsaa.afip.gov.ar" in g.datos["WSAA|url_prod"]
    assert "wsaahomo.afip.gov.ar" in g.datos["WSAA|url_homo"]
    assert "wsfev1" in g.datos["WSFEv1|url_prod"]
    assert g.datos["WSFEv1|cat_iva"] == "6"
    assert g.datos["WSAA|privatekey_prod"]


def test_ida_y_vuelta_con_ini_real(tmp_path, monkeypatch):
    """Escribe de verdad y vuelve a leer: el ciclo completo."""
    monkeypatch.chdir(tmp_path)
    import libs.Utiles as U

    instalacion.guardar_config_inicial(_datos_minimos())

    assert (tmp_path / "sistema.ini").exists()
    assert U.LeerIni(clave="base") == "sqlite"
    assert U.LeerIni(clave="empresa", key="FACTURA") == "Mi Empresa"
    # y con eso deja de ser primer arranque
    assert instalacion.es_primer_arranque() is False
