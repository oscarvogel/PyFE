"""Comprueba que cada vista tenga los atributos que SU controlador usa.

El controlador de facturas tiene 154 referencias a `self.view.*` sobre 30
atributos. Escribirlos a mano uno por uno es como salen los errores: compila
todo, la pantalla abre, y el atributo que falta explode tres pantallas mas
abajo, cuando el operador llega a esa parte.

Recorre el par controlador/vista y dice que falta. Corre antes de tocar una
vista con 30 referencias colgando.
"""

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (controlador, vista). Solo los que tienen la vista en el atributo `view`.
PARES = [
    ("controladores/Facturas.py", "vistas/Facturas.py"),
    ("controladores/Remitos.py", "vistas/Remitos.py"),
    ("controladores/Articulos.py", "vistas/Articulos.py"),
    ("controladores/Clientes.py", "vistas/Clientes.py"),
    ("controladores/Proveedores.py", "vistas/Proveedores.py"),
    ("controladores/CentroCostos.py", "vistas/CentroCostos.py"),
    ("controladores/VentaSimple.py", "vistas/VentaSimple.py"),
    ("controladores/ConsultaCtaCte.py", "vistas/ConsultaCtaCte.py"),
    ("controladores/EnvioEmail.py", "vistas/EnvioEmail.py"),
    ("controladores/EmiteRecibo.py", "vistas/EmiteRecibo.py"),
    ("controladores/InformeVentasPorGrupo.py", "vistas/InformeVentasPorGrupo.py"),
]


def _leer(ruta):
    """Lee tolerando los archivos que estan en latin-1.

    Hay controladores viejos con tildes en latin-1, y un `open` sin `errors`
    corta el recorrido entero por un solo byte.
    """
    with open(ruta, "rb") as f:
        crudo = f.read()
    for codificacion in ("utf-8", "latin-1"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", "replace")


def _usados_por_el_controlador(ruta):
    arbol = ast.parse(_leer(ruta), ruta)
    usados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute) and nodo.attr == "view":
            # Lo que importa es el atributo de al lado: `self.view.gridFactura`
            # y `controller.view.btnGrabarFactura` usan el mismo camino.
            if isinstance(nodo.ctx, ast.Load):
                usados.add(nodo.id if False else None)
        if isinstance(nodo, ast.Attribute) and isinstance(nodo.value, ast.Attribute) \
                and nodo.value.attr == "view" and isinstance(nodo.ctx, ast.Load):
            usados.add(nodo.attr)
    usados.discard(None)
    return usados


def _definidos_en_la_vista(ruta):
    """Los `self.<algo> = ` de la clase, mas sus metodos.

    Los metodos tambien son contrato: el controlador llama `self.view.
    ActualizaTotales(...)` y si la vista no lo tiene, revienta al sumar los
    totales, que es en la tercera pantalla de uso.
    """
    arbol = ast.parse(_leer(ruta), ruta)
    definidos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute) and isinstance(nodo.value, ast.Name) \
                and nodo.value.id == "self" and isinstance(nodo.ctx, ast.Store):
            definidos.add(nodo.attr)
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definidos.add(nodo.name)
    return definidos


# Los que heredan de Formulario / Grilla / VistaBase y no aparecen escritos
# en la vista. Acarlos a mano seria inventar metodos que ya existen.
HEREDADOS = {
    "Cerrar", "cerrarformulario", "close", "show", "exec_", "controles",
    "tableView", "MostrarDeuda", "resize", "setWindowTitle", "isVisible",
}

problemas = 0
for controlador, vista in PARES:
    ruta_c = os.path.join(RAIZ, controlador)
    ruta_v = os.path.join(RAIZ, vista)
    if not (os.path.exists(ruta_c) and os.path.exists(ruta_v)):
        continue
    usados = _usados_por_el_controlador(ruta_c) - HEREDADOS
    definidos = _definidos_en_la_vista(ruta_v)
    faltan = sorted(usados - definidos)
    if faltan:
        print("{} -> {}: FALTAN {}".format(controlador, vista, ", ".join(faltan)))
        problemas += len(faltan)

print()
print("{} atributos que faltan en total".format(problemas))
sys.exit(1 if problemas else 0)
