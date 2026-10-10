# coding=utf-8
"""Tests de la carpeta de datos: donde se escribe cuando la app no se puede.

El bug que estos tests cubren
----------------------------
Instalado en `C:\\Program Files\\Asiento`, el programa corre sin permisos de
administrador y no puede escribir en su propia carpeta. El asistente de primer
arranque completaba y al guardar tiraba:

    PermissionError: [Errno 13] Permission denied:
    'C:\\Program Files\\Asiento\\sistema.ini'

Que se escriba en la carpeta del usuario, y no en la del programa, es lo que
evita eso (ver `libs/rutas.py`).

Que se prueba y que no
----------------------
Ojo con el alcance de estos tests, porque es facil pasarse de optimista:

- Lo que SI se prueba de verdad: que la escritura del asistente termine sin
  excepcion y que el archivo exista con lo que se le pidio, usando el
  `GrabarIni` real y sin pasarle una funcion de escritura a mano.
- Lo que NO se puede reproducir aca: que una carpeta sea de solo lectura por
  permisos de Windows. Crear un ACL que la vuelva no escribible es cosa de la
  maquina, no del repo, y el test pasaria en la maquina de desarrollo (que
  corre como administrador) y fallaria en la de un usuario comun, al reves de
  lo que tiene que pasar.
  Por eso la decision "esta carpeta no se puede escribir" se INYECTA, y en
  cambio la consecuencia de esa decision -- que el archivo termine en la
  carpeta de datos y no en la del programa -- se mide sobre el archivo de
  verdad. La sonda que decide se prueba aparte, con carpetas reales.

La prueba manual, en la maquina donde pasa el bug, esta en
`docs/CARPETA-DE-DATOS.md`.
"""

import os
import sys

import pytest

from libs import instalacion
from libs import rutas
from libs.Utiles import ErrorEscrituraConfig, GrabarIni, LeerIni

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _cache_limpia():
    """Cada test deja la sesion como la encontro.

    `libs.rutas` cachea la carpeta de datos y las sondas de escritura. Sin
    esto, un test que fija una carpeta deja el resultado puesto para todos los
    que corren despues.

    Y tambien se restaura el directorio de trabajo: `_asegurar_carpeta_de_trabajo`
    hace `os.chdir` por su cuenta, y `monkeypatch.chdir` NO lo deshace (solo
    recuerda los cambios que hace el propio test). Sin restaurarlo, la suite
    sigue corriendo desde una carpeta temporal y los tests que usan rutas
    relativas --`plantillas/factura_qr.csv`, por ejemplo-- dejan de encontrar
    lo que necesitan.
    """
    antes = os.getcwd()
    rutas.limpiar_cache()
    yield
    rutas.limpiar_cache()
    if os.getcwd() != antes:
        os.chdir(antes)


def _sin_permiso_de_escritura(monkeypatch):
    """Deja el directorio de trabajo como si no se pudiera escribir en el.

    Se inyecta la sonda, no `os.access`: la sonda real se prueba en
    `test_la_sonda_escribe_un_archivo_de_verdad`.
    """
    monkeypatch.setattr(rutas, "puede_escribir", lambda carpeta, probar=None: False)
    rutas.limpiar_cache()


def _escribible_siempre(carpeta, probar=None):
    """El directorio de trabajo se puede escribir, sin hacer la sonda.

    Se pasa en vez de la sonda real para que el test no dependa de los permisos
    de la maquina donde corre. La sonda de verdad se prueba en
    `test_la_sonda_escribe_un_archivo_de_verdad`.
    """
    return True


DATOS_ASISTENTE = {
    "base": "sqlite",
    "nombre_sistema": "Asiento",
    "empresa": "Cliente de Prueba SRL",
    "membrete1": "Direction 123",
    "cuit": "30111111126",
    "basedatos": "pyfe",
    "homo": "S",
}


# -- La sonda que decide ----------------------------------------------------


def test_la_sonda_escribe_un_archivo_de_verdad(tmp_path):
    """La sonda tiene que crear el archivo, no adivinar con os.access.

    `os.access(carpeta, os.W_OK)` da True en carpetas en las que despues no se
    puede crear nada, que es justo el caso que hace fallar a los usuarios. Por
    eso la sonda abre un archivo de verdad.
    """
    assert rutas.puede_escribir(str(tmp_path)) is True

    # Y no deja nada tirado.
    assert os.listdir(str(tmp_path)) == []


def test_la_sonda_dice_que_no_si_la_carpeta_no_existe(tmp_path):
    assert rutas.puede_escribir(str(tmp_path / "no-esta")) is False


def test_la_sonda_dice_que_no_si_no_se_puede_crear(tmp_path):
    """Si el archivo no se puede crear, no es escribible. Sin excepciones."""
    assert rutas.puede_escribir(str(tmp_path), probar=_levantar) is False


def _levantar(_carpeta):
    raise PermissionError(13, "Permission denied")


# -- Donde se escribe -------------------------------------------------------


def test_si_la_carpeta_de_trabajo_se_puede_escribir_se_usa_esa(tmp_path,
                                                              monkeypatch):
    """Desarrollo, tests, portables y tools/ siguen usando el cwd.

    Esto no es un detalle: los tests del repo hacen `monkeypatch.chdir` y
    esperan que el sistema.ini se lea de ahi. Si la regla se invertiera, todos
    esos tests leerian la configuracion de otro lado.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setattr(rutas, "puede_escribir", _escribible_siempre)
    rutas.limpiar_cache()

    assert os.path.normcase(rutas.carpeta_datos()) == \
        os.path.normcase(os.path.abspath(str(tmp_path)))
    assert os.path.normcase(rutas.ruta_ini()) == \
        os.path.normcase(os.path.abspath(str(tmp_path / "sistema.ini")))


def test_si_la_carpeta_del_programa_no_se_puede_escribir_va_a_localappdata(
        tmp_path, monkeypatch):
    """El caso del bug: la carpeta del programa no se puede escribir."""
    programa = tmp_path / "Program Files" / "Asiento"
    programa.mkdir(parents=True)
    datos = tmp_path / "localappdata"
    datos.mkdir()

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _sin_permiso_de_escritura(monkeypatch)

    assert rutas.carpeta_datos() == str(datos / "Asiento")
    # Y la carpeta se crea sola: si el usuario nunca abrio la app, no existe.
    assert os.path.isdir(str(datos / "Asiento"))
    assert rutas.ruta_ini() == str(datos / "Asiento" / "sistema.ini")


def test_la_variable_de_entorno_manda(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    forzado = tmp_path / "otro-lugar"
    monkeypatch.setenv(rutas.ENV_CARPETA_DATOS, str(forzado))

    assert rutas.carpeta_datos() == str(forzado)
    assert os.path.isdir(str(forzado))


def test_la_base_tambien_va_a_la_carpeta_de_datos(tmp_path, monkeypatch):
    """La base es relativa al directorio de trabajo: si no se mueve, no se crea."""
    programa = tmp_path / "programa"
    programa.mkdir()
    datos = tmp_path / "datos"
    datos.mkdir()

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _sin_permiso_de_escritura(monkeypatch)

    assert rutas.ruta_base("sistema.db") == str(datos / "Asiento" / "sistema.db")


# -- Instalar en otro lado sin perder lo que ya estaba ---------------------
#
# El 2026-10-08 la instalacion paso de `C:\Program Files\Asiento` a
# `%LOCALAPPDATA%\Programs\Asiento`. Con la regla de antes, el directorio de
# trabajo escribible se llevaba la configuracion y la base a la carpeta nueva,
# que viene vacia: el cliente que ya usaba el sistema habria visto el asistente
# de nuevo y la base VACIA. Estos tests fijan la regla que lo evita.


def _instalada(monkeypatch, instalar=True):
    """Deja la app como si fuera el ejecutable compilado de PyInstaller."""
    monkeypatch.setattr(rutas.sys, "frozen", instalar, raising=False)


def test_la_app_instalada_no_abandona_los_datos_que_ya_tenia(
        tmp_path, monkeypatch):
    """El caso del cliente que ya venia usando el sistema.

    La carpeta de datos vieja sigue mandando, aunque la carpeta del programa
    nueva se pueda escribir. Si esto no se respeta, el cliente ve el asistente
    de primer arranque y una base sin un solo comprobante.
    """
    programa = tmp_path / "Programs" / "Asiento"
    programa.mkdir(parents=True)
    datos = tmp_path / "localappdata"
    (datos / "Asiento").mkdir(parents=True)
    (datos / "Asiento" / "sistema.ini").write_text(
        "[param]\nconfigurado = S\nempresa = Cliente Real\n", encoding="utf-8")

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _instalada(monkeypatch)
    monkeypatch.setattr(rutas, "puede_escribir", _escribible_siempre)
    rutas.limpiar_cache()

    assert os.path.normcase(rutas.carpeta_datos()) == \
        os.path.normcase(str(datos / "Asiento"))
    assert rutas.ruta_ini() == str(datos / "Asiento" / "sistema.ini")


def test_una_instalacion_nueva_no_busca_datos_viejos(tmp_path, monkeypatch):
    """Sin datos previos, una instalacion nueva escribe junto al programa.

    Es lo que espera una maquina limpia: la carpeta del programa es del usuario
    y se puede escribir, asi que no tiene sentido mandar la configuracion a
    otro lado.
    """
    programa = tmp_path / "Programs" / "Asiento"
    programa.mkdir(parents=True)
    datos = tmp_path / "localappdata"
    datos.mkdir()

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _instalada(monkeypatch)
    monkeypatch.setattr(rutas, "puede_escribir", _escribible_siempre)
    rutas.limpiar_cache()

    assert os.path.normcase(rutas.carpeta_datos()) == \
        os.path.normcase(str(programa))


def test_en_desarrollo_manda_el_directorio_de_trabajo(tmp_path, monkeypatch):
    """Sin `sys.frozen` no hay mudanza: el `sistema.ini` del repo manda.

    Importa mas de lo que parece. En una maquina donde el sistema ya esta
    instalado, `%LOCALAPPDATA%\\Asiento\\sistema.ini` existe de verdad; si esta
    regla no mirara `sys.frozen`, `python main.py` desde el repo leeria ese
    archivo y no el del repo. Cambiar el archivo de la carpeta de trabajo no
    cambiaria nada y el bug seria invisible.
    """
    programa = tmp_path / "repo"
    programa.mkdir()
    (programa / "sistema.ini").write_text("[param]\nempresa = Del Repo\n",
                                          encoding="utf-8")
    datos = tmp_path / "localappdata"
    (datos / "Asiento").mkdir(parents=True)
    (datos / "Asiento" / "sistema.ini").write_text(
        "[param]\nempresa = Del Cliente\n", encoding="utf-8")

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _instalada(monkeypatch, instalar=False)
    monkeypatch.setattr(rutas, "puede_escribir", _escribible_siempre)
    rutas.limpiar_cache()

    assert os.path.normcase(rutas.carpeta_datos()) == \
        os.path.normcase(str(programa))
    # Y lo que lee es el archivo del repo, no el del cliente instalado.
    assert LeerIni(clave="empresa", key="param") == "Del Repo"


def test_buscar_datos_previos_no_crea_la_carpeta(tmp_path, monkeypatch):
    """Preguntar no es crear.

    Si `_datos_ya_existentes` creara la carpeta, arrancar la app en una
    maquina donde nunca se instalo dejaria `%LOCALAPPDATA%\\Asiento` vacia en el
    perfil de cada usuario.
    """
    datos = tmp_path / "localappdata"
    datos.mkdir()
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _instalada(monkeypatch)
    rutas.limpiar_cache()

    assert not (datos / "Asiento").exists()
    rutas.carpeta_datos()
    assert not (datos / "Asiento").exists()


# -- El asistente de primer arranque ---------------------------------------
#
# Este es el camino que se rompio: completar el asistente y que al guardar
# muera el programa.


def test_el_asistente_guarda_sin_morir(tmp_path, monkeypatch):
    """El wizard completo, con el GrabarIni real, en una carpeta de solo lectura.

    Antes esto tiraba PermissionError y la app se caia con un traceback de
    PyInstaller. Ahora el archivo queda en la carpeta de datos del usuario.
    """
    programa = tmp_path / "Program Files" / "Asiento"
    programa.mkdir(parents=True)
    datos = tmp_path / "localappdata"
    datos.mkdir()

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _sin_permiso_de_escritura(monkeypatch)

    resultado = instalacion.guardar_config_inicial(dict(DATOS_ASISTENTE))

    assert resultado["base"] == "sqlite"
    escrito = datos / "Asiento" / "sistema.ini"
    assert escrito.is_file(), "el sistema.ini tiene que quedar en la carpeta de datos"

    # Contenido real, leido con el LeerIni real.
    assert LeerIni(clave="configurado", key="param") == "S"
    assert LeerIni(clave="empresa", key="FACTURA") == "Cliente de Prueba SRL"
    assert LeerIni(clave="base") == "sqlite"

    # Y en la carpeta del programa no se escribio nada.
    assert list(programa.iterdir()) == []

    # Con la configuracion guardada, ya no es el primer arranque.
    assert instalacion.es_primer_arranque() is False


def test_el_cuit_se_normaliza_tambien(tmp_path, monkeypatch):
    """El paso que va despues del asistente tambien tiene que poder escribir."""
    programa = tmp_path / "programa"
    programa.mkdir()
    datos = tmp_path / "datos"
    datos.mkdir()

    monkeypatch.chdir(str(programa))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _sin_permiso_de_escritura(monkeypatch)

    instalacion.guardar_config_inicial(dict(DATOS_ASISTENTE))

    normalizado = instalacion.normalizar_cuit_emisor()
    assert normalizado["estado"] == "ok"
    assert normalizado["cuit"] == "30111111126"
    assert LeerIni(clave="cuit", key="WSFEv1") == "30111111126"


def test_normalizar_el_cuit_no_tira_si_no_se_puede_guardar():
    """Un arreglo que no se puede guardar avisa; no mata el arranque.

    Antes el error subia desde `grabar(...)` y la app no abria, cuando lo unico
    que estaba haciendo era una correccion de una clave.
    """
    def falla(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied")

    resultado = instalacion.normalizar_cuit_emisor(
        grabar=falla,
        leer=lambda clave=None, key=None: {
            ("cuit", "FACTURA"): "30-11111112-6",
            ("cuit", "WSFEv1"): "",
        }.get((clave, key), ""))

    assert resultado["estado"] == "nada"
    assert resultado["sin_guardar"] is True


# -- El error tiene que ser entendible --------------------------------------


def test_no_se_puede_abrir_el_ini_por_una_carpeta(tmp_path, monkeypatch):
    """GrabarIni no deja escapar un error pelado de permisos.

    Se arma el problema de verdad: en vez del archivo, hay una carpeta con ese
    nombre, y `open(..., 'w')` falla con PermissionError. El error que sale
    tiene que decir que archivo es y que hacer, porque eso es lo que ve el
    usuario en la pantalla.
    """
    monkeypatch.chdir(tmp_path)
    # Un directorio con el nombre del archivo: no se puede abrir para escribir.
    (tmp_path / "sistema.ini").mkdir()

    with pytest.raises(ErrorEscrituraConfig) as error:
        GrabarIni(clave="base", key="param", valor="sqlite")

    mensaje = str(error.value)
    assert str(tmp_path / "sistema.ini") in mensaje
    assert "Program Files" in mensaje
    # Es un OSError: el codigo que ya lo maneja como tal sigue sirviendo.
    assert isinstance(error.value, OSError)


# -- Migracion de una instalacion que ya existia ---------------------------


def test_la_migracion_trae_el_ini_y_la_base(tmp_path):
    """Un cliente que ya usaba el sistema no puede aparecer como vacio."""
    programa = tmp_path / "programa"
    programa.mkdir()
    (programa / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nconfigurado = S\nempresa = Cliente Real\n",
        encoding="utf-8")
    (programa / "sistema.db").write_bytes(b"contenido de la base")
    datos = tmp_path / "datos"
    datos.mkdir()

    copiados = rutas.migrar_desde_instalacion(str(programa), str(datos))

    assert set(copiados) == {"sistema.ini", "sistema.db"}
    assert (datos / "sistema.db").read_bytes() == b"contenido de la base"
    assert "configurado = S" in (datos / "sistema.ini").read_text(encoding="utf-8")
    # El original queda donde estaba: no se borra nada.
    assert (programa / "sistema.ini").is_file()


def test_la_migracion_trae_una_base_con_otro_nombre(tmp_path):
    """Con `usa_nombre_db = S` la base se llama como el `basedatos`.

    Si la migracion solo mirara `sistema.db`, ese cliente se encontraria con la
    base vacia: la app abre, no dice nada raro, y no tiene un solo comprobante.
    """
    programa = tmp_path / "programa"
    programa.mkdir()
    (programa / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nusa_nombre_db = S\nbasedatos = servin\n",
        encoding="utf-8")
    (programa / "servin.db").write_bytes(b"la base de servin")
    (programa / "no-es-la-base.txt").write_text("hola", encoding="utf-8")
    datos = tmp_path / "datos"
    datos.mkdir()

    copiados = rutas.migrar_desde_instalacion(str(programa), str(datos))

    assert set(copiados) == {"sistema.ini", "servin.db"}
    assert (datos / "servin.db").read_bytes() == b"la base de servin"
    assert not (datos / "no-es-la-base.txt").exists()


def test_la_migracion_no_pisa_lo_que_ya_esta(tmp_path):
    """Lo que el usuario ya configuro en la carpeta nueva manda."""
    programa = tmp_path / "programa"
    programa.mkdir()
    (programa / "sistema.ini").write_text("[param]\nempresa = Viejo\n",
                                          encoding="utf-8")
    datos = tmp_path / "datos"
    datos.mkdir()
    (datos / "sistema.ini").write_text("[param]\nempresa = Nuevo\n",
                                       encoding="utf-8")

    copiados = rutas.migrar_desde_instalacion(str(programa), str(datos))

    assert copiados == {}
    assert "Nuevo" in (datos / "sistema.ini").read_text(encoding="utf-8")


def test_migrar_sobre_si_mismo_no_hace_nada(tmp_path):
    """Instalacion portable: la carpeta de datos es la del programa."""
    (tmp_path / "sistema.ini").write_text("[param]\nbase = sqlite\n",
                                          encoding="utf-8")

    assert rutas.migrar_desde_instalacion(str(tmp_path), str(tmp_path)) == {}


def test_migrar_una_carpeta_vacia_no_falla(tmp_path):
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    destino = tmp_path / "destino"
    destino.mkdir()

    assert rutas.migrar_desde_instalacion(str(vacio), str(destino)) == {}


# -- El arranque completo ---------------------------------------------------
#
# `main._asegurar_carpeta_de_trabajo` es el que deja el directorio de trabajo
# en la carpeta de la app. Si devuelve la carpeta del programa, el resto del
# arrangement se apoya sobre una carpeta en la que no se puede escribir.


def test_el_arranque_avisa_cuando_los_datos_no_van_a_la_carpeta_del_programa(
        tmp_path, monkeypatch, capsys):
    import main

    programa = tmp_path / "programa"
    programa.mkdir()
    datos = tmp_path / "datos"
    datos.mkdir()

    monkeypatch.setattr(main, "_carpeta_de_la_app", lambda: str(programa))
    monkeypatch.setenv("LOCALAPPDATA", str(datos))
    _sin_permiso_de_escritura(monkeypatch)

    resultado = main._asegurar_carpeta_de_trabajo()

    assert resultado == str(datos / "Asiento")
    # Los logs van ahi, no a una carpeta en la que no se puede escribir.
    assert os.path.isdir(str(datos / "Asiento"))
    # Y el directorio de trabajo sigue siendo el de la app: de ahi se leen
    # las plantillas y las imagenes.
    assert os.path.normcase(os.getcwd()) == os.path.normcase(str(programa))

    salida = capsys.readouterr().out
    assert "no se puede escribir" in salida
    assert str(datos / "Asiento") in salida


def test_el_arranque_no_suplica_si_los_datos_van_en_la_carpeta_del_programa(
        tmp_path, monkeypatch, capsys):
    import main

    programa = tmp_path / "programa"
    programa.mkdir()

    monkeypatch.setattr(main, "_carpeta_de_la_app", lambda: str(programa))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "no-se-usa"))
    monkeypatch.setattr(rutas, "puede_escribir", _escribible_siempre)
    rutas.limpiar_cache()

    resultado = main._asegurar_carpeta_de_trabajo()

    assert os.path.normcase(resultado) == os.path.normcase(str(programa))
    assert "no se puede escribir" not in capsys.readouterr().out
    # El sistema.ini se creo en la carpeta del programa, como siempre.
    assert (programa / "sistema.ini").is_file()
    assert LeerIni(clave="iniciosistema") == str(programa) + "/"


# -- La base real ----------------------------------------------------------


def test_la_base_se_crea_en_la_carpeta_de_datos(tmp_path):
    """Importa el modelo de verdad, en un proceso aparte, y mira donde apunta.

    Va en un subproceso porque `modelos.ModeloBase` lee la configuracion al
    importarse: si se importara aca, el resto de la suite veria la base de este
    test.
    """
    import subprocess

    programa = tmp_path / "programa"
    programa.mkdir()
    datos = tmp_path / "datos"
    datos.mkdir()
    # La configuracion tiene que estar en la carpeta de datos: es ahi donde la
    # va a leer el modelo. Sin `base = sqlite` entra por la rama de MySQL.
    destino = datos / "Asiento"
    destino.mkdir()
    (destino / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nconfigurado = S\n", encoding="utf-8")

    codigo = (
        "import os, sys\n"
        "sys.path.insert(0, {!r})\n"
        "os.chdir({!r})\n"
        "from libs import rutas\n"
        "rutas.limpiar_cache()\n"
        "import modelos.ModeloBase as m\n"
        "print(m.db.database)\n"
    ).format(REPO, str(programa))

    proceso = subprocess.run([sys.executable, "-c", codigo],
                             capture_output=True, text=True, timeout=180,
                             env=dict(os.environ,
                                      LOCALAPPDATA=str(datos),
                                      PYFE_CARPETA_DATOS=str(destino)))
    assert proceso.returncode == 0, proceso.stderr
    assert proceso.stdout.strip().endswith(os.path.join("Asiento", "sistema.db"))
    # Y el archivo no se crea todavia: peewee abre la base en el primer uso.
    assert not (destino / "sistema.db").exists()
