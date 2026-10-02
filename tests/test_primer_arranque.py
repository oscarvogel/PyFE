import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# -- Regresion: argumentos inesperados no pueden matar la app -------------
def test_learini_no_muere_con_argumentos_desconocidos(monkeypatch):
    """Bug real: LeerIni usaba argparse.parse_args(), que hace SystemExit
    con cualquier argumento que no conozca. Abrir el .exe con un archivo,
    o un doble clic, mataba la aplicacion."""
    import libs.Utiles as U
    monkeypatch.chdir(os.path.dirname(os.path.abspath(U.__file__)))
    monkeypatch.setattr(sys, "argv", ["PyFE.exe", "algo.txt", "--inventado"])
    assert U.LeerIni(clave="nombre_sistema") is not None


def test_grabarini_tampoco_muere(monkeypatch, tmp_path):
    import libs.Utiles as U
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sistema.ini").write_text("[param]\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["PyFE.exe", "--inventado", "x"])
    U.GrabarIni(clave="prueba", key="param", valor="ok")
    assert "prueba = ok" in (tmp_path / "sistema.ini").read_text(encoding="utf-8")


def test_los_argumentos_propios_seguen_funcionando(monkeypatch, tmp_path):
    """-i y -a tienen que seguir respetando lo que siempre respetaron."""
    import libs.Utiles as U
    carpeta = tmp_path / "otra"
    carpeta.mkdir()
    (carpeta / "mi.ini").write_text(
        "[param]\nnombre_sistema = DesdeArchivo\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv",
                        ["PyFE.exe", "-i", str(carpeta), "-a", "mi.ini"])
    assert U.LeerIni(clave="nombre_sistema") == "DesdeArchivo"


# -- La ventana del asistente --------------------------------------------
def test_el_asistente_se_puede_construir(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    assert "Configuracion inicial" in d.windowTitle()
    d.close()


def test_por_defecto_es_sqlite(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    assert d.datos()["base"] == "sqlite"
    d.close()


def test_con_sqlite_los_campos_de_servidor_estan_deshabilitados(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    assert d.txtHost.isEnabled() is False
    assert d.txtPassword.isEnabled() is False
    d.close()


def test_al_pasar_a_mysql_se_habilitan(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.cmbBase.setCurrentIndex(1)          # mysql
    assert d.cmbBase.currentData() == "mysql"
    assert d.txtHost.isEnabled() is True
    assert d.txtPassword.isEnabled() is True
    d.close()


def test_el_password_este_oculto(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    assert d.txtPassword.echoMode() == d.txtPassword.Password
    d.close()


def test_datos_devuelve_lo_que_se_typed(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.txtEmpresa.setText("  Mi Empresa SRL  ")
    d.txtCuit.setText("20-12345678-6")
    datos = d.datos()
    # los espacios se limpian al guardar
    assert datos["empresa"] == "Mi Empresa SRL"
    assert datos["cuit"] == "20-12345678-6"
    # y los defaults son los seguros
    assert datos["homo"] == "S"
    assert datos["cat_iva"] == "6"
    d.close()


def test_no_acepta_sin_empresa(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.txtEmpresa.setText("")
    d.aceptar()                      # deberia quedarse abierto
    assert d.result() == 0           # no acepto
    d.close()


def test_no_acepta_con_cuit_invalido(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.txtEmpresa.setText("Mi Empresa")
    d.txtCuit.setText("20-00000000-0")   # digito verificador erroneo
    d.aceptar()
    assert d.result() == 0
    d.close()


def test_avisa_el_cuit_invalido_mientras_se_escribe(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.txtCuit.setText("20-00000000-0")
    assert d.lblCuit.text() != ""
    d.txtCuit.setText("20-12345678-6")
    assert d.lblCuit.text() == ""
    d.close()


def test_acepta_con_todo_completo(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.txtEmpresa.setText("Mi Empresa")
    d.txtCuit.setText("20-12345678-6")
    d.aceptar()
    assert d.result() != 0           # si acepto
    d.close()


def test_mysql_exige_el_nombre_de_la_base(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.cmbBase.setCurrentIndex(1)
    d.txtEmpresa.setText("Mi Empresa")
    d.txtCuit.setText("20-12345678-6")
    d.txtBasedatos.setText("")
    d.aceptar()
    assert d.result() == 0           # sin nombre de base no puede seguir
    d.close()


def test_recordar_esta_marcado_por_defecto(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    assert d.chkRecordar.isChecked() is True
    d.close()


def test_si_no_recorda_no_se_guarda_el_password(app):
    from vistas.PrimerArranque import DialogoPrimerArranque
    d = DialogoPrimerArranque()
    d.cmbBase.setCurrentIndex(1)
    d.txtBasedatos.setText("mi_base")
    d.txtUsuario.setText("root")
    d.txtPassword.setText("secreto")
    d.chkRecordar.setChecked(False)
    assert "password" not in d.datos()
    d.chkRecordar.setChecked(True)
    assert d.datos()["password"] == "secreto"
    d.close()
