# coding=utf-8
"""Test de recursos de la interfaz: todo icono referenciado tiene que existir.

Por que existe
--------------
Los iconos NO van empaquetados en el .exe: `compila.bat` copia `imagenes/`
suelto al lado del ejecutable. Si un `.py` referencia un icono con ruta
relativa a mano en vez de usar el helper `imagen()`, el recurso se pierde al
empaquetar y el boton sale sin icono, sin ningun error en pantalla.

Este test falla en desarrollo, que es donde se puede arreglar, en vez de
descubrirlo en una instalacion de un cliente.

Se analiza el ARBOL DE SINTAXIS (ast), no el texto: asi los docstrings y los
comentarios que mencionan 'imagenes/x.png' como ejemplo no se confundan con
una referencia real.

No necesita Qt ni base de datos: solo lee los fuentes.
"""

import ast
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Extensiones que cuentan como icono dentro de imagenes/.
EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".ico", ".svg")

CARPETAS_A_REVISAR = ("vistas", "libs", "controladores", "modelos")
ARCHIVOS_SUELTOS = ("main.py",)


def _leer_fuente(ruta):
    """Lee el fuente tolerando los .py legacy que no son UTF-8 limpio.

    Se decodifica en latin-1 como ultimo recurso porque nunca falla, y solo se
    buscan rutas ASCII, asi que el resultado no depende de la codificacion.
    """
    with open(ruta, "rb") as f:
        crudo = f.read()
    for codificacion in ("utf-8", "latin-1"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return crudo.decode("latin-1")


def _archivos_python():
    for carpeta in CARPETAS_A_REVISAR:
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for nombre in sorted(os.listdir(base)):
            if nombre.endswith(".py"):
                yield os.path.join(base, nombre)
    for nombre in ARCHIVOS_SUELTOS:
        yield os.path.join(RAIZ, nombre)


def _literal(valor):
    """Devuelve el string si el nodo es una constante de texto, si no None.

    En ast, un literal como 'x.png' es un Constant, no un str: hay que
    desenvolverlo o el matching nunca encuentra nada.
    """
    if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
        return valor.value
    return None


def _referencias():
    """[(archivo_relativo, linea, referencia, tipo)] leyendo el codigo real.

    tipo = 'set-nuevo'  -> icono('nombre')       (correcto para la interfaz)
    tipo = 'recurso'    -> imagen('x.png')       (logos, PDF, app icon)
    tipo = 'harcodeada' -> imagen='imagenes/x.png' (se rompe al empaquetar)
    """
    hallazgos = []
    for ruta in _archivos_python():
        fuente = _leer_fuente(ruta)
        try:
            arbol = ast.parse(fuente, filename=ruta)
        except SyntaxError:
            # Un archivo que no parsea no se puede revisar: se avisa para que
            # no quede un modulo entero sin cubrir en silencio.
            pytest.fail("{} no parsea, sus iconos quedan sin revisar".format(
                os.path.relpath(ruta, RAIZ)))

        for nodo in ast.walk(arbol):
            # icono('nombre')  -> el set nuevo, sin extension
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) \
                    and nodo.func.id == "icono" and nodo.args:
                ref = _literal(nodo.args[0])
                if ref:
                    hallazgos.append((ruta, nodo.lineno, ref + ".svg", "set-nuevo"))

            # imagen('x.png')
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) \
                    and nodo.func.id == "imagen" and nodo.args:
                ref = _literal(nodo.args[0])
                if ref:
                    hallazgos.append((ruta, nodo.lineno, ref, "recurso"))

            # imagen='imagenes/x.png'  o  imagen=icono('x')
            if isinstance(nodo, ast.keyword) and nodo.arg == "imagen":
                ref = _literal(nodo.value)
                if ref:
                    tipo = "harcodeada" if ("/" in ref or "\\" in ref) else "recurso"
                    hallazgos.append((ruta, nodo.value.lineno, ref, tipo))
                elif (isinstance(nodo.value, ast.Call)
                      and isinstance(nodo.value.func, ast.Name)
                      and nodo.value.func.id == "icono" and nodo.value.args):
                    ref = _literal(nodo.value.args[0])
                    if ref:
                        hallazgos.append((ruta, nodo.value.lineno, ref + ".svg",
                                          "set-nuevo"))

            # LeerIni('iniciosistema') + 'imagenes/x.png'  (expresion BinOp)
            if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
                ref = _literal(nodo.right)
                izquierda = nodo.left
                usa_ini = (isinstance(izquierda, ast.Call)
                           and isinstance(izquierda.func, ast.Name)
                           and izquierda.func.id == "LeerIni")
                if usa_ini and ref and ("/" in ref or "\\" in ref):
                    hallazgos.append((ruta, nodo.lineno, ref, "harcodeada"))

    return hallazgos


REFERENCIAS = _referencias()


def _es_icono(referencia):
    """Filtra las rutas que son archivos generados (tmp/*.pdf) y no iconos."""
    return referencia.replace("\\", "/").lower().endswith(EXTENSIONES_IMAGEN)


def _ruta_completa(referencia, tipo):
    """Normaliza a 'imagenes/nombre.png' o 'carpeta/nombre.ext'."""
    ref = referencia.replace("\\", "/").lstrip("./")
    if tipo == "set-nuevo":
        return "imagenes/iconos/" + ref
    if "/" in ref:
        partes = [p for p in ref.split("/") if p]
        if partes[0] == "imagenes":
            return "/".join(partes)
        # Una subcarpeta que no es imagenes/ no la resuelve imagen(): es un
        # dato de la aplicacion, no un icono.
        return None
    return "imagenes/" + ref


def test_el_escanon_detecta_referencias():
    """Guarda contra falsos positivos: si el escaneo se rompe, no pasa de mentira."""
    assert len(REFERENCIAS) > 50, (
        "el escaneo de iconos no encontro nada, revisar el recorrido de ast")
    del_nuevo = [r for r in REFERENCIAS if r[3] == "set-nuevo"]
    assert len(del_nuevo) > 40, (
        "deberian verse unas 70 referencias al set nuevo, hay {}".format(
            len(del_nuevo)))


def test_todos_los_iconos_existen():
    from libs.recursos import imagen, ruta_recurso

    faltan = []
    for ruta, linea, referencia, tipo in REFERENCIAS:
        completa = _ruta_completa(referencia, tipo)
        if not completa or not _es_icono(referencia):
            continue
        # Se resuelve por la via real de cada API, no por un atajo: asi el test
        # cubre lo que la app hace de verdad.
        if tipo == "set-nuevo":
            existe = bool(ruta_recurso(completa))
        else:
            existe = bool(imagen(completa))
        if not existe:
            faltan.append("{}:{} -> {}".format(
                os.path.relpath(ruta, RAIZ), linea, completa))

    assert not faltan, (
        "Iconos referenciados que no existen:\n  " + "\n  ".join(faltan))


def test_los_iconos_de_ui_usan_el_api_nuevo():
    """La interfaz pide iconos por nombre del set nuevo, no por nombre de archivo.

    Quedaba un puente de traduccion en libs.recursos que convertia
    imagen('new.png') en el icono nuevo. Se elimino en la Etapa 2 al migrar las
    llamadas: con el puente, un icono viejo se ve bien y nadie se entera de que
    el nombre pedido ya no existe en el set.

    Las excepciones son imagenes que no son iconos de interfaz: logos que van
    dentro de un PDF y el icono de la ventana. Esos no tienen version en el set
    monoline y no deberian: no son controles, son contenido.
    """
    from pathlib import Path

    # archivo -> motivo por el que sigue usando imagen()
    EXCEPTO = {
        "Logo S-01.png": "icono de la ventana de la aplicacion",
        "afip_wscdc.png": "logo de ARCA que se estampa en el PDF de constatacion",
        "dgr-misiones.png": "logo de la provincia, en la carga de compras",
    }

    raiz = Path(__file__).resolve().parent.parent
    sospechosos = []
    for carpeta in ("vistas", "libs", "controladores", "modelos"):
        for ruta in (raiz / carpeta).glob("*.py"):
            try:
                arbol = ast.parse(ruta.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for nodo in ast.walk(arbol):
                # imagen('algo.png') con un argumento literal.
                if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                        and nodo.func.id == "imagen" and nodo.args):
                    ref = _literal(nodo.args[0])
                    if (isinstance(ref, str)
                            and ref.lower().endswith((".png", ".jpg", ".svg"))
                            and ref not in EXCEPTO):
                        sospechosos.append("{}:{} -> {!r}".format(
                            ruta.name, nodo.lineno, ref))

    if sospechosos:
        pytest.fail(
            "imagen() con nombre de archivo viejo; usar icono('nombre'):\n  "
            + "\n  ".join(sorted(set(sospechosos))))


def test_el_set_de_iconos_nuevo_esta_completo():
    """Los 9 de la pantalla principal tienen que existir como SVG."""
    from libs.recursos import ruta_recurso
    for nombre in ("nueva-venta", "clientes", "productos", "comprobantes",
                   "cuentas", "reportes", "arca", "configuracion", "salir"):
        assert ruta_recurso("imagenes/iconos/{}.svg".format(nombre)), (
            "falta el icono {}.svg del set nuevo".format(nombre))


# -- Marca ----------------------------------------------------------------

def test_los_derivados_de_la_marca_existen():
    """El logo se genera una vez y se deriva a todos los tamanos que se usan.

    Los genera tools/generar_marca.py. Si alguien reemplaza el original y no
    regenera, el encabezado se queda sin logo y el .exe se queda con el icono
    viejo: esto lo avisa antes.
    """
    from libs.recursos import ruta_recurso

    for nombre in ("logo-vogel.png", "logo-vogel.ico", "marca-recortada.png",
                   "marca-completa.png", "marca-32.png", "marca-48.png"):
        assert ruta_recurso("imagenes/marca/" + nombre), (
            "falta imagenes/marca/{}; correr tools/generar_marca.py".format(nombre))
    for lado in (16, 24, 32, 48, 64, 128, 256):
        assert ruta_recurso("imagenes/marca/logo-{}.png".format(lado)), (
            "falta el logo de {}.px".format(lado))


def test_el_ico_tiene_las_resoluciones_que_windows_necesita():
    """Un .ico de una sola resolucion se ve borroso en la barra de tareas."""
    import struct

    ruta = os.path.join(RAIZ, "imagenes", "marca", "logo-vogel.ico")
    if not os.path.isfile(ruta):
        pytest.fail("falta el .ico de la marca")

    with open(ruta, "rb") as f:
        datos = f.read()

    _reservado, tipo, cantidad = struct.unpack("<HHH", datos[:6])
    assert tipo == 1, "no es un .ico (tipo={})".format(tipo)
    assert cantidad >= 4, "el .ico tiene solo {} resoluciones".format(cantidad)

    lados = set()
    for i in range(cantidad):
        base = 6 + i * 16
        ancho, alto = struct.unpack("<BB", datos[base:base + 2])
        lados.add(ancho if ancho else 256)
    # Windows necesita 16, 32, 48 y 256; sin 256 se ve mal en pantallas grandes.
    for necesario in (16, 32, 48, 256):
        assert necesario in lados, (
            "el .ico no tiene {}x{}; tiene {}".format(necesario, necesario,
                                                      sorted(lados)))


def test_la_app_usa_el_logo_nuevo():
    """icono_sistema() tiene que devolver la marca, no el logo anterior."""
    from libs.recursos import ruta_recurso

    # La funcion se cambia a que apunte al .png de la marca: si alguien vuelve
    # al nombre viejo, el test lo dice.
    ruta_utiles = os.path.join(RAIZ, "libs", "Utiles.py")
    with open(ruta_utiles, "r", encoding="utf-8", errors="replace") as f:
        texto = f.read()
    bloque = texto.split("def icono_sistema(")[1].split("\ndef ")[0]
    assert "imagenes/marca/logo-" in bloque or "marca/logo-vogel" in bloque, (
        "icono_sistema() no apunta al logo de la marca:\n{}".format(
            bloque[:400]))

    # Y que la marca exista de verdad, no que apunte a un archivo roto.
    assert ruta_recurso("imagenes/marca/logo-256.png")

    # El logo viejo queda solo si alguien lo usa a proposito; el de la ventana
    # no.
    assert "Logo S-01" not in bloque, (
        "icono_sistema() todavia usa el logo anterior")


def test_no_quedan_rutas_hardcodeadas():
    """Las rutas de icono a mano son las que se pierden al empaquetar."""
    malas = []
    for ruta, linea, referencia, tipo in REFERENCIAS:
        if tipo == "harcodeada" and _es_icono(referencia):
            malas.append("{}:{} -> {}".format(
                os.path.relpath(ruta, RAIZ), linea, referencia))

    assert not malas, (
        "Usar imagen() en vez de la ruta a mano (se pierden al empaquetar):\n  "
        + "\n  ".join(malas))


if __name__ == "__main__":
    print("referencias de icono en codigo real:", len(REFERENCIAS))
    print("")
    print("HARDCODEADAS (se pierden al empaquetar):")
    total = 0
    for ruta, linea, referencia, tipo in REFERENCIAS:
        if tipo == "harcodeada" and _es_icono(referencia):
            print("  {}:{} -> {}".format(os.path.relpath(ruta, RAIZ), linea, referencia))
            total += 1
    print("  total:", total)
    print("")
    print("ICONOS QUE NO EXISTEN:")
    from libs.recursos import ruta_recurso
    faltan = 0
    for ruta, linea, referencia, _tipo in REFERENCIAS:
        completa = _ruta_completa(referencia)
        if not completa or not _es_icono(referencia):
            continue
        if not ruta_recurso(completa):
            print("  {}:{} -> {}".format(os.path.relpath(ruta, RAIZ), linea, completa))
            faltan += 1
    print("  total:", faltan)
