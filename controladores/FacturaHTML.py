# coding=utf-8
"""Factura con diseno compacto: plantilla y PDF A4 generados con fpdf2.

Por que existe
--------------
La plantilla fiscal (plantillas/factura_qr.csv) dibuja por coordenadas: cada
texto tiene su x/y en una planilla. Para agrandar una letra hay que mover
media hoja a mano, y el resultado sigue viendose como un formulario de los
90. Esta capa arma el comprobante en HTML (plantillas/factura_moderna.html)
con fpdf2, que ya es dependencia: sin nada nuevo que instalar y sin pasar
por el spooler de Windows (QPrinter se cuelga si la impresora por defecto
no responde, y QPdfWriter tambien: probado).

La cabecera y el detalle usan HTML; pago, totales y CAE se dibujan en
coordenadas fijas para que queden juntos cerca del pie cuando hay pocos
renglones. El credito se imprime en el pie fijo de cada hoja.

No reemplaza nada: es un camino alternativo. Si el parametro FACTURA_HTML
no esta en "S" (o si algo falla), la impresion sigue por el camino de
siempre. La FCE tambien sigue por el suyo.

Reglas del motor (fpdf2 write_html, probadas una por una)
---------------------------------------------------------
- En las celdas vale UN solo bloque de texto: un <br> la parte en dos y
  revienta con NotImplementedError. Varias lineas van en varias filas.
- En las celdas el COLOR se ignora (todo sale del color ambiente) pero el
  TAMAÑO (<font size>) y la negrita (<b>) si aplican. Los colores van fuera
  de las tablas, donde todo vale.
- Los anchos de columna se declaran SOLO en la primera fila; en las demas
  solo ensucian el log. Sin anchos en la primera, revienta.
- Sin tablas anidadas (revienta) y sin <font> mezclado con texto en la
  misma celda (revienta). El fondo por fila (bgcolor en tr) si anda.
- El <img> respeta width/height SOLO fuera de tablas; adentro ocupa toda
  la celda. Logo y QR van fuera.
- Las fuentes base son latin-1: lo que no entra se traduce en _latinizar.

Los datos entran como atributos (cabfact real o la muestra de
DisenoComprobante): todo se lee con getattr y valores por defecto, nunca
con consultas. Lo unico que toca disco es el QR, que se genera igual que
en la impresion normal.
"""
import html as html_lib
import os
from string import Template

from libs.Utiles import (DeCodifica, LeerIni, formato_cuit,
                         ubicacion_sistema)
from libs.visor import abrir_pdf


PARAM_HTML = "FACTURA_HTML"
PLANTILLA = "factura_moderna.html"

LETRA_POR_CODIGO = {
    1: "A", 2: "A", 3: "A", 6: "B", 7: "B", 8: "B",
    11: "C", 12: "C", 13: "C",
    201: "A", 202: "A", 203: "A", 206: "B", 207: "B", 208: "B",
    211: "C", 212: "C", 213: "C",
}


def usar_factura_html():
    """True si el diseno moderno esta activado. Apagado por defecto."""
    try:
        from modelos.ParametrosSistema import ParamSist
        return (ParamSist.ObtenerParametro(PARAM_HTML, "N") or "N").strip().upper() == "S"
    except Exception:
        return False


def _texto(valor, defecto=""):
    if valor is None:
        return defecto
    return str(valor)


def _fecha_corta(valor):
    """date/datetime a dd/mm/aaaa. El texto se deja como esta."""
    try:
        return valor.strftime("%d/%m/%Y")
    except Exception:
        return _texto(valor)


def _importe(valor):
    """El numero como se lee en la factura, o vacio si no hay."""
    try:
        from libs.Grillas import _formato_importe
        if valor is None:
            return ""
        return _formato_importe(valor)
    except Exception:
        return _texto(valor)


def _letra(tipocomp):
    letra = getattr(tipocomp, "letra", None)
    if letra:
        return _texto(letra).strip().upper() or "X"
    try:
        return LETRA_POR_CODIGO.get(int(getattr(tipocomp, "codigo", 0)), "X")
    except Exception:
        return "X"


def _es_cf(cliente):
    try:
        return int(getattr(getattr(cliente, "tiporesp", None), "idtiporesp", 0)) == 3
    except Exception:
        return False


def _renglones_desde_base(idcabfact):
    """Las filas Detfact guardadas, para cuando no vienen renglones.

    Es lo que lee la impresion normal si no se los pasan (reimpresion).
    Las filas sirven tal cual: tienen los mismos atributos que usa
    datos_comprobante (idarticulo, descad, cantidad, precio, tipoiva).
    """
    try:
        if not idcabfact:
            return []
        from modelos.Detfact import Detfact

        return list(Detfact.select()
                    .where(Detfact.idcabfact == idcabfact)
                    .order_by(Detfact.iddetfact))
    except Exception:
        return []


def _qr_ruta(datos):
    """El QR de AFIP como ruta de archivo, o "" si no se pudo generar."""
    try:
        from controladores.FE import PyQRv1
        from libs.instalacion import cuit_emisor

        pyqr = PyQRv1()
        pyqr.CrearArchivo()
        cuit = _texto(datos.get("emisor_cuit", "")).replace("-", "") or cuit_emisor()
        pyqr.GenerarImagen(
            1, datos.get("qr_fecha", ""), int(cuit or 0),
            int(datos.get("pto_vta", 0) or 0), int(datos.get("tipo_cmp", 0) or 0),
            int(datos.get("nro_cmp", 0) or 0), round(float(datos.get("total_crudo", 0) or 0), 2),
            "PES", "1.000", int(datos.get("tipo_doc", 99) or 99),
            _texto(datos.get("nro_doc", "")).replace("-", "") or "0",
            "E", _texto(datos.get("cae", "")),
        )
        ruta = os.path.abspath(pyqr.Archivo)
        if not (ruta and os.path.isfile(ruta)):
            return ""
        # El PNG sale grande y fpdf2 lo tiene en cuenta para el corte de
        # pagina aunque despues lo dibuje chico: se deja en 180px (a 64pt
        # impresos sobra para escanearlo) y el PDF tambien pesa menos.
        try:
            from PIL import Image
            with Image.open(ruta) as imagen:
                if max(imagen.size) > 180:
                    imagen.resize((180, 180)).save(ruta, "PNG")
        except Exception:
            pass
        return ruta
    except Exception:
        return ""


def _logo_ruta():
    """El logo de la marca (o el generico), o ("", False) si no hay.

    Devuelve (ruta, borrar_despues): si el archivo es mas grande que la
    caja se deja una copia reducida en el temporal, porque el tamaño
    impreso sale del archivo y un logo alto se come un cuarto de hoja.
    """
    try:
        from controladores.FacturaBranding import cargar_config_marca_factura

        try:
            config = cargar_config_marca_factura()
            candidatos = [config.logo, "plantillas/logo.png"]
        except Exception:
            candidatos = ["plantillas/logo.png"]
        base = ubicacion_sistema()
        for candidato in candidatos:
            for ruta in (os.path.join(base, _texto(candidato)),
                         _texto(candidato)):
                if ruta and os.path.isfile(ruta):
                    return _encajar_logo(ruta)
    except Exception:
        pass
    return "", False


def _encajar_logo(ruta):
    """(ruta, borrar) con el logo dentro de 320x140, sin deformar."""
    try:
        import tempfile

        from PIL import Image

        with Image.open(ruta) as imagen:
            if imagen.size[0] <= 320 and imagen.size[1] <= 140:
                return os.path.abspath(ruta).replace("\\", "/"), False
            copia = imagen.copy()
        copia.thumbnail((320, 140))
        tmp = tempfile.NamedTemporaryFile(prefix="logo_factura_",
                                          suffix=".png", delete=False)
        tmp.close()
        copia.save(tmp.name, "PNG")
        return tmp.name.replace("\\", "/"), True
    except Exception:
        try:
            return os.path.abspath(ruta).replace("\\", "/"), False
        except Exception:
            return "", False


def _colores_marca():
    """Los colores del Diseno de comprobante, con los de la casa si falta."""
    try:
        from controladores.FacturaBranding import cargar_config_marca_factura
        config = cargar_config_marca_factura()
        return {
            "primario": config.color_primario or "#0F2A44",
            "secundario": config.color_secundario or "#0B2035",
            "acento": config.color_acento or "#F2A900",
            "texto_suave": config.color_texto_secundario or "#8EA8C3",
            "leyenda": config.leyenda or "",
            "web": config.web or "",
        }
    except Exception:
        return {
            "primario": "#0F2A44", "secundario": "#0B2035",
            "acento": "#F2A900", "texto_suave": "#8EA8C3",
            "leyenda": "", "web": "",
        }


def datos_comprobante(cabfact, renglones=None):
    """Todo lo que la plantilla necesita, en un dict plano de strings.

    No consulta la base: lee atributos (sirve el Cabfact real y la muestra
    de DisenoComprobante). Los importes ya vienen formateados para pantalla.
    """
    cliente = getattr(cabfact, "cliente", None)
    tipocomp = getattr(cabfact, "tipocomp", None)
    es_cf = _es_cf(cliente)

    numero = _texto(getattr(cabfact, "numero", ""))
    try:
        pto_vta = int((numero.split("-")[0] if "-" in numero else numero[:4]) or 0)
    except Exception:
        pto_vta = 0
    try:
        nro_cmp = int((numero.split("-")[-1] if "-" in numero else numero[-8:]) or 0)
    except Exception:
        nro_cmp = 0

    if es_cf:
        doc_label, documento, tipo_doc = "DNI", _texto(getattr(cliente, "dni", "")), 96
    else:
        doc_label = "CUIT"
        documento = _texto(getattr(cliente, "cuit", ""))
        tipo_doc = 80
    if not _texto(documento).strip("0").strip():
        documento, tipo_doc = "", 99

    items = []
    for d in renglones or []:
        try:
            codigo = _texto(getattr(getattr(d, "idarticulo", None), "idarticulo",
                                    getattr(d, "idarticulo", "")))
            cantidad = getattr(d, "cantidad", "")
            detalle = _texto(getattr(d, "descad", getattr(d, "detalle", "")))
            precio = getattr(d, "precio", getattr(d, "precio_unitario", ""))
            iva = getattr(getattr(d, "tipoiva", None), "iva", "")
            try:
                importe = float(str(precio or 0).replace(",", ".")) * float(str(cantidad or 0).replace(",", "."))
            except Exception:
                importe = ""
            items.append({
                "codigo": codigo, "cantidad": _texto(cantidad),
                "detalle": detalle, "precio": _importe(precio),
                "iva": _texto(iva), "importe": _importe(importe),
            })
        except Exception:
            continue

    filas_iva = []
    try:
        netoa = float(str(getattr(cabfact, "netoa", 0) or 0))
    except Exception:
        netoa = 0
    try:
        netob = float(str(getattr(cabfact, "netob", 0) or 0))
    except Exception:
        netob = 0
    if netoa:
        filas_iva.append(("IVA 21%", _importe(netoa), _importe(netoa * 21 / 100)))
    if netob:
        filas_iva.append(("IVA 10,5%", _importe(netob), _importe(netob * 10.5 / 100)))
    try:
        tributos = float(str(getattr(cabfact, "percepciondgr", 0) or 0))
    except Exception:
        tributos = 0

    try:
        forma = _texto(getattr(getattr(cabfact, "formapago", None), "detalle", ""))
    except Exception:
        forma = ""
    try:
        cuotas = int(getattr(cabfact, "cuotapago", 1) or 1)
    except Exception:
        cuotas = 1
    if cuotas > 1:
        forma = "{} {} pagos".format(forma, cuotas).strip()

    try:
        from libs.instalacion import cuit_emisor
        emisor_cuit = formato_cuit(cuit_emisor())
    except Exception:
        emisor_cuit = ""
    membrete1 = DeCodifica(LeerIni(clave="membrete1", key="FACTURA"))
    membrete2 = DeCodifica(LeerIni(clave="membrete2", key="FACTURA"))
    iibb = _texto(LeerIni(clave="iibb", key="FACTURA"))
    condicion_iva = _texto(LeerIni(clave="iva", key="FACTURA"))
    inicio = _texto(LeerIni(clave="inicio", key="FACTURA"))
    emisor_fiscal = " · ".join(x for x in (
        "CUIT {}".format(emisor_cuit) if emisor_cuit else "",
        "IIBB {}".format(iibb) if iibb else "") if x)
    emisor_condicion = " · ".join(x for x in (
        "Condición frente al IVA: {}".format(condicion_iva) if condicion_iva else "",
        "Inicio de actividades: {}".format(inicio) if inicio else "") if x)
    try:
        homo = (LeerIni(clave="homo") or "").strip().upper() == "S"
    except Exception:
        homo = False

    try:
        localidad = _texto(getattr(getattr(cliente, "localidad", None), "nombre", ""))
        provincia = _texto(getattr(getattr(cliente, "localidad", None), "provincia", ""))
    except Exception:
        localidad, provincia = "", ""

    nombre_recep = _texto(getattr(cabfact, "nombre", "")) or _texto(getattr(cliente, "nombre", ""))
    try:
        concepto = int(getattr(cabfact, "concepto", 1) or 1)
    except Exception:
        concepto = 1
    periodo = ""
    if concepto in (2, 3):
        desde = _fecha_corta(getattr(cabfact, "desde", ""))
        hasta = _fecha_corta(getattr(cabfact, "hasta", ""))
        periodo = "Período facturado: desde {} hasta {}".format(desde, hasta)
    try:
        from libs.Utiles import FechaMysql
        qr_fecha = FechaMysql(getattr(cabfact, "desde", None) or getattr(cabfact, "fecha", None))
    except Exception:
        qr_fecha = ""

    return {
        "tipo_nombre": _texto(getattr(tipocomp, "nombre", "Factura")),
        "letra": _letra(tipocomp),
        "numero": numero,
        "fecha": _fecha_corta(getattr(cabfact, "fecha", "")),
        "empresa": DeCodifica(LeerIni(clave="empresa", key="FACTURA")),
        "emisor_cuit": emisor_cuit,
        "emisor_linea1": membrete1,
        "emisor_linea2": membrete2,
        "emisor_fiscal": emisor_fiscal,
        "emisor_condicion": emisor_condicion,
        "emisor_detalle": "<br>".join(
            html_lib.escape(_texto(x)) for x in [
                membrete1,
                membrete2,
                "CUIT {} · IIBB {}".format(
                    emisor_cuit, iibb).strip(" ·"),
                "Condición frente al IVA: {} · Inicio de actividades: {}".format(
                    condicion_iva, inicio).strip(" ·"),
            ] if _texto(x).strip()),
        "recep_nombre": nombre_recep,
        "recep_doc_label": doc_label,
        "recep_doc": documento,
        "recep_dom": _texto(getattr(cabfact, "domicilio", "")) or _texto(getattr(cliente, "domicilio", "")),
        "recep_loc": " · ".join(x for x in [localidad, provincia] if x),
        "recep_iva": _texto(getattr(getattr(cliente, "tiporesp", None), "nombre", "")),
        "items": items,
        "subtotal": _importe(getattr(cabfact, "neto", "")),
        "filas_iva": filas_iva,
        "tributos": _importe(tributos) if tributos else "",
        "tributos_detalle": _texto(getattr(getattr(cliente, "percepcion", None), "detalle", "")),
        "descuento": _importe(getattr(cabfact, "descuento", 0) or 0),
        "recargo": _importe(getattr(cabfact, "recargo", 0) or 0),
        "periodo": periodo,
        "concepto": concepto,
        "total": _importe(getattr(cabfact, "total", "")),
        "total_crudo": getattr(cabfact, "total", 0),
        "forma_pago": forma,
        "cae": _texto(getattr(cabfact, "cae", "")),
        "cae_vto": _fecha_corta(getattr(cabfact, "venccae", "")),
        "tipo_cmp": getattr(tipocomp, "codigo", 0),
        "pto_vta": pto_vta,
        "nro_cmp": nro_cmp,
        "tipo_doc": tipo_doc,
        "nro_doc": documento,
        "qr_fecha": qr_fecha,
        "homo": homo,
    }


def _fila_item(item, par):
    if par:
        apertura = "<tr bgcolor=\"#F7F9FB\">"
    else:
        apertura = "<tr>"
    return (
        apertura +
        "<td>{codigo}</td><td>{cantidad}</td><td>{detalle}</td>"
        '<td align="right">{precio}</td><td align="right">{iva}</td>'
        '<td align="right">{importe}</td></tr>'
    ).format(**{k: html_lib.escape(str(v)) for k, v in item.items()})


# Caracteres fuera de latin-1 (lo unico que traen las fuentes base del
# PDF): se traducen a algo parecido en vez de reventar la emision con
# UnicodeEncodeError por una viñeta en una leyenda.
_LATINOS = {
    "\u2013": "-", "\u2014": "-", "\u2018": "'",
    "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u2022": "-", "\u00a0": " ",
}


def _latinizar(texto):
    return "".join(_LATINOS.get(c, c) for c in _texto(texto))


def html_comprobante(datos, marca=None):
    """El HTML final, con todo escapado y sin $ sin reemplazar."""
    marca = marca or _colores_marca()
    ruta = os.path.join(ubicacion_sistema(), "plantillas", PLANTILLA)
    with open(ruta, encoding="utf-8") as fh:
        plantilla = Template(fh.read())

    filas_items = "\n".join(
        _fila_item(item, i % 2) for i, item in enumerate(datos.get("items", [])))
    filas_iva = "\n".join(
        '<p align="right"><font size="11">{} ({}) {}</font></p>'.format(
            html_lib.escape(str(etiqueta)), html_lib.escape(str(base)),
            html_lib.escape(str(importe)))
        for etiqueta, base, importe in datos.get("filas_iva", []))
    if datos.get("tributos"):
        detalle = datos.get("tributos_detalle") or "Tributos"
        tributos_html = (
            '<p align="right"><font size="11">{} {}</font></p>'.format(
                html_lib.escape(str(detalle)),
                html_lib.escape(str(datos["tributos"]))))
    else:
        tributos_html = ""
    descuento_html = ""
    try:
        if float(str(datos.get("descuento", "")).replace(".", "").replace(",", ".") or 0):
            descuento_html += (
                '<p align="right"><font size="11">Descuento -{}</font></p>'.format(
                    html_lib.escape(str(datos["descuento"]))))
    except Exception:
        pass
    try:
        if float(str(datos.get("recargo", "")).replace(".", "").replace(",", ".") or 0):
            descuento_html += (
                '<p align="right"><font size="11">Recargo +{}</font></p>'.format(
                    html_lib.escape(str(datos["recargo"]))))
    except Exception:
        pass

    if datos.get("logo_ruta"):
        # Sin alto: lo calcula solo y no deforma el logo. Fuera de tablas,
        # que es donde fpdf2 respeta el tamaño pedido.
        logo_img = '<img src="{}" width="110"><br>'.format(datos["logo_ruta"])
    else:
        logo_img = ""
    if datos.get("qr_ruta"):
        qr_img = '<img src="{}" width="64">'.format(datos["qr_ruta"])
    else:
        qr_img = ""
    if datos.get("periodo"):
        periodo_html = (
            '<p><font size="8" color="#526477">{}</font></p>'.format(
                html_lib.escape(str(datos["periodo"]))))
    else:
        periodo_html = ""

    valores = {
        "color_primario": marca["primario"],
        "color_secundario": marca["secundario"],
        "color_acento": marca["acento"],
        "color_texto_suave": marca["texto_suave"],
        "homo_banner": ('<center><font size="14" color="#C9D3DD">'
                        '<b>HOMOLOGACIÓN</b></font></center>'
                        if datos.get("homo") else ""),
        "logo_img": logo_img,
        "qr_img": qr_img,
        "tipo_nombre": datos.get("tipo_nombre", ""),
        "letra": datos.get("letra", ""),
        "numero": datos.get("numero", ""),
        "fecha": datos.get("fecha", ""),
        "empresa": datos.get("empresa", ""),
        "emisor_cuit": datos.get("emisor_cuit", ""),
        "emisor_linea1": datos.get("emisor_linea1", ""),
        "emisor_linea2": datos.get("emisor_linea2", ""),
        "emisor_fiscal": datos.get("emisor_fiscal", ""),
        "emisor_condicion": datos.get("emisor_condicion", ""),
        "emisor_detalle": datos.get("emisor_detalle", ""),
        "recep_nombre": datos.get("recep_nombre", ""),
        "recep_doc_label": datos.get("recep_doc_label", ""),
        "recep_doc": datos.get("recep_doc", ""),
        "recep_dom": datos.get("recep_dom", ""),
        "recep_loc": datos.get("recep_loc", ""),
        "recep_iva": datos.get("recep_iva", ""),
        "filas_items": filas_items,
        "subtotal": datos.get("subtotal", ""),
        "filas_iva": filas_iva,
        "tributos_html": tributos_html,
        "descuento_html": descuento_html,
        "total": datos.get("total", ""),
        "forma_pago": datos.get("forma_pago", ""),
        "cae": datos.get("cae", ""),
        "cae_vto": datos.get("cae_vto", ""),
        "periodo_html": periodo_html,
        "leyenda": datos.get("leyenda", marca.get("leyenda", "")),
        "web": datos.get("web", marca.get("web", "")),
        "credito": datos.get("credito", ""),
        # El pie en una sola variable: si leyenda y web estan vacias sale
        # una sola linea, que es lo que entra al pie de la primera hoja.
        "pie": "<br>".join(
            x for x in (datos.get("leyenda", marca.get("leyenda", "")),
                        datos.get("web", marca.get("web", "")),
                        datos.get("credito", ""))
            if _texto(x).strip()),
    }
    # Los textos libres pueden traer < > (un nombre): se escapan para que
    # el HTML no se rompa. El HTML armado aca arriba no trae ninguno, asi
    # que vale para todo salvo esos bloques.
    #
    # El $ (pesos) NO se toca: Template solo interpreta los $ de la
    # plantilla, y los valores entran literales.
    HTML_YA_ARMADO = {"filas_items", "filas_iva", "tributos_html",
                      "descuento_html", "emisor_detalle", "logo_img",
                      "qr_img", "homo_banner", "periodo_html"}
    for clave, valor in list(valores.items()):
        if clave not in HTML_YA_ARMADO:
            valores[clave] = html_lib.escape(_texto(valor))
    # substitute() ya levanta si falta un placeholder: un "$total" impreso
    # no llega nunca al papel. Y antes de entregar, todo a latin-1 (las
    # fuentes base del PDF no traen mas que eso).
    return _latinizar(plantilla.substitute(valores))


def _rgb(color, defecto):
    """Convierte el color configurable a RGB, con un valor seguro."""
    try:
        color = str(color or "").strip().lstrip("#")
        if len(color) != 6:
            raise ValueError("color incompleto")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        color = defecto.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _texto_pie(datos, marca):
    derecha = " · ".join(
        _texto(x).strip() for x in (
            datos.get("leyenda") or marca.get("leyenda"),
            datos.get("web") or marca.get("web"),
        ) if _texto(x).strip())
    return _texto(datos.get("credito", "")).strip(), derecha


def _dibujar_cierre(pdf, datos, marca):
    """Pago, autorización y totales anclados al pie de la hoja A4."""
    primario = _rgb(marca.get("primario"), "#0F2A44")
    suave = _rgb(marca.get("texto_suave"), "#8EA8C3")
    panel = (241, 245, 248)
    borde = (207, 218, 228)
    tinta = (36, 54, 74)
    total_rows = [("Subtotal", datos.get("subtotal", ""))]
    total_rows.extend(
        ("{} ({})".format(etiqueta, base), importe)
        for etiqueta, base, importe in datos.get("filas_iva", []))
    if datos.get("tributos"):
        total_rows.append((datos.get("tributos_detalle") or "Tributos",
                           datos["tributos"]))
    for clave, rotulo, signo in (("descuento", "Descuento", "-"),
                                  ("recargo", "Recargo", "+")):
        valor = _texto(datos.get(clave, ""))
        try:
            tiene_valor = float(valor.replace(".", "").replace(",", ".") or 0) != 0
        except Exception:
            tiene_valor = False
        if tiene_valor:
            total_rows.append((rotulo, signo + valor))

    alto_totales = max(41, 13 + len(total_rows) * 5 + 10)
    fin_panel = 276
    inicio_panel = fin_panel - alto_totales
    y_pago = inicio_panel - 18
    if pdf.get_y() > y_pago - 4:
        # Si la tabla ocupó la zona reservada para el cierre, el cierre pasa
        # completo a una hoja nueva: nunca se pisa un renglón ni el pie.
        pdf.add_page()
        inicio_panel = fin_panel - alto_totales
        y_pago = inicio_panel - 18

    # El cierre se dibuja de forma absoluta en la franja reservada. La regla
    # automática de salto ya protegió el detalle; dejarla activa aquí haría
    # que cada celda del cierre saltara a otra página al superar los 217 mm.
    pdf.set_auto_page_break(False)
    pdf.set_draw_color(*borde)
    pdf.set_fill_color(*panel)
    pdf.rect(10, y_pago, 190, 13, style="DF")
    pdf.set_xy(14, y_pago + 2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*suave)
    pdf.cell(35, 3, "FORMA DE PAGO")
    pdf.set_xy(14, y_pago + 6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*tinta)
    pdf.cell(180, 5, _latinizar(datos.get("forma_pago", "")))

    x_cae, ancho_cae = 10, 110
    x_total, ancho_total = 124, 76
    pdf.set_draw_color(*borde)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(x_cae, inicio_panel, ancho_cae, alto_totales, style="DF")
    pdf.set_fill_color(*panel)
    pdf.rect(x_total, inicio_panel, ancho_total, alto_totales, style="DF")

    pdf.set_xy(x_cae + 4, inicio_panel + 4)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*suave)
    pdf.cell(74, 4, "AUTORIZACIÓN ARCA")
    pdf.set_xy(x_cae + 4, inicio_panel + 13)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*primario)
    pdf.cell(76, 5, _latinizar("CAE {}".format(datos.get("cae", ""))))
    pdf.set_xy(x_cae + 4, inicio_panel + 21)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*tinta)
    pdf.cell(77, 4, _latinizar("Vencimiento {}".format(datos.get("cae_vto", ""))))
    pdf.set_xy(x_cae + 4, inicio_panel + 27)
    pdf.cell(77, 4, "Comprobante autorizado · Original")
    qr = datos.get("qr_ruta")
    if qr and os.path.isfile(qr):
        pdf.image(qr, x=x_cae + 85, y=inicio_panel + 5, w=20, h=20)

    y = inicio_panel + 4
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*tinta)
    for etiqueta, importe in total_rows:
        pdf.set_xy(x_total + 4, y)
        pdf.cell(47, 4.5, _latinizar(etiqueta))
        pdf.set_xy(x_total + 50, y)
        pdf.cell(22, 4.5, _latinizar(importe), align="R")
        y += 5
    pdf.set_draw_color(*borde)
    pdf.line(x_total + 4, y + 1, x_total + ancho_total - 4, y + 1)
    pdf.set_fill_color(*primario)
    pdf.rect(x_total + 4, fin_panel - 13, ancho_total - 8, 10, style="F")
    pdf.set_xy(x_total + 7, fin_panel - 11)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(20, 6, "TOTAL")
    pdf.set_xy(x_total + 28, fin_panel - 11)
    pdf.cell(ancho_total - 35, 6, _latinizar(datos.get("total", "")), align="R")
    pdf.set_auto_page_break(True, 80)


def generar_pdf(html, salida, datos=None, marca=None):
    """Genera el PDF A4 y fija el cierre/pie contra la zona inferior."""
    from fpdf import FPDF

    marca = marca or _colores_marca()
    pie_izquierda, pie_derecha = _texto_pie(datos or {}, marca)

    class FacturaPDF(FPDF):
        def footer(self):
            primario = _rgb(marca.get("primario"), "#0F2A44")
            self.set_draw_color(207, 218, 228)
            self.set_line_width(0.25)
            self.line(10, 281, 200, 281)
            self.set_y(283)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(*primario)
            texto_izquierda = _latinizar(pie_izquierda)
            while (self.get_string_width(texto_izquierda) > 118 and
                   self.font_size_pt > 5.2):
                self.set_font("Helvetica", "", self.font_size_pt - 0.2)
            self.cell(120, 4, texto_izquierda)
            self.set_text_color(*_rgb(marca.get("texto_suave"), "#8EA8C3"))
            texto_derecha = _latinizar(pie_derecha)
            self.set_font("Helvetica", "", 6)
            while (self.get_string_width(texto_derecha) > 70 and
                   self.font_size_pt > 5.2):
                self.set_font("Helvetica", "", self.font_size_pt - 0.2)
            self.cell(70, 4, texto_derecha, align="R")

    pdf = FacturaPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    # Reserva el área inferior para el resumen/CAE y el pie fijo. El detalle
    # puede continuar en otras páginas sin invadir esa zona.
    pdf.set_auto_page_break(True, 80)
    pdf.add_page()
    pdf.set_draw_color(207, 218, 228)
    pdf.set_line_width(0.25)
    html_superior, marcador, _html_inferior = _latinizar(html).partition(
        "__PYFE_CIERRE__")
    pdf.write_html(html_superior + ("</font>" if marcador else ""))
    if datos is not None and marcador:
        _dibujar_cierre(pdf, datos, marca)
    pdf.output(salida)


def imprimir_html(cabfact, salida=None, mostrar=True, renglones=None):
    """Arma el PDF moderno de un comprobante.

    Devuelve (True, ruta) si salio. No escribe en la base. Si falta la
    plantilla o algo falla, devuelve (False, None) para que quien llama
    siga por el camino de siempre.
    """
    try:
        if salida is None:
            nombre = "{}-{}.pdf".format(
                _texto(getattr(getattr(cabfact, "tipocomp", None), "nombre",
                               "comprobante")).replace(" ", "_"),
                _texto(getattr(cabfact, "numero", "?")))
            salida = os.path.join("facturas", nombre)
        if renglones is None:
            # Reimpresion (o cualquier impresion sin renglones a mano):
            # salen de la base, como en el camino de siempre.
            renglones = _renglones_desde_base(
                getattr(cabfact, "idcabfact", None))
        datos = datos_comprobante(cabfact, renglones)
        try:
            from libs.Constantes import CREDITO_SOFTWARE
            datos["credito"] = CREDITO_SOFTWARE
        except Exception:
            datos["credito"] = ""
        marca = _colores_marca()
        datos["leyenda"] = marca.get("leyenda", "")
        datos["web"] = marca.get("web", "")
        logo_tmp = None
        try:
            logo, logo_tmp = _logo_ruta()
            if logo:
                datos["logo_ruta"] = logo
            qr = _qr_ruta(datos)
            if qr:
                datos["qr_ruta"] = qr
            contenido = html_comprobante(datos, marca=marca)
            generar_pdf(contenido, salida, datos=datos, marca=marca)
            if mostrar:
                abrir_pdf(salida, False)
            return True, salida
        finally:
            if logo_tmp:
                try:
                    os.remove(logo_tmp)
                except Exception:
                    pass
    except Exception:
        return False, None
