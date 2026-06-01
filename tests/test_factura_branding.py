from pathlib import Path


class PyFepdfDoble:
    def __init__(self):
        self.campos = []
        self.datos = []

    def AgregarCampo(self, *args, **kwargs):
        self.campos.append((args, kwargs))
        return True

    def AgregarDato(self, *args):
        self.datos.append(args)
        return True


def test_config_marca_desactivada_no_aplica_nada(tmp_path):
    from controladores.FacturaBranding import ConfigMarcaFactura, aplicar_marca_factura

    pyfpdf = PyFepdfDoble()
    config = ConfigMarcaFactura(activa=False)

    assert aplicar_marca_factura(pyfpdf, tmp_path, config) is False
    assert pyfpdf.campos == []
    assert pyfpdf.datos == []


def test_config_marca_parametrizada_agrega_logo_fondo_y_textos(tmp_path):
    from controladores.FacturaBranding import ConfigMarcaFactura, aplicar_marca_factura

    logo = tmp_path / "logo-cliente.png"
    fondo = tmp_path / "fondo-cliente.png"
    logo.write_bytes(b"logo")
    fondo.write_bytes(b"fondo")

    pyfpdf = PyFepdfDoble()
    config = ConfigMarcaFactura(
        activa=True,
        logo=str(logo),
        fondo=str(fondo),
        web="cliente.com.ar",
        leyenda="Documento comercial parametrizado.",
        color_primario="#112233",
        color_acento="#AABBCC",
    )

    assert aplicar_marca_factura(pyfpdf, tmp_path, config) is True
    assert ("logo", str(logo)) in pyfpdf.datos
    nombres = [args[0] for args, kwargs in pyfpdf.campos]
    assert "marca-fondo" in nombres
    assert "marca-web" in nombres
    assert "marca-leyenda" in nombres


def test_crear_ejemplo_vogel_deja_assets_versionables(tmp_path):
    from controladores.FacturaBranding import crear_ejemplo_vogel

    origen_logo = tmp_path / "origen-logo.png"
    origen_logo.write_bytes(b"logo")

    ejemplo = crear_ejemplo_vogel(tmp_path, fuentes_logo=[str(origen_logo)])

    assert ejemplo.logo == tmp_path / "plantillas" / "logo-vogel-ejemplo.png"
    assert ejemplo.logo.read_bytes() == b"logo"
    assert ejemplo.fondo == tmp_path / "plantillas" / "factura-fondo-vogel-ejemplo.png"
    assert ejemplo.fondo.exists()


def test_obtener_formato_factura_usa_formato_marca_si_esta_activa(tmp_path):
    from controladores.FacturaBranding import ConfigMarcaFactura, obtener_formato_factura

    formato = tmp_path / "plantillas" / "factura-marca-cliente.csv"
    formato.parent.mkdir()
    formato.write_text("'Logo';'I';1;1;2;2;None;0;0;0;0;0;0;'I';'';0\n")

    config = ConfigMarcaFactura(activa=True, formato="plantillas/factura-marca-cliente.csv")

    assert obtener_formato_factura(tmp_path, config, "plantillas/factura_qr.csv") == formato


def test_obtener_formato_factura_vuelve_al_default_si_no_hay_formato(tmp_path):
    from controladores.FacturaBranding import ConfigMarcaFactura, obtener_formato_factura

    config = ConfigMarcaFactura(activa=True, formato="plantillas/no-existe.csv")

    assert obtener_formato_factura(tmp_path, config, "plantillas/factura_qr.csv") == tmp_path / "plantillas" / "factura_qr.csv"
