# coding=utf-8
"""Tests del generador de build info y del contrato de release.

Por que hay que testear esto
----------------------------
`version.txt` lo lee PyInstaller con `eval()` y tiene que ser UNA expresion
de Python. El archivo avisaba en su propio encabezado que agregar una linea
suelta rompe la compilacion con "Failed to deserialize VSVersionInfo".

Acabo de meter un timestamp de 6 componentes donde antes habia una version
corta, y la unica forma de saber si eso sigue compilando es **preguntarle a
la libreria instalada**: se genera el archivo y se hace que PyInstaller lo
parsee y lo serialice. Un test que solo mirara que el archivo existe
pasaria en verde aunque la compilacion este rota.

Los tests trabajan sobre una copia en tmp_path, no sobre los archivos del
repo: generar y restaurar son operaciones que el release hace de verdad, y
un test no puede dejar el arbol de trabajo con la version de otro build.
"""

import importlib
import os
import shutil
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

VERSION_TEXTO = os.path.join(RAIZ, "version.txt")
BUILD_INFO_REPO = os.path.join(RAIZ, "libs", "build_info.py")

VERSION_BUILD = "2026.10.05.08.37.00"


@pytest.fixture
def generador(tmp_path):
    """El generador con las rutas apuntando a copias de los archivos reales.

    Ojo con el nombre: dentro del fixture hay que referirse al modulo por
    `generar_build_info`. Escribir el nombre del propio fixture resuelve al
    espacio de nombres global y devuelve la funcion, no el modulo.
    """
    sys.path.insert(0, os.path.join(RAIZ, "tools"))
    import generar_build_info

    importlib.reload(generar_build_info)

    version_copia = tmp_path / "version.txt"
    shutil.copyfile(VERSION_TEXTO, str(version_copia))
    # El build_info que se usa de semilla es el REAL del repo, no uno
    # armado a mano: el comportamiento interesante es que el generador
    # conserve el resto del archivo, y para eso tiene que partir del real.
    build_info_copia = tmp_path / "build_info.py"
    shutil.copyfile(BUILD_INFO_REPO, str(build_info_copia))

    generar_build_info.ARCHIVO_VERSION = str(version_copia)
    generar_build_info.ARCHIVO_BUILD_INFO = str(build_info_copia)
    return generar_build_info


def _importar_build_info(ruta):
    """Importa el archivo generado como modulo, de verdad.

    Importarlo y llamar sus funciones es la unica forma de comprobar que
    el archivo sirve. Leer el texto y comparar strings no detectaria que
    falte una funcion.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_info_bajo_prueba", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_build_info_generado_sigue_siendo_un_modulo_que_funciona(generador):
    """El bug que solo aparecia en el release real.

    El generador reescribia libs/build_info.py entero desde una plantilla
    con dos lineas. Eso se llevaba `manifest_url_for`, `es_build_productivo` y
    `changelog_url_for`: la app compilada no podia consultar actualizaciones.

    Y la suite entera pasaba en verde, porque los tests corren contra el
    archivo versionado y nunca contra el generado. Solo fallaba cuando
    `release.ps1` generaba el build de verdad. Este test hace exactamente lo
    que hacia el release: generar y despues importar.
    """
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])

    modulo = _importar_build_info(generador.ARCHIVO_BUILD_INFO)

    # La identidad del build, correcta.
    assert modulo.APP_ID == "asiento"
    assert modulo.BUILD_VERSION == VERSION_BUILD
    # Y las funciones que el release anterior se habia llevado.
    assert modulo.es_build_productivo() is True
    assert "apps/asiento/latest.json" in modulo.manifest_url_for("asiento")
    assert "apps/asiento/changelog.json" in modulo.changelog_url_for("asiento")

    # Un app_id desconocido tiene que seguir dando error, no KeyError pelado.
    with pytest.raises(ValueError):
        modulo.manifest_url_for("no-registrada")


def test_despues_de_restaurar_el_modulo_tambien_sigue_funcionando(generador):
    """El ciclo completo: generar, restaurar, y que el archivo quede entero."""
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    generador.main(["--restaurar"])

    modulo = _importar_build_info(generador.ARCHIVO_BUILD_INFO)
    assert modulo.APP_ID == "development"
    assert modulo.es_build_productivo() is False
    assert "apps/asiento/latest.json" in modulo.manifest_url_for("asiento")


def test_el_generador_no_toca_el_resto_del_archivo(generador):
    """Ni una linea mas de las dos, ni una menos.

    Si el generador reescribiera el archivo, cualquier correccion que se le
    haga (una app nueva, un comentario) se perderia en el proximo release,
    en silencio.
    """
    antes = open(BUILD_INFO_REPO, "r", encoding="utf-8").read()
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    generador.main(["--restaurar"])
    despues = open(generador.ARCHIVO_BUILD_INFO, "r", encoding="utf-8").read()

    assert antes == despues, "el ciclo generar/restaurar no devuelve el archivo"


def test_el_generador_falla_sin_tocar_nada_si_el_archivo_no_tiene_los_campos(generador):
    """Un build_info con otro formato tiene que cortar el release, no
    dejarlo a medias.

    El riesgo de verdad es que escriba lo que pueda y siga: el release
    publicaria un build cuya app no puede actualizar, y el error apareceria
    en la PC del cliente como "no me avisa de las actualizaciones".
    """
    bueno = open(BUILD_INFO_REPO, "r", encoding="utf-8").read()
    roto = "# sin los campos que el generador espera\nX = 1\n"
    try:
        with open(generador.ARCHIVO_BUILD_INFO, "w", encoding="utf-8") as fh:
            fh.write(roto)

        with pytest.raises(ValueError):
            generador.escribir_build_info("asiento", VERSION_BUILD)

        # Y no lo toco: quedo entero, no a medias.
        with open(generador.ARCHIVO_BUILD_INFO, "r", encoding="utf-8") as fh:
            assert fh.read() == roto
    finally:
        with open(generador.ARCHIVO_BUILD_INFO, "w", encoding="utf-8") as fh:
            fh.write(bueno)


def _build_info_actual(ruta):
    texto = open(ruta, "r", encoding="utf-8").read()
    return texto


def test_el_arbol_versionado_esta_en_modo_desarrollo():
    """El repo nunca queda con la identidad de un build publicado.

    Si el release fallara entre generar y restaurar, el arbol quedaria
    marcando la app como la version que se estaba compilando. En desarrollo
    eso haria que el actualizador creyera que estas atrasado.
    """
    texto = open(BUILD_INFO_REPO, "r", encoding="utf-8").read()
    assert 'APP_ID = "development"' in texto
    assert 'BUILD_VERSION = "0.0.0.0.0.0"' in texto


def test_generar_escribe_app_id_y_timestamp(generador):
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])

    texto = generador._leer(generador.ARCHIVO_BUILD_INFO)
    assert 'APP_ID = "asiento"' in texto
    assert 'BUILD_VERSION = "{}"'.format(VERSION_BUILD) in texto


def test_restaurar_deja_el_estado_de_desarrollo(generador):
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    generador.main(["--restaurar"])

    texto = generador._leer(generador.ARCHIVO_BUILD_INFO)
    assert 'APP_ID = "development"' in texto
    assert 'BUILD_VERSION = "0.0.0.0.0.0"' in texto


def test_el_version_txt_generado_lo_parsea_pyinstaller(generador):
    """La prueba que de verdad importa: que la compilacion no se rompa.

    PyInstaller 6.x expone `load_version_info_from_text_file`, que es
    exactamente el parseo que hace al compilar. Si el archivo con timestamp
    no pasa por ahi, el build muere con "Failed to deserialize
    VSVersionInfo" y no hay version nueva para instalar.
    """
    versioninfo = pytest.importorskip(
        "PyInstaller.utils.win32.versioninfo")
    if not hasattr(versioninfo, "load_version_info_from_text_file"):
        pytest.skip("la version de PyInstaller instalada no expone el parser")

    # Ejecuta de verdad: main() escribe los archivos.
    assert generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"]) == 0

    version = versioninfo.load_version_info_from_text_file(
        generador.ARCHIVO_VERSION)
    # Y que se pueda serializar al recurso que va dentro del .exe.
    assert version.toRaw()

    strings = {}
    for entrada in version.kids[0].kids[0].kids:
        strings[entrada.name] = entrada.val
    assert strings["ProductVersion"] == VERSION_BUILD
    assert strings["FileVersion"] == VERSION_BUILD
    # El bloque ffi son 4 DWORD fijos: de ahi salen los primeros cuatro
    # componentes del timestamp.
    assert version.ffi.fileVersionMS is not None
    assert version.ffi.fileVersionLS is not None


def test_el_version_txt_conserva_la_estructura_de_vs_version_info(generador):
    """Un solo cambio de valores, nunca una reescritura.

    El archivo se genera con reemplazos sobre el texto, no desde una
    plantilla. Si se regenerara entero, cualquier correccion que se le haga
    al archivo (un copyright, un nombre de producto) se perderia en el
    proximo build.
    """
    original = open(VERSION_TEXTO, "r", encoding="utf-8").read()
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    generado = generador._leer(generador.ARCHIVO_VERSION)

    assert "VSVersionInfo(" in generado
    assert "PyInstaller lo lee con eval()" in generado
    for linea in ("CompanyName", "ProductName", "FileDescription",
                  "LegalCopyright", "VarFileInfo"):
        assert linea in generado
    # Solo cambian los numeros de version.
    assert len(generado.splitlines()) == len(original.splitlines())


def test_filevers_tiene_cuatro_componentes_para_windows(generador):
    """El bloque `ffi` de VSVersionInfo es de 4 DWORD: ni uno mas ni menos.

    El manifiesto tiene 6 componentes. Meterlos todos ahi daria un recurso
    invalido, que es justamente el error que el encabezado del archivo
    describe.
    """
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    generado = generador._leer(generador.ARCHIVO_VERSION)

    import re
    for clave in ("filevers", "prodvers"):
        encontrado = re.search(clave + r"=\(([^)]*)\)", generado)
        assert encontrado, "falta {}".format(clave)
        partes = encontrado.group(1).split(",")
        assert len(partes) == 4, "{} tiene {} componentes".format(clave, len(partes))
        assert all(p.strip().isdigit() for p in partes)


def test_rechaza_una_version_con_formato_incorrecto(generador):
    """Con un formato raro, el error tiene que ser explicito.

    Escribir '0.9.0' o '2026.10.5' en el manifiesto es la causa mas comun de
    un chequeo que nunca encuentra actualizaciones.
    """
    assert generador.main(["--version", "0.9.0"]) == 2
    assert generador.main(["--version", "2026.10.5"]) == 2


def test_verificar_informa_el_estado(generador, capsys):
    generador.main(["--version", VERSION_BUILD, "--app-id", "asiento"])
    assert generador.main(["--verificar"]) == 0
    salida = capsys.readouterr().out
    assert "asiento" in salida
    assert "PRODUCTIVO" in salida
