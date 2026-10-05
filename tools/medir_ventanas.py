"""Mide quais janelas ficam cortadas pelo conteudo que pedem.

Por que medir em vez de olhar
-----------------------------
Olhar quarenta capturas da uma impressao. Medir diz quantos pixels faltam e
onde: uma janela de 100 px de altura nao esta "um pouco apertada", esta
esmagada ate nao caber uma linha.

De onde vem o numero
-------------------
`sizeHint()` e o tamanho que o layout PEDE. Se a janela e menor que isso, o
Qt esta cortando algo: um botao queda pela metade, um campo nao cabe, uma
coluna vira-scrollbar. E o que o operador chama de "apertado".

`minimumSizeHint()` e o menor tamanho ainda viavel. Abaixo disso nao da para
usar a tela, por isso um valor menor e um achado mais grave que uno apenas
apertado.

O que ele nao mede
------------------
Se a coluna da grade ficou de 56 px porque e o minimo de `_reparte_anchos`.
Isso nao e corte de janela, e corte de conteudo, e so se ve olhando.
"""

import ast
import importlib
import os
import sys

# La medicion se hace con la plataforma de Qt de verdad, no con offscreen: en
# offscreen la pantalla reporta 800x600 y todas las ventanas parecen mas
# grandes que la pantalla, lo que hace padrear el diagnostico. Con la real se
# mide contra la pantalla donde el operador trabaja.
if len(sys.argv) > 1 and sys.argv[1] == "offscreen":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])


def _claves_del_menu():
    from vistas.Main import SECCIONES
    claves = []
    for _t, _i, items in SECCIONES:
        for clave, _etiqueta, _icono in items:
            claves.append((clave, _etiqueta))
    return claves


def _controladores():
    """{clave: (modulo, clase)} leido de Main.py con ast."""
    ruta = os.path.join(RAIZ, "controladores", "Main.py")
    arbol = ast.parse(open(ruta, encoding="utf-8").read(), ruta)

    imports = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module and \
                nodo.module.startswith("controladores."):
            for alias in nodo.names:
                imports[alias.asname or alias.name] = nodo.module

    destinos = {}
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.FunctionDef) and nodo.name == "DESTINOS"):
            continue
        for sub in ast.walk(nodo):
            if not isinstance(sub, ast.Dict):
                continue
            for clave, valor in zip(sub.keys, sub.values):
                if not isinstance(clave, ast.Constant):
                    continue
                llamada = valor.body if isinstance(valor, ast.Lambda) else valor
                if not isinstance(llamada, ast.Call):
                    continue
                args = [a for a in llamada.args if isinstance(a, ast.Name)]
                if args and args[0].id in imports:
                    destinos[clave.value] = (imports[args[0].id], args[0].id)
    return destinos


def _describe(ventana, etiqueta, clave):
    for _ in range(6):
        app.processEvents()

    ancho, alto = ventana.width(), ventana.height()
    minimo = ventana.minimumSizeHint()

    # Columnas de grilla que quedaron en el minimo: se ven como una franja de
    # numeros, no como una columna.
    #
    # Las ocultas NO se cuentan: no se ven, y una columna oculta conserva un
    # ancho propio que no dice nada de como se ve la pantalla. Contarlas daba
    # falsos positivos en casi todas las grillas.
    columnas_chicas = []
    from PyQt5.QtWidgets import QTableWidget
    for grilla in ventana.findChildren(QTableWidget):
        for col in range(grilla.columnCount()):
            if grilla.isColumnHidden(col):
                continue
            if grilla.columnWidth(col) <= 60:
                encabezado = grilla.horizontalHeaderItem(col)
                columnas_chicas.append(
                    encabezado.text() if encabezado else "#{}".format(col))

    problemas = []
    # Lo que decide es `minimumSizeHint`, no `sizeHint`: el minimo es lo que el
    # layout NECESITA para no cortar nada. El sizeHint se infla con
    # contenedores sin layout (una pestana vacia pide 640x480 de default) y
    # por eso no sirve para decidir el tamano de la ventana.
    if minimo.width() > ancho:
        problemas.append("le faltan {} px de ancho (pide {} minimo)".format(
            minimo.width() - ancho, minimo.width()))
    if minimo.height() > alto:
        problemas.append("le faltan {} px de alto (pide {} minimo)".format(
            minimo.height() - alto, minimo.height()))
    if ancho < 620:
        problemas.append("chica: {} px de ancho".format(ancho))
    if columnas_chicas:
        problemas.append("columnas de 56px: {}".format(
            ", ".join(columnas_chicas[:6])))

    estado = "MAL " if problemas else "ok  "
    print("{}{:<26} {:>5}x{:<5} min {:>5}x{:<5} {}".format(
        estado, clave, ancho, alto, minimo.width(), minimo.height(),
        " | ".join(problemas) if problemas else ""))
    return problemas


def main():
    destinos = _controladores()
    pantalla = QApplication.primaryScreen()
    if pantalla is not None:
        area = pantalla.availableGeometry()
        print("pantalla real: {}x{}\n".format(area.width(), area.height()))

    print("ventana                     real        minimo       problema")
    print("-" * 100)

    malas = []
    for clave, etiqueta in _claves_del_menu():
        if clave not in destinos:
            continue
        modulo, clase = destinos[clave]
        try:
            controlador = getattr(importlib.import_module(modulo), clase)()
            app.processEvents()
            ventana = getattr(controlador, "view", None)
            if ventana is None or not hasattr(ventana, "minimumSizeHint"):
                continue
            ventana.show()
            problemas = _describe(ventana, etiqueta, clave)
            if problemas:
                malas.append((clave, etiqueta, problemas))
            ventana.close()
        except Exception as e:
            print("FALLA {:<26} {}".format(clave, e))

    print()
    print("=" * 100)
    if not malas:
        print("Ninguna pantalla se recorta.")
        return 0

    print("{} pantallas con problemas:\n".format(len(malas)))
    for clave, etiqueta, problemas in malas:
        print("  {} ({})".format(clave, etiqueta))
        for p in problemas:
            print("      - {}".format(p))
    return 1


if __name__ == "__main__":
    sys.exit(main())
