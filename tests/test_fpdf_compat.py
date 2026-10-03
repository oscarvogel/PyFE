"""Compatibilidad entre pyfepdf (fpdf 1.7) y fpdf2.

Por que esta probada
--------------------
pyafipws sigue escribiendo para fpdf 1.7, que fue descontinuado: hoy esta
fpdf2. Upstream NO lo actualizo (se verifico contra las ramas 2025 y main a
octubre de 2026: las dos siguen en pyfepdf 3.11c, sin tocar el tema). O sea,
esto no se arregla actualizando: hay que.translationarlo.

Lo que se traduce esta aca, no dentro de pyafipws, porque pyafipws/ esta en
.gitignore: un arreglo ahi no llega a nadie mas y se pierde en la proxima
clonacion.

Cada incompatibilidad que se arreglo aqui la provoco un PDF vacio o un PDF
que no salia, y se paso de a una. Los tests fijan las cuatro.
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from libs import fpdf_compat  # noqa: E402


# -- Alineacion: los codigos que pyfepdf usa y fpdf2 no conoce ---------------

def test_d_se_traduce_a_derecha():
    """D = derecha, en castellano. fpdf 1.7 lo traducía explicitamente."""
    elementos = [{"name": "IVA21", "align": "D"}]
    assert fpdf_compat.normalizar_align(elementos) == 1
    assert elementos[0]["align"] == "R"


def test_i_se_traduce_a_izquierda():
    """I = izquierda, en castellano. Se usa en CAE, CUIT y direcciones."""
    elementos = [{"name": "CAE", "align": "I"}]
    assert fpdf_compat.normalizar_align(elementos) == 1
    assert elementos[0]["align"] == "L"


def test_los_codigos_validos_no_se_tocan():
    elementos = [{"name": "a", "align": "L"}, {"name": "b", "align": "C"},
                 {"name": "c", "align": "R"}, {"name": "d", "align": "J"},
                 {"name": "e", "align": ""}]
    assert fpdf_compat.normalizar_align(elementos) == 0
    assert [e["align"] for e in elementos] == ["L", "C", "R", "J", ""]


def test_el_valor_vacio_no_revienta():
    elementos = [{"name": "a"}, {"name": "b", "align": None}]
    fpdf_compat.normalizar_align(elementos)      # no tiene que lanzar
    assert elementos[1]["align"] is None


# -- Fuentes -----------------------------------------------------------------

def test_arial_black_se_reemplaza_por_arial():
    """fpdf 1.7 lo hacia por su cuenta; fpdf2 lanza Undefined font."""
    elementos = [{"name": "titulo", "font": "Arial Black"}]
    assert fpdf_compat.normalizar_fuentes(elementos) == 1
    assert elementos[0]["font"] == "arial"


def test_arial_normal_no_se_toca():
    elementos = [{"name": "x", "font": "Arial"}]
    assert fpdf_compat.normalizar_fuentes(elementos) == 0
    assert elementos[0]["font"] == "Arial"


# -- Metodos que fpdf2 le saque a la plantilla -------------------------------

def test_has_key_vuelve_a_existir():
    """Sin esto, ProcesarPlantilla aborta en la linea 1110 y el PDF sale vacio."""
    from fpdf.template import Template

    fpdf_compat._instalar_has_key()
    assert hasattr(Template, "has_key")

    plantilla = Template(elements=[
        {"name": "CAE", "type": "T", "x1": 0, "y1": 0, "x2": 10, "y2": 10,
         "font": "arial", "size": 10, "align": "L", "text": ""}])
    assert plantilla.has_key("CAE") is True
    assert plantilla.has_key("cae") is True, "no distingue mayusculas, como antes"
    assert plantilla.has_key("NoExiste") is False


def test_un_campo_que_no_esta_no_revienta():
    """fpdf2 lanza; fpdf 1.7 lo ignoraba en silencio y hay que volver a eso.

    pyfepdf asigna campos que estan en sus plantillas originales pero no en
    las nuestras (hoja, por ejemplo). Si el primero que falta aborta todo, el
    PDF se escribe sin ningun dato de la factura.
    """
    from fpdf.template import Template

    fpdf_compat._instalar_has_key()
    fpdf_compat._relajar_setitem()

    plantilla = Template(elements=[
        {"name": "Total", "type": "T", "x1": 0, "y1": 0, "x2": 10, "y2": 10,
         "font": "arial", "size": 10, "align": "L", "text": ""}])
    plantilla.add_page()

    plantilla["CampoQueNoExiste"] = "lo que sea"      # no tiene que lanzar
    assert fpdf_compat.campos_ignorados(), "el campo ignorado tiene que quedar anotado"
    assert "CampoQueNoExiste" in fpdf_compat.campos_ignorados()

    # Se lee en minuscula: las claves de la plantilla van guardadas asi.
    plantilla["Total"] = "9.900,00"                    # este si existe
    assert plantilla["total"] == "9.900,00"


def test_los_valores_se_convierten_a_texto():
    """Un numero en un campo de texto reventaba el render con un int."""
    from fpdf.template import Template

    fpdf_compat._instalar_has_key()
    fpdf_compat._relajar_setitem()

    plantilla = Template(elements=[
        {"name": "IVA", "type": "T", "x1": 0, "y1": 0, "x2": 10, "y2": 10,
         "font": "arial", "size": 10, "align": "L", "text": ""}])
    plantilla.add_page()

    plantilla["IVA"] = 1718.18
    assert isinstance(plantilla["iva"], str)
    assert plantilla["iva"] == "1718.18"

    plantilla["IVA"] = None
    assert plantilla["iva"] == ""


# -- Sobre una plantilla real del proyecto -----------------------------------

def test_una_plantilla_real_no_deja_codigos_que_fpdf2_rechace():
    """La comprobacion que importa: la factura_qr.csv del repo, de verdad."""
    from fpdf.template import Template

    ruta = os.path.join(RAIZ, "plantillas", "factura_qr.csv")
    if not os.path.isfile(ruta):
        pytest.skip("no esta la plantilla")

    fpdf_compat._instalar_has_key()
    fpdf_compat._relajar_setitem()

    import csv
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.reader(f, delimiter=";"))
    claves = ("name", "type", "x1", "y1", "x2", "y2", "font", "size",
              "bold", "italic", "underline", "foreground", "background",
              "align", "text", "priority", "multiline")
    elementos = []
    for fila in filas:
        if len(fila) < 15:
            continue
        elemento = {}
        for i, clave in enumerate(claves):
            if i >= len(fila):
                break
            valor = fila[i]
            if valor == "":
                valor = None
            else:
                try:
                    valor = eval(valor.strip(), {"__builtins__": {}}, {})
                except Exception:
                    valor = valor.strip("'")
            elemento[clave] = valor
        if elemento.get("name"):
            elementos.append(elemento)

    assert elementos, "no se pudo leer la plantilla"
    fpdf_compat.normalizar_align(elementos)
    fpdf_compat.normalizar_fuentes(elementos)

    # La pregunta se le hace a fpdf2, no a una lista escrita a mano: Align usa
    # intern(), asi que el enum tiene NOMBRES cortos (L, C, R, J) y VALORES
    # largos (LEFT, CENTER...). coerce() acepta los dos.
    from fpdf.enums import Align
    malos = []
    for e in elementos:
        valor = e.get("align")
        if not valor:
            continue
        try:
            Align.coerce(valor)
        except ValueError:
            malos.append((e["name"], valor))
    assert not malos, "fpdf2 rechaza estos alignments: {}".format(malos[:5])

    # Y tiene que poder construirse de verdad, no solo no tener alignments raros.
    Template(elements=elementos)      # si algo falta, revienta aca
