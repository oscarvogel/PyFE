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

    # Devuelve la lista de lo que no se pudo aplicar. Desactivada, no aplica
    # nada y por lo tanto no tiene nada que avisar.
    assert aplicar_marca_factura(pyfpdf, tmp_path, config) == []
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

    # Lista vacia: no quedo nada sin aplicar.
    assert aplicar_marca_factura(pyfpdf, tmp_path, config) == []
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

# -- CUIT del emisor ------------------------------------------------------

def test_el_cuit_de_la_factura_va_suelto_y_con_guiones():
    """El CUIT del emisor no puede ir con el rotulo pegado.

    Antes se imprimia 'CUIT: 20123456789' en un solo campo. Mal por dos
    motivos: el rotulo mezclado con el dato hace que el campo no se pueda leer
    ni copiar como numero, y un CUIT en un comprobante fiscal se muestra con
    guiones (XX-XXXXXXXX-X), que es como lo pone la mascara del campo de
    captura de la app.
    """
    import os

    raiz = Path(__file__).resolve().parent.parent
    faltan = []
    for carpeta in ("controladores", "vistas", "libs"):
        base = raiz / carpeta
        if not base.is_dir():
            continue
        for ruta in sorted(base.glob("*.py")):
            try:
                texto = ruta.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for i, linea in enumerate(texto.splitlines(), 1):
                if "AgregarDato" in linea and "CUIT" in linea and "CUIT:" in linea:
                    faltan.append("{}/{}:{} -> {}".format(
                        carpeta, ruta.name, i, linea.strip()))

    assert not faltan, (
        "el CUIT se sigue pasando con el rotulo pegado:\n  " + "\n  ".join(faltan))


def test_el_rotulo_del_cuit_existe_como_campo_propio():
    """El rotulo tiene que estar en el formato, en un campo aparte.

    Si se saca del codigo y no se agrega al .csv, la factura muestra el numero
    pelado y sin ninguna referencia de que es.
    """
    from libs.recursos import ruta_recurso

    for formato in ("factura_marca.csv", "factura_qr.csv"):
        ruta = ruta_recurso("plantillas/" + formato)
        assert ruta, "falta la plantilla {}".format(formato)
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            lineas = f.read().splitlines()

        campos = {}
        for linea in lineas:
            if linea.startswith("'"):
                campos[linea.split("'")[1]] = linea

        assert "CUIT" in campos, "{} no tiene el campo CUIT".format(formato)
        assert "CUIT.L" in campos, (
            "{} no tiene el campo CUIT.L: quedaria el numero sin rotulo y sin "
            "explicar que es".format(formato))

        def posicion(nombre):
            partes = campos[nombre].split(";")
            return float(partes[2]), float(partes[3])

        x_rotulo, y_rotulo = posicion("CUIT.L")
        x_valor, y_valor = posicion("CUIT")
        assert x_rotulo < x_valor, (
            "{}: el rotulo quedo a la derecha del valor".format(formato))
        assert abs(y_rotulo - y_valor) < 3, (
            "{}: el rotulo quedo en otra fila (y={} contra y={})".format(
                formato, y_rotulo, y_valor))


def test_formato_cuit_devuelve_el_numero_con_guiones():
    from libs.Utiles import formato_cuit

    assert formato_cuit("20123456789") == "20-12345678-9"
    assert formato_cuit("20-12345678-9") == "20-12345678-9"
    # Un valor que no es un CUIT se devuelve tal cual, para que se vea el
    # problema en vez de recortarlo en silencio.
    assert formato_cuit("") == ""
    assert formato_cuit("algo raro") == "algo raro"

# -- Identidad del producto y pie de la factura ---------------------------

def test_el_nombre_del_producto_no_lleva_la_marca_de_nadie():
    """El producto se vende a estudios contables: el nombre es neutro.

    Que aparezca "Vogel" en el nombre solo tiene sentido si el software fuera
    de uso interno. Es un chequeo de decision comercial, no de codigo, pero
    conviene que quede escrito en un test para que no se cuelgue la marca sin
    que nadie lo note.
    """
    from libs.Constantes import EMPRESA_DESARROLLO, NOMBRE_PRODUCTO

    assert NOMBRE_PRODUCTO == "Asiento"
    assert "Vogel" not in NOMBRE_PRODUCTO
    assert "PyFE" not in NOMBRE_PRODUCTO
    # La empresa si va, pero en el pie de credito y no en el nombre.
    assert EMPRESA_DESARROLLO == "Vogel Consultoria"


def test_el_cliente_no_ve_la_marca_en_el_nombre_del_sistema():
    """`nombre_sistema` es el titulo de todos los avisos, y sale del .ini.

    El valor por defecto tiene que ser el producto, no el nombre de la empresa
    que lo desarrollo: en la maquina de un estudio contable, un aviso que dice
    "Vogel Consultoria" confunde.
    """
    import os
    import tempfile

    from libs.Utiles import LeerIni

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original = os.path.join(raiz, "sistema.ini")
    if not os.path.isfile(original):
        return  # no hay configuracion en este entorno

    with open(original, "r", encoding="utf-8", errors="replace") as f:
        texto = f.read()
    import re
    match = re.search(r"nombre_sistema\s*=\s*(.+)", texto)
    if match:
        valor = match.group(1).strip()
        assert "Vogel" not in valor, (
            "el nombre del sistema de esta instalacion dice '{}': es el titulo "
            "de todos los avisos".format(valor))


def test_el_pie_de_la_factura_credita_el_desarrollo():
    """El pie lleva 'Desarrollo de ...' con la empresa y el contacto.

    Va en el pie de la pagina, NO en el bloque del emisor: ese bloque
    identifica a quien factura, y quien factura es el cliente. Por eso el
    texto tiene que decir 'Desarrollo de' y no 'Emitido por'.
    """
    from libs.Constantes import CREDITO_SOFTWARE

    assert CREDITO_SOFTWARE.startswith("Desarrollo de")
    assert "vogelconsultoria.com.ar" in CREDITO_SOFTWARE
    assert "WhatsApp" in CREDITO_SOFTWARE
    # No puede decir 'Emitido por': seria poner el nombre del que desarrollo el
    # software en el bloque del emisor, que es del cliente.
    assert "Emitido por" not in CREDITO_SOFTWARE


def test_el_campo_del_pie_existe_en_los_dos_formatos():
    """Sin el campo en el .csv, el pie no se imprime."""
    from libs.recursos import ruta_recurso

    for formato in ("factura_marca.csv", "factura_qr.csv"):
        ruta = ruta_recurso("plantillas/" + formato)
        assert ruta, "falta la plantilla {}".format(formato)
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            lineas = f.read().splitlines()
        campo = [l for l in lineas if l.startswith("'creditoSoftware';")]
        assert campo, "{} no tiene el campo creditoSoftware".format(formato)
        partes = campo[0].split(";")
        y = float(partes[3])
        tam = int(partes[7])
        # Abajo de todo y chico: un credito de software no compite con los
        # datos fiscales del comprobante.
        assert y >= 285, "{}: el pie esta en y={}, muy arriba".format(formato, y)
        assert tam <= 7, "{}: el pie usa {} pt, deberia ser chico".format(formato, tam)
