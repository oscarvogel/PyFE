# coding=utf-8
"""El build del demo: carpeta de datos propia y actualizador apagado.

Por que estos tests existen
---------------------------
El demo se puede instalar en la maquina de un cliente que ya tiene Asiento de
produccion. Si las dos apps usaran `%LOCALAPPDATA%\\Asiento`, el demo abriria la
base REAL del cliente. Y si el demo tuviera el actualizador encendido, una
maquina de demo podria terminar bajando el instalador de PRODUCCION y
ejecutandolo encima de sus datos de prueba.

Son dos riesgos que no se ven mirando una pantalla: ninguno da error, dan
"funciona" mientras hacen algo que no tiene que pasar. Cada test ata una regla
a una condicion observable.
"""

import io
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

APP_ID_DEMO = "asiento-demo"


@pytest.fixture(autouse=True)
def _cache_de_rutas_limpia():
    """No dejar la carpeta de datos resuelta para los tests que siguen.

    `libs.rutas` cachea la carpeta de datos por directorio de trabajo. Este
    archivo resuelve la del demo, y si el resultado queda cacheado para la
    carpeta del repo, los tests que dependen del `sistema.ini` del repo
    (armar un comprobante, por ejemplo) leen una ruta que ya no existe: el CUIT
    vuelve vacio y `int('')` revienta a mitad del PDF.

    El mensaje del error no dice nada de su causa -- parece un bug de
    facturacion -- y los tests que fallan no tienen nada que ver con el demo.
    Es el mismo motivo por el que `tests/test_carpeta_datos.py` limpia la cache
    en un fixture autouse.
    """
    from libs import rutas

    antes = os.getcwd()
    rutas.limpiar_cache()
    yield
    rutas.limpiar_cache()
    if os.getcwd() != antes:
        os.chdir(antes)


# -- La carpeta de datos del demo ------------------------------------------


def test_el_demo_usa_una_carpeta_de_datos_propia():
    """La regla que evita que el demo abra la base del cliente."""
    from libs.build_info import nombre_build

    assert nombre_build(APP_ID_DEMO) == "Asiento DEMO"
    assert nombre_build("asiento") == "Asiento"


def test_los_dos_pueden_convivir_en_la_misma_maquina(tmp_path, monkeypatch):
    """Dos app_id, dos carpetas. Una no ve los datos de la otra.

    El caso que importa es el de la maquina con la carpeta del programa de solo
    lectura (la instalacion vieja en `Program Files`): ahi los datos caen
    siempre en `%LOCALAPPDATA%`, y es donde el demo se apoyaria encima de la
    base del cliente si compartieran nombre.
    """
    from libs import rutas

    local = tmp_path / "localappdata"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.delenv(rutas.ENV_CARPETA_DATOS, raising=False)
    # Carpeta del programa de solo lectura: los datos van a la del usuario.
    monkeypatch.setattr(rutas, "puede_escribir", lambda carpeta, probar=None: False)

    monkeypatch.setattr("libs.build_info.APP_ID", "asiento")
    rutas.limpiar_cache()
    produccion = rutas.carpeta_datos()

    monkeypatch.setattr("libs.build_info.APP_ID", APP_ID_DEMO)
    rutas.limpiar_cache()
    demo = rutas.carpeta_datos()

    assert produccion != demo
    assert os.path.basename(produccion) == "Asiento"
    assert os.path.basename(demo) == "Asiento DEMO"
    assert produccion.endswith(os.path.join("Asiento"))
    assert demo.endswith(os.path.join("Asiento DEMO"))


def test_en_desarrollo_sigue_el_de_produccion():
    """`development` no es una app mas: usa el nombre de siempre.

    Si no, cambiar el `sistema.ini` del repo no cambiaria nada en una maquina
    donde el demo ya se habia abierto alguna vez.
    """
    from libs.build_info import nombre_build

    assert nombre_build("development") == "Asiento"


def test_un_app_id_desconocido_no_inventa_un_nombre():
    """Se resuelve por tabla, no por formato: lo no registrado cae en el de
    produccion, que es lo seguro (no deja los datos colgados en un lado)."""
    from libs.build_info import nombre_build

    assert nombre_build("inventado") == "Asiento"


# -- El nombre que ve el operador ------------------------------------------
#
# Se prueban las ventanas DE VERDAD, no el texto del codigo. Un test que
# grepea "no aparece NOMBRE_PRODUCTO" pasa igual si el titulo se calcula con
# logica rota: no dice nada de lo que el operador ve.


@pytest.fixture
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _ventana_principal():
    from vistas.Main import MainView

    ventana = MainView()
    ventana.initUi()   # sin esto la vista existe pero esta vacia
    return ventana


def test_la_ventana_principal_del_demo_dice_demo(app, monkeypatch):
    """El error que mas se cuela en una demo: parecerse a produccion.

    Si el demo se presenta como "Asiento" a secas, el operador no tiene forma
    de saber que esta en la maquina de pruebas. Y si emite ahi, el comprobante
    queda con el CUIT de la maquina de la demo.
    """
    monkeypatch.setattr("libs.build_info.APP_ID", APP_ID_DEMO)

    ventana = _ventana_principal()
    try:
        assert ventana.windowTitle() == "Asiento DEMO"
    finally:
        ventana.close()


def test_el_saludo_de_la_pantalla_principal_dice_demo(app, monkeypatch):
    """No solo el titulo de la barra: tambien lo que se lee en el medio."""
    from PyQt5.QtWidgets import QLabel

    monkeypatch.setattr("libs.build_info.APP_ID", APP_ID_DEMO)

    ventana = _ventana_principal()
    try:
        textos = [lbl.text() for lbl in ventana.findChildren(QLabel)]
        assert "Asiento DEMO" in textos
    finally:
        ventana.close()


def test_el_asistente_del_demo_se_presenta_como_demo(app, monkeypatch):
    """El primer arranque tiene que ofrecer el nombre ya puesto.

    `txtNombreSistema` es lo que el operador ve antes de confirmar, y de ahi
    sale `param.nombre_sistema`, que despues usan todos los avisos de la app.
    """
    from vistas.PrimerArranque import DialogoPrimerArranque

    monkeypatch.setattr("libs.build_info.APP_ID", APP_ID_DEMO)

    dlg = DialogoPrimerArranque()
    try:
        assert "Asiento DEMO" in dlg.windowTitle()
        assert dlg.txtNombreSistema.text() == "Asiento DEMO"
    finally:
        dlg.close()


def test_en_produccion_el_titulo_no_dice_demo(app, monkeypatch):
    """La otra mitad: produccion no puede quedar con 'DEMO' pegado."""
    monkeypatch.setattr("libs.build_info.APP_ID", "asiento")

    ventana = _ventana_principal()
    try:
        assert ventana.windowTitle() == "Asiento"
        assert "DEMO" not in ventana.windowTitle()
    finally:
        ventana.close()


def test_la_configuracion_guarda_el_nombre_del_demo(tmp_path, monkeypatch):
    """Lo que el asistente escribe, leido de verdad con el LeerIni real."""
    from libs import instalacion
    from libs.Utiles import LeerIni

    datos = tmp_path / "datos"
    datos.mkdir()
    monkeypatch.chdir(str(datos))
    monkeypatch.setattr("libs.build_info.APP_ID", APP_ID_DEMO)

    instalacion.guardar_config_inicial({
        "base": "sqlite", "empresa": "Cliente de Prueba",
        "cuit": "30111111126", "homo": "S",
    })

    assert LeerIni(clave="nombre_sistema", key="param") == "Asiento DEMO"


# -- El actualizador tiene que estar apagado -------------------------------


def test_el_demo_no_tiene_actualizador():
    """El build del demo no se actualiza solo. Nunca.

    Este es el test mas importante de los dos grupos: si el demo se encendiera,
    una maquina de demostracion podria descargar el instalador de produccion y
    ejecutarlo sobre la base de pruebas, sin que nadie pidiera nada.
    """
    from libs.actualizaciones import UpdateService

    servicio = UpdateService(app_id=APP_ID_DEMO)
    assert servicio.habilitado is False
    # Y sin manifiesto no hay contra que compararse.
    assert servicio.manifest_url is None


def test_produccion_sigue_pudiendo_actualizarse():
    """El cambio no puede apagar el canal de produccion."""
    from libs.actualizaciones import UpdateService

    servicio = UpdateService(app_id="asiento")
    assert servicio.manifest_url is not None
    assert servicio.habilitado is True


def test_desarrollo_sigue_deshabilitado():
    from libs.actualizaciones import UpdateService

    assert UpdateService(app_id="development").habilitado is False


# -- El changelog del demo -------------------------------------------------


def test_el_changelog_de_un_app_sin_historial_no_rompe():
    """`fetch()` tiene que devolver lista vacia, no levantar ValueError.

    Antes la URL se resolvia fuera del try. Con un app_id sin historial
    registrado -- el demo -- eso reventaba. Hoy el demo no llega aca porque su
    `es_build_productivo()` es False, pero el try tiene que estar.
    """
    from libs.changelog import ChangelogService

    servicio = ChangelogService(app_id=APP_ID_DEMO)
    assert servicio.fetch() == []
    assert servicio.pending([]) == []


def test_el_demo_no_tiene_app_id_productivo():
    """El demo no puede entrar al canal de actualizaciones por accidente.

    `es_build_productivo()` mira si el app_id esta en la tabla de manifiestos.
    Si alguien agrega el demo ahi, esto avisa.
    """
    from libs.build_info import APP_ID, es_build_productivo, manifest_url_for

    assert APP_ID == "development"   # el arbol esta en desarrollo
    assert es_build_productivo() is False
    with pytest.raises(ValueError):
        manifest_url_for(APP_ID_DEMO)


# -- El instalador del demo ------------------------------------------------


def _installer(nombre):
    with io.open(os.path.join(REPO, "installer", nombre),
                 encoding="utf-8") as fh:
        return fh.read()


def test_el_instalador_del_demo_tiene_identidad_propia():
    """AppId y carpeta de programa distintos de los de produccion.

    Con el mismo AppId, instalar el demo en una maquina con produccion
    desinstalaria (o pisaria) la de produccion.
    """
    demo = _installer("Asiento_Demo.iss")
    produccion = _installer("Asiento.iss")

    id_demo = [l for l in demo.splitlines() if l.startswith("AppId=")][0]
    id_prod = [l for l in produccion.splitlines() if l.startswith("AppId=")][0]
    assert id_demo != id_prod

    assert "Asiento DEMO" in demo
    assert "{localappdata}\\Programs\\{#AppName}" in demo


def test_el_demo_se_instala_sin_privilegios():
    """Si el demo pidiera administrador, volveria el problema de la carpeta de
    solo lectura que se corrigio hoy en el instalador de produccion."""
    demo = _installer("Asiento_Demo.iss")
    assert "PrivilegesRequired=lowest" in demo
    assert "PrivilegesRequired=admin" not in demo


def test_el_demo_borra_la_base_al_reinstalarse():
    """Un demo reinstalado arranca de cero, como RND DEMO."""
    demo = _installer("Asiento_Demo.iss")
    assert "[InstallDelete]" in demo
    assert "sistema.db" in demo


# -- El certificado de homologacion ----------------------------------------


def test_la_carpeta_de_datos_del_instalador_es_la_que_mira_la_app():
    """El .iss escribe el sistema.ini: tiene que ser donde la app lee.

    Es el acoplamiento que nadie ve. El nombre de la carpeta de datos sale de
    nombre_build("asiento-demo") en el codigo, y el .iss lo tiene escrito
    aparte para poder escribir el sistema.ini antes de que arranque nada. Si
    uno cambia y el otro no, el instalador escribe la configuracion en una
    carpeta que la app no mira: el demo abre como recien instalado, vuelve el
    asistente y el certificado queda sin usar. No da ningun error.
    """
    import re

    from libs.build_info import nombre_build

    esperado = os.path.join("{localappdata}", nombre_build(APP_ID_DEMO))
    demo = _installer("Asiento_Demo.iss")

    # ISPP acepta el signo igual del #define como opcional, asi que se
    # matchea con el y sin el. Un test que solo mirara una forma daria un
    # falso verde si alguien reescribe la linea.
    patron = re.compile(r'^\s*#define\s+CarpetaDatos\s*=?\s*"([^"]+)"',
                        re.MULTILINE)
    encontrados = patron.findall(demo)
    assert encontrados, "el .iss ya no define CarpetaDatos"

    for valor in encontrados:
        assert valor == esperado, (
            "el .iss precarga datos en {} pero la app los lee en {}".format(
                valor, esperado))


def _defines_del_demo():
    """Los `#define` del .iss, como dict. El `=` es opcional en ISPP."""
    import re

    demo = _installer("Asiento_Demo.iss")
    return dict(re.findall(r'^\s*#define\s+(\w+)\s*=?\s*"([^"]*)"',
                           demo, re.MULTILINE))


def _entradas_ini_del_demo():
    """Las lineas de [INI] del .iss, como dict (seccion, clave) -> valor.

    Se parsea en vez de buscar texto: el formato cambio mas de una vez
    (secciones en bloque, despues Section/Key/String), y un assert con
    "configurado=S" in demo se rompe con cada formato sin avisar que el dato
    seguia ahi.

    Las constantes `{#Algo}` se expanden con los `#define` del mismo archivo,
    porque el .iss usa `{#AppName}` y no el texto literal: si el nombre del
    producto cambia, el .iss cambia solo y el test tiene que verlo igual.
    """
    import re

    demo = _installer("Asiento_Demo.iss")
    defines = _defines_del_demo()

    def expandir(texto):
        for _ in range(5):          # por si un define apunta a otro
            nuevo = re.sub(r"\{#(\w+)\}", lambda m: defines.get(m.group(1),
                                                                m.group(0)),
                           texto)
            if nuevo == texto:
                break
            texto = nuevo
        return texto

    patron = re.compile(
        r'Section:\s*"([^"]*)";\s*Key:\s*"([^"]*)";\s*String:\s*"(.*)"')
    entradas = {}
    for seccion, clave, valor in patron.findall(demo):
        entradas[(seccion, clave)] = expandir(valor)
    return entradas


def test_el_demo_precarga_la_configuracion_para_emitir():
    """El demo tiene que abrir listo, no pedir que lo configure uno."""
    from libs.instalacion import SECCION_CERT, SECCION_FACTURACION, SECCION_FISCAL

    ini = _entradas_ini_del_demo()
    assert ini, "el .iss ya no precarga ninguna clave con la seccion [INI]"

    # configurado = S es lo que hace que es_primer_arranque() de False y el
    # asistente no aparezca.
    assert ini.get(("param", "configurado")) == "S"
    assert ini.get(("param", "base")) == "sqlite"
    # Homologacion, siempre: el certificado que viaja es de prueba.
    assert ini.get(("param", "homo")) == "S"
    assert ini.get(("param", "nombre_sistema")) == "Asiento DEMO"

    # El CUIT tiene que ser el del certificado apretado en el paquete.
    assert ini.get((SECCION_FISCAL, "cuit")) == "20-23347203-5"

    # Las rutas del certificado tienen que ser las que el .iss copia.
    assert ini.get((SECCION_CERT, "cert_homo")) == \
        "certificados/certificado_homologacion.crt"
    assert ini.get((SECCION_CERT, "privatekey_homo")) == \
        "certificados/clave_privada_homo.key"
    # Las URLs de homologacion, y son las mismas que escribe
    # guardar_config_inicial(). Ojo: WSAA es `wsaahomo` y WSFE es `wswhomo`.
    # No es un typo, son dos servicios distintos.
    assert ini.get((SECCION_CERT, "url_homo")) == \
        "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
    assert ini.get((SECCION_FACTURACION, "url_homo")) == \
        "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
    # Las de produccion tambien estan escritas, como las escribe el asistente,
    # pero no se usan mientras `homo = S`. Lo que las apaga es esa clave, que
    # ya se verifica mas arriba: no que la URL este ausente.


def test_el_demo_no_apunta_a_produccion():
    """Lo de produccion tiene que quedar en un archivo que no existe.

    El paquete no trae certificado de produccion. Si el operador completara
    esos dos campos a mano, el demo emitiria DE VERDAD contra ARCA. Lo que se
    busca aca es que no venga cableado, no que se lo impongamos.
    """
    ini = _entradas_ini_del_demo()
    assert ini.get(("WSAA", "cert_prod")) == \
        "certificados/certificado_produccion.crt"
    assert ini.get(("WSAA", "privatekey_prod")) == \
        "certificados/clave_privada_produccion.key"

    demo = _installer("Asiento_Demo.iss")
    # Y que el instalador no escriba esos archivos en ningun lado.
    assert "demo-certificados\\certificado_produccion.crt" not in demo
    assert "demo-certificados\\clave_privada_produccion.key" not in demo


def test_el_demo_embarca_el_certificado_y_no_la_build_de_produccion():
    """El .crt/.key van por `[Files]` desde `installer/`, nunca desde `dist/`."""
    demo = _installer("Asiento_Demo.iss")
    assert 'Source: "demo-certificados\\certificado_homologacion.crt"' in demo
    assert 'Source: "demo-certificados\\clave_privada_homo.key"' in demo
    # Si el certificado estuviera en dist, la build de produccion lo subiria.
    assert "dist\\certificados" not in demo


def test_la_carpeta_del_certificado_no_entra_al_repo():
    """La clave privada no se commitea.

    Si esto se rompe, la primera corrida del script deja una clave privada de
    Vogel en el arbol y `git add -A` la sube al remoto.
    """
    with io.open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
        contenido = fh.read()
    assert "/installer/demo-certificados/" in contenido


# -- La herramienta que arma el certificado --------------------------------


def _certificado_de_prueba(tmp_path, cuit=20233472035, dias=300, con_clave=True):
    """Un .crt/.key propios, para no depender del certificado real de Vogel."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import datetime

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sujeto = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"demo"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, u"CUIT {}".format(cuit)),
    ])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    # `dias` es la vida que le queda. Para uno vencido va en negativo, y el
    # not_valid_before se va para atras para que el par siga siendo valido
    # como intervalo (si no, el constructor lo rechaza).
    cert = (x509.CertificateBuilder()
            .subject_name(sujeto)
            .issuer_name(sujeto)
            .public_key(clave.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(ahora - datetime.timedelta(days=abs(dias) + 30))
            .not_valid_after(ahora + datetime.timedelta(days=dias))
            .sign(clave, hashes.SHA256()))

    ruta_cert = str(tmp_path / "demo.crt")
    with open(ruta_cert, "wb") as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))

    ruta_clave = str(tmp_path / "demo.key")
    if con_clave:
        with open(ruta_clave, "wb") as fh:
            fh.write(clave.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()))
    return ruta_cert, ruta_clave


def test_la_herramienta_acepta_un_par_correcto(tmp_path):
    import tools.preparar_certificado_demo as prep

    ruta_cert, ruta_clave = _certificado_de_prueba(tmp_path)
    info = prep.validar(ruta_cert, ruta_clave, "20-23347203-5")
    assert info["cuit"] == "20233472035"
    assert info["dias"] > 0


def test_la_herramienta_rechaza_un_certificado_vencido(tmp_path):
    """Un demo con el certificado vencido abre bien y no emite: peor que nada.

    Sin este chequeo, el error aparece en la maquina del cliente, al autorizar
    el primer comprobante, sin relacion apparent con la instalacion.
    """
    import tools.preparar_certificado_demo as prep

    ruta_cert, ruta_clave = _certificado_de_prueba(tmp_path, dias=-10)
    with pytest.raises(prep.ErrorPreparacion) as error:
        prep.validar(ruta_cert, ruta_clave, "20-23347203-5")
    assert "vencio" in str(error.value).lower()


def test_la_herramienta_rechaza_una_clave_que_no_es_la_del_certificado(tmp_path):
    """Un par desarmado no falla al copiar: falla al autorizar, lejos."""
    import tools.preparar_certificado_demo as prep

    ruta_cert, _ = _certificado_de_prueba(tmp_path)
    otra = tmp_path / "otra"
    otra.mkdir()
    _, otra_clave = _certificado_de_prueba(otra)
    with pytest.raises(prep.ErrorPreparacion) as error:
        prep.validar(ruta_cert, otra_clave, "20-23347203-5")
    assert "NO es la del certificado" in str(error.value)


def test_la_herramienta_rechaza_el_certificado_del_cuit_que_no_es(tmp_path):
    """Pasar por error el certificado de PRODUCCION tiene que frenar el build.

    Si el .crt es del CUIT del cliente y no del de Vogel, el demo emitiria de
    verdad contra ARCA con la identidad fiscal de otra empresa.
    """
    import tools.preparar_certificado_demo as prep

    ruta_cert, ruta_clave = _certificado_de_prueba(tmp_path, cuit=20124067201)
    with pytest.raises(prep.ErrorPreparacion) as error:
        prep.validar(ruta_cert, ruta_clave, "20-23347203-5")
    assert "CUIT" in str(error.value)


def test_copiar_deja_los_nombres_que_la_app_espera(tmp_path, monkeypatch):
    """Los nombres tienen que coincidir con los de GeneraCertificados.

    Si el .iss los busca con otro nombre y el sistema.ini apunta al que espera
    la app, el certificado queda al lado pero sin usar.
    """
    import tools.preparar_certificado_demo as prep
    from controladores.GeneraCertificados import (
        NOMBRE_CERT_HOMOLOGACION, NOMBRE_CLAVE_HOMOLOGACION)

    assert prep.NOMBRE_CERT == NOMBRE_CERT_HOMOLOGACION
    assert prep.NOMBRE_CLAVE == NOMBRE_CLAVE_HOMOLOGACION

    destino = tmp_path / "demo-certificados"
    monkeypatch.setattr(prep, "DESTINO", str(destino))
    ruta_cert, ruta_clave = _certificado_de_prueba(tmp_path)
    salida_cert, salida_clave = prep.copiar(ruta_cert, ruta_clave)

    assert os.path.basename(salida_cert) == NOMBRE_CERT_HOMOLOGACION
    assert os.path.basename(salida_clave) == NOMBRE_CLAVE_HOMOLOGACION
    assert os.path.isfile(salida_cert) and os.path.isfile(salida_clave)