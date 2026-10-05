# coding=utf-8
"""Control de caracteres raros en los archivos tocados.

En varios pasos se me colaron fragmentos en otros idiomas (chino, ruso) y uno
con letras al reves. Ninguno rompe el codigo, pero quedan en un archivo que el
equipo va a leer, y un `git diff` lleno de ruido esconde el cambio de verdad.

Busca caracteres fuera de latin-1 que no sean los de puntuacion que el doc ya
usa (comillas angulares, raya, puntos suspensivos, flecha, signo menos).
"""
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PERMITIDOS = {
    0x2014: "EM DASH", 0x2013: "EN DASH", 0x2026: "ELLIPSIS",
    0x00AB: "GUILLMET <<", 0x00BB: "GUILLMET >>", 0x00B0: "GRADO",
    0x2192: "FLECHA", 0x2212: "SIGNO MENOS", 0x00A0: "NO SEPARABLE",
}

ARCHIVOS = [
    "docs/STOCK.md",
    "docs/ETAPA-3-COMPONENTES.md",
    "tools/sembrar_stock.py",
    "tools/cargar_productos_prueba.py",
    "tools/capturar_stock_sembrado.py",
    "tools/capturar_dialogos.py",
    "libs/stock.py",
    "libs/Etiquetas.py",
    "libs/Formulario.py",
    "controladores/Stock.py",
    "controladores/VentaSimple.py",
    "vistas/VentaSimple.py",
    "vistas/Stock.py",
    "tests/test_semilla_stock.py",
    "tests/test_stock_en_venta.py",
    "tests/test_dialogos_chicos.py",
]

malos = []
for relativo in ARCHIVOS:
    ruta = os.path.join(RAIZ, relativo)
    if not os.path.isfile(ruta):
        continue
    with io.open(ruta, encoding="utf-8") as f:
        for numero, linea in enumerate(f, 1):
            for caracter in linea:
                codigo = ord(caracter)
                if codigo <= 0xFF or codigo in PERMITIDOS:
                    continue
                try:
                    nombre = __import__("unicodedata").name(caracter)
                except ValueError:
                    nombre = "?"
                malos.append((relativo, numero, hex(codigo), nombre, caracter))

if not malos:
    print("OK: sin caracteres raros en", len(ARCHIVOS), "archivos.")
    sys.exit(0)

print("Caracteres fuera de latin-1 sin ser puntuacion permitida:")
for relativo, numero, codigo, nombre, caracter in malos[:40]:
    print("  {}:{}  {}  {}  {!r}".format(relativo, numero, codigo, nombre,
                                        caracter))
print()
print("total:", len(malos))
sys.exit(1)