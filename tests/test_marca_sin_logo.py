"""La marca sin logo tiene que aplicar el resto igual.

El caso que reporto el operador
------------------------------
Cargo colores, web y leyenda, active el interruptor, y el comprobante salio
igual que sin marca. Sin aviso.

La causa: aplicar_marca_factura() tenia 'if not logo...: return False', y
devuelto eso se iba sin agregar ni el fondo, ni la web, ni la leyenda, ni los
colores. O sea que TODA la marca dependia de que hubiera un logo. Un cliente
que quiere solo su color de acento y su web, y no tiene logo, no podia tener
marca, y la pantalla no le decia nada.

Estos tests fijan que cada parte es independiente, y que lo que no se pudo
aplicar se devuelve para que la pantalla lo muestre.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class _PyFepdfDoble(object):
    """Anota lo que se le agregaria, sin dibujar nada."""

    def __init__(self):
        self.datos = []
        self.campos = []

    def AgregarDato(self, nombre, valor):
        self.datos.append((nombre, valor))

    def AgregarCampo(self, nombre, *args):
        # El nombre va aparte: en args[0] esta el TIPO ('I' o 'T').
        self.campos.append((nombre, args, {}))


def test_sin_logo_salen_la_web_y_la_leyenda(tmp_path):
    from controladores.FacturaBranding import (ConfigMarcaFactura,
                                               aplicar_marca_factura)

    pyfpdf = _PyFepdfDoble()
    config = ConfigMarcaFactura(
        activa=True,
        logo="",                       # <- no hay logo, y NO importa
        fondo="",
        web="cliente.com.ar",
        leyenda="Documento comercial.",
    )

    pendientes = aplicar_marca_factura(pyfpdf, str(tmp_path), config)

    nombres = [nombre for nombre, _args, _ in pyfpdf.campos]
    assert "marca-web" in nombres, \
        "sin logo no sale la web: la marca entera dependia del logo"
    assert "marca-leyenda" in nombres, \
        "sin logo no sale la leyenda"
    assert not pyfpdf.datos, "no hay logo, no deberia agregar el dato logo"
    assert pendientes == [], "no quedo nada sin aplicar: {}".format(pendientes)


def test_un_logo_inexistente_no_se_traga_al_resto(tmp_path):
    """Se avisa el logo que falta, pero el resto se aplica igual."""
    from controladores.FacturaBranding import (ConfigMarcaFactura,
                                               aplicar_marca_factura)

    pyfpdf = _PyFepdfDoble()
    config = ConfigMarcaFactura(
        activa=True,
        logo=str(tmp_path / "no-existe.png"),
        web="cliente.com.ar",
    )

    pendientes = aplicar_marca_factura(pyfpdf, str(tmp_path), config)

    nombres = [nombre for nombre, _args, _ in pyfpdf.campos]
    assert "marca-web" in nombres, "un logo roto se llevo la web con el"
    assert any("no-existe.png" in p for p in pendientes), \
        "no aviso que el logo no esta: {}".format(pendientes)


def test_un_fondo_inexistente_no_se_traga_al_resto(tmp_path):
    from controladores.FacturaBranding import (ConfigMarcaFactura,
                                               aplicar_marca_factura)

    pyfpdf = _PyFepdfDoble()
    config = ConfigMarcaFactura(
        activa=True,
        fondo=str(tmp_path / "no-existe.png"),
        leyenda="Documento comercial.",
    )

    pendientes = aplicar_marca_factura(pyfpdf, str(tmp_path), config)

    nombres = [nombre for nombre, _args, _ in pyfpdf.campos]
    assert "marca-leyenda" in nombres
    assert any("no-existe.png" in p for p in pendientes)
    assert "marca-fondo" not in nombres, "agrego un fondo que no existe"


def test_desactivada_no_devuelve_pendientes(tmp_path):
    from controladores.FacturaBranding import (ConfigMarcaFactura,
                                               aplicar_marca_factura)

    pendientes = aplicar_marca_factura(_PyFepdfDoble(), str(tmp_path),
                                       ConfigMarcaFactura(activa=False))
    assert pendientes == []


def test_todo_en_su_lugar_devuelve_lista_vacia(tmp_path):
    """El camino feliz: logo y fondo existen, no hay nada que avisar."""
    from controladores.FacturaBranding import (ConfigMarcaFactura,
                                               aplicar_marca_factura)

    logo = tmp_path / "logo.png"
    fondo = tmp_path / "fondo.png"
    logo.write_bytes(b"x")
    fondo.write_bytes(b"x")

    pyfpdf = _PyFepdfDoble()
    pendientes = aplicar_marca_factura(
        pyfpdf, str(tmp_path),
        ConfigMarcaFactura(activa=True, logo=str(logo), fondo=str(fondo),
                           web="w", leyenda="l"))

    assert pendientes == [], pendientes
    assert ("logo", str(logo)) in pyfpdf.datos
    nombres = [nombre for nombre, _args, _ in pyfpdf.campos]
    assert "marca-fondo" in nombres
    assert "marca-web" in nombres
    assert "marca-leyenda" in nombres
