"""El boton 'Genera' tiene que generar el CSR de verdad.

Que estaba pasando
------------------
El metodo era una sola linea sin llamada:

    wsaa = WSAA()
    wsaa.CrearPedidoCertificado        <- sin parentesis, no hace nada

Apretarlo no pasaba nada y no habia ningun aviso, asi que la pantalla parecia
rota. Y es la pantalla por la que pasa cualquier cliente que quiere emitir.

El CUIT va en el subject del CSR y ARCA usa ese valor para emitir el
certificado, asi que uno mal obliga a repetir todo con una clave nueva. Por eso
la validacion va ANTES de generar la clave, y no despues: una clave RSA se
genera una sola vez y no se tira.

Estos tests usan la criptografia de verdad, con una clave de 2048 bits para que
no tarden. Lo que se prueba es que el boton produce los dos archivos y que no
produce nada con datos malos.
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# 20-23347203-5: el CUIT de los certificados que hay en el repo, con digito
# verificador valido.
CUIT_BUENO = "20-23347203-5"
CUIT_MALO = "20-23347203-4"


class _Senal(object):
    """Lo unico que se le pide a una senal: connect()."""

    def connect(self, *args, **kwargs):
        return None


class _Boton(object):
    """Un boton: tiene una senal clicked, como un Boton de verdad."""

    def __init__(self):
        self.clicked = _Senal()


class _Vista(object):
    """Una vista de mentira con los cuatro campos y los dos botones."""

    class _Entrada(object):
        def __init__(self):
            self._texto = ""

        def setText(self, texto):
            self._texto = texto

        def text(self):
            return self._texto

    def __init__(self):
        self.controles = {n: self._Entrada() for n in
                          ("cuit", "empresa", "nombre", "archivo")}
        self.btnCerrar = _Boton()
        self.btnGenera = _Boton()
        self.Cerrar = lambda: None


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def avisos(monkeypatch):
    """Anota los showAlert / showError / showConfirmation."""
    import libs.Ventanas as V

    vistos = []

    def _alert(titulo, mensaje, *a, **kw):
        vistos.append(("alert", titulo, mensaje))

    def _error(titulo, mensaje, que_hacer=None, detalle=None):
        vistos.append(("error", titulo, mensaje))

    def _confirmar(titulo, mensaje, **kw):
        vistos.append(("confirm", titulo, mensaje))
        return False

    monkeypatch.setattr(V, "showAlert", _alert)
    monkeypatch.setattr(V, "showError", _error)
    monkeypatch.setattr(V, "showConfirmation", _confirmar)

    class _Progreso(object):
        def __init__(self, titulo, etapas):
            self.titulo = titulo

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def avanzar(self, nombre):
            return None

    monkeypatch.setattr(V, "Progreso", _Progreso)
    return vistos


@pytest.fixture
def controlador(qt, monkeypatch):
    import controladores.GeneraCertificados as G

    monkeypatch.setattr(G, "GeneraCertificadoView", _Vista)
    # 2048 en vez de 4096: el test no necesita la llave mas larga y asi tarda
    # segundos en vez de un minuto.
    monkeypatch.setattr(G.WSAA, "CrearClavePrivada",
                        _crear_clave_corta())
    c = G.GeneraCertificadosController()
    c.view.Cerrar = lambda: None
    return c


def _crear_clave_corta():
    from pyafipws.wsaa import WSAA
    original = WSAA.CrearClavePrivada

    def _corta(self, filename="privada.key", key_length=2048,
               pub_exponent=0x10001, passphrase=""):
        return original(self, filename=filename, key_length=key_length,
                        pub_exponent=pub_exponent, passphrase=passphrase)

    return _corta


def _preparar(controlador, cuit=CUIT_BUENO, empresa="VOGEL CONSULTORIA",
              nombre="Oscar Vogel", archivo=None):
    if archivo is None:
        archivo = os.path.join(tempfile.mkdtemp(prefix="csr_"), "pedido.csr")
    c = controlador.view.controles
    c['cuit'].setText(cuit)
    c['empresa'].setText(empresa)
    c['nombre'].setText(nombre)
    c['archivo'].setText(archivo)
    return archivo


# -- El camino que importa -------------------------------------------------

def test_el_boton_genera_la_clave_y_el_csr(controlador, avisos):
    """El bug: el boton no hacia nada."""
    ruta_csr = _preparar(controlador)

    assert controlador.onClickBtnGenera() is True

    assert os.path.isfile(ruta_csr), "no se genero el CSR"
    assert os.path.getsize(ruta_csr) > 100, "el CSR salio vacio"

    ruta_clave = os.path.join(os.path.dirname(ruta_csr), "clave_privada_homo.key")
    assert os.path.isfile(ruta_clave), "no se genero la clave privada"


def test_el_csr_lleva_el_cuit_que_puso_el_usuario(controlador, avisos):
    """ARCA emite el certificado con el CUIT del CSR: tiene que ser el pedido."""
    ruta_csr = _preparar(controlador)
    controlador.onClickBtnGenera()

    with open(ruta_csr, "rb") as f:
        contenido = f.read().decode("utf-8", "replace")

    # El CSR va en PEM, en base64. Con una asercion sobre el texto crudo no se
    # ve el CUIT, asi que se lee con la misma libreria que lo firmo.
    from cryptography import x509
    with open(ruta_csr, "rb") as f:
        peticion = x509.load_pem_x509_csr(f.read())

    atributos = {a.oid._name: a.value for a in peticion.subject}
    assert "20-23347203" in str(atributos.get("serialNumber", "")), \
        "el CSR no lleva el CUIT: {}".format(atributos)


def test_el_csr_esta_firmado(controlador, avisos):
    """Sin firma ARCA lo rechaza, y no avisa de nada."""
    ruta_csr = _preparar(controlador)
    controlador.onClickBtnGenera()

    from cryptography import x509
    with open(ruta_csr, "rb") as f:
        peticion = x509.load_pem_x509_csr(f.read())

    assert peticion.is_signature_valid, "el CSR no esta firmado"


def test_avisa_los_pasos_de_arca(controlador, avisos):
    """La parte que no se adivina: que hacer con el CSR."""
    _preparar(controlador)
    controlador.onClickBtnGenera()

    alertas = [a for a in avisos if a[0] == "alert"]
    assert alertas, "no aviso nada: el operador no sabe que hacer con el CSR"
    texto = alertas[-1][2]
    assert "ManageARCA" in texto
    assert "certificado_homologacion.crt" in texto, \
        "no dice con que nombre guardar el certificado que devuelve ARCA"


# -- Los caminos donde NO tiene que generar nada ---------------------------

def test_un_cuit_invalido_no_genera_nada(controlador, avisos):
    """Se valida antes de gastar la clave: no se tira y se repite."""
    carpeta = tempfile.mkdtemp(prefix="csr_malo_")
    ruta_csr = os.path.join(carpeta, "pedido.csr")
    _preparar(controlador, cuit=CUIT_MALO, archivo=ruta_csr)

    assert controlador.onClickBtnGenera() is False

    assert not os.path.exists(ruta_csr), "genero un CSR con un CUIT invalido"
    assert not os.path.exists(os.path.join(carpeta, "clave_privada_homo.key")), \
        "gasto la clave privada con un CUIT invalido"
    assert any("CUIT no es valido" in a[2] for a in avisos)


def test_sin_archivo_no_genera_nada(controlador, avisos):
    _preparar(controlador)
    controlador.view.controles['archivo'].setText("")

    assert controlador.onClickBtnGenera() is False
    assert any("donde guardar" in a[2] for a in avisos)


def test_sin_razon_social_no_genera_nada(controlador, avisos):
    _preparar(controlador, empresa="")

    assert controlador.onClickBtnGenera() is False
    assert any("razon social" in a[2] for a in avisos)


def test_una_clave_existente_pide_confirmacion(controlador, avisos):
    """Reemplazar la clave invalida lo que se haya firmado antes.

    Con el fingerprint de la clave nueva, todos los certificados hechos con la
    vieja dejan de servir. Por eso pregunta en vez de pisar.
    """
    carpeta = tempfile.mkdtemp(prefix="csr_pide_")
    ruta_clave = os.path.join(carpeta, "clave_privada_homo.key")
    with open(ruta_clave, "w") as f:
        f.write("una clave cualquiera")

    _preparar(controlador, archivo=os.path.join(carpeta, "pedido.csr"))

    assert controlador.onClickBtnGenera() is False
    with open(ruta_clave) as f:
        assert f.read() == "una clave cualquiera", "la clave se piso sin preguntar"
    assert any(a[0] == "confirm" for a in avisos)
