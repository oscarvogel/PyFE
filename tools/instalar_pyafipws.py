# coding=utf-8
"""Deja pyafipws en el estado exacto con el que PyFE puede emitir.

Por que existe
--------------
`pyafipws` no está en `requirements.txt` ni en el repo: está en el
`.gitignore` porque es un clon aparte de https://github.com/reingart/pyafipws.
No se puede instalar desde PyPI porque ahí está congelado en la versión
2.7.1874, de 2016, sin los arreglos que ARCA exige desde 2025 (un comprobante
por respuesta, `FeDetReq` como objeto en vez de lista).

O sea: hoy, la única forma de que PyFE pueda emitir es que este clon esté en
la máquina con los cambios applied a mano. Si alguien clona PyFE en otra
máquina e instala `requirements.txt`, no puede facturar, y no hay ningún paso
documentado que lo arregle. Eso es lo que este script cierra.

Que NO hace
-----------
No manda nada a internet si el clon ya está. Y no borra un clon con cambios
sin preguntar: si encuentra trabajo sin commitear, para y lo dice.

Uso
---
    python tools/instalar_pyafipws.py              # deja el clon como debe
    python tools/instalar_pyafipws.py --verificar  # solo comprueba, no toca
    python tools/instalar_pyafipws.py --rehacer    # borra y vuelve a armar
"""

import argparse
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "pyafipws")

ORIGEN = "https://github.com/reingart/pyafipws.git"
RAMA = "2025"

# La punta de la rama 2025 PUBLICA. Se verificó contra GitHub con
# `git ls-remote origin refs/heads/2025` y da este mismo SHA, así que se puede
# bajar desde cualquier maquina.
#
# Ojo con esto, que es la trampa del asunto: el clon de desarrollo tiene dos
# commits que nunca se subieron (8aeed1e "Handle ARCA single event responses" y
# 8cf471b). Pinear uno de esos hacia un script que se puede correr en cualquier
# maquina daria un error incomprensible: "pathspec did not match any file known
# to git". Por eso la base es 36d4c86 y el parche lleva adentro los dos.
COMMIT_BASE = "36d4c8658bdac4d79c5e192064f7574d80652275"

# A donde deja el parche el clon de desarrollo. No hace falta compilarlo ni
# subirlo a ningun lado: sirve para que un humano pueda ver que el clon esta
# donde deberia. El parche de PyFE es el que aplica.
COMMIT_PARCHEADO = "8cf471b"

ARCHIVO_PARCHE = "pyafipws_arca_2025.patch"

# El nombre con que Python "mangla" el metodo privado que agregan los
# arreglos de ARCA 2025. Se busca en la clase importada y no en el texto del
# archivo: lo que importa es lo que la app importa, no lo que dice el fuente.
METODO_ARCA_2025 = "_WSFEv1__limpiar_valores_vacios"

# Se llena si el clon esta pero no se puede importar. Aparece en el mensaje de
# --verificar, que es el que mira uno cuando algo no anda.
PROBLEMA_IMPORT = ""


def _git(ruta, *args, **kwargs):
    return subprocess.run(("git", "-C", ruta) + args, capture_output=True,
                          text=True, **kwargs)


def _raiz_python():
    """La carpeta que tiene que estar en el path para poder importar.

    Es la que CONTIENE la carpeta `pyafipws`, no la carpeta misma. Con
    `--destino` puede ser otra, asi que se calcula y no se escribe fija.
    """
    return os.path.dirname(DESTINO)


def _existe_destino():
    return os.path.isdir(os.path.join(DESTINO, ".git"))


def _sin_cambios_sin_commitar():
    """Archivos modificados o sin commitear dentro del clon. Sin `cache/`,
    que son archivos generados al cachear el WSDL."""
    r = _git(DESTINO, "status", "--porcelain", "--", ".", ":(exclude)cache")
    return [linea for linea in r.stdout.splitlines() if linea.strip()]


def _tiene_los_arreglos():
    """Importa la clase como la importa la app y pregunta si tiene el metodo.

    Importar de verdad es lo que da la respuesta que importa: si el clon
    sirve o no. Y de paso detecta el otro problema, que el clon este pero con
    las dependencias de pyafipws sin instalar.

    Lo que hay que sumar al path es la RAIZ del repo, no la carpeta del clon:
    el paquete importable se llama `pyafipws` y es la carpeta `pyafipws/` que
    cuelga de la raiz. Con la carpeta del clon en el path, `import pyafipws`
    no encuentra nada.
    """
    if not os.path.isfile(os.path.join(DESTINO, "wsfev1.py")):
        return False
    raiz_python = _raiz_python()
    if raiz_python not in sys.path:
        sys.path.insert(0, raiz_python)
    try:
        from pyafipws.wsfev1 import WSFEv1
    except Exception as e:
        # Tragar el motivo deja el mensaje "no tiene los arreglos" cuando en
        # realidad lo que falta son las dependencias de pyafipws. Un
        # diagnostico que miente es peor que uno que no existe.
        globals()["PROBLEMA_IMPORT"] = "{}: {}".format(type(e).__name__, e)
        return False
    globals()["CLASE_WSFev1"] = WSFEv1
    return hasattr(WSFEv1, METODO_ARCA_2025)


def verificar(silencioso=False):
    """Devuelve (ok, problema). `ok` en False si el clon no sirve para emitir."""
    if not _existe_destino():
        return False, ("no hay clon en {}. Corre el script sin --verificar, "
                       "o `git clone -b {} {} pyafipws` y despues checkout "
                       "{} y aplicar {}".format(
                           DESTINO, RAMA, ORIGEN, COMMIT_BASE, ARCHIVO_PARCHE))
    if not _tiene_los_arreglos():
        if PROBLEMA_IMPORT:
            return False, ("el clon esta pero no se puede importar (falta una "
                           "dependencia de pyafipws): " + PROBLEMA_IMPORT)
        return False, ("el clon no tiene los arreglos de ARCA 2025. Falta "
                       "aplicar {} sobre el commit {}".format(
                           ARCHIVO_PARCHE, COMMIT_BASE))
    if not os.path.isfile(os.path.join(RAIZ, ARCHIVO_PARCHE)):
        return False, "falta el parche {} en la raiz de PyFE".format(ARCHIVO_PARCHE)
    if not silencioso:
        clase = globals().get("CLASE_WSFev1")
        if clase is not None:
            import pyafipws.wsfev1 as _mod
            print("  clase importada de: {}".format(_mod.__file__))
            print("  metodos de ARCA 2025: {}".format(
                sorted(m for m in dir(clase) if "limpiar" in m or "normalizar" in m)))
        print("pyafipws: clon en {} con los arreglos de ARCA 2025.".format(DESTINO))
    return True, ""


def clonar():
    print("Clonando {} rama {}...".format(ORIGEN, RAMA))
    r = subprocess.run(("git", "clone", "-q", "-b", RAMA, ORIGEN, DESTINO),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("No se pudo clonar:\n" + (r.stderr or r.stdout))


def dejar_en_el_commit_pineado():
    r = _git(DESTINO, "checkout", "-q", COMMIT_BASE)
    if r.returncode != 0:
        raise SystemExit("No se pudo ir a {}:\n{}".format(COMMIT_BASE, r.stderr))


def aplicar_parche():
    parche = os.path.join(RAIZ, ARCHIVO_PARCHE)
    if not os.path.isfile(parche):
        raise SystemExit("Falta el parche {}".format(parche))
    r = subprocess.run(("git", "-C", DESTINO, "apply", parche),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("El parche no aplico sobre {}:\n{}".format(
            COMMIT_BASE, r.stderr or r.stdout))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--verificar", action="store_true",
                       help="solo comprobar, no tocar nada")
    grupo.add_argument("--rehacer", action="store_true",
                       help="borrar el clon y volver a armarlo")
    p.add_argument("--destino", default=None,
                   help="carpeta donde clonar (por defecto la del repo). La "
                        "carpeta tiene que llamarse pyafipws, que es el "
                        "nombre con el que se importa. Sirve para probar el "
                        "montaje sin tocar el clon de desarrollo.")
    args = p.parse_args()

    if args.destino:
        destino = os.path.abspath(args.destino)
        if os.path.basename(destino) != "pyafipws":
            raise SystemExit(
                "La carpeta tiene que llamarse 'pyafipws': ese es el nombre "
                "del paquete que importa la app. Recibi: {}".format(
                    os.path.basename(destino)))
        globals()["DESTINO"] = destino

    if args.verificar:
        ok, problema = verificar()
        if not ok:
            print("pyafipws: NO esta en condiciones de emitir.")
            print("  " + problema)
            return 1
        return 0

    if args.rehacer and os.path.isdir(DESTINO):
        print("Borrando el clon actual de {}".format(DESTINO))
        shutil.rmtree(DESTINO)

    if _existe_destino():
        pendientes = _sin_cambios_sin_commitar()
        if pendientes:
            print("El clon tiene cambios que no estan en ningun commit:")
            for linea in pendientes[:10]:
                print("  " + linea)
            print("\nNo se toca nada. Con --rehacer se borra y se vuelve a "
                  "armar desde el commit pineado.")
            return 1

    if not _existe_destino():
        clonar()

    dejar_en_el_commit_pineado()
    aplicar_parche()

    ok, problema = verificar()
    if not ok:
        raise SystemExit("Se armo pero no queda bien:\n  " + problema)

    print("Listo. pyafipws quedo en {} + {}. El arbol coincide con el commit "
          "{} del clon de desarrollo.".format(COMMIT_BASE, ARCHIVO_PARCHE,
                                             COMMIT_PARCHEADO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
