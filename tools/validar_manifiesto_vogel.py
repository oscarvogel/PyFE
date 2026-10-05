"""Valida apps/<app_id>/latest.json contra el schema del repo vogel-releases.

El schema declara `additionalProperties: false`, asi que un campo de mas no es
inofensivo: hoy ningun pipeline lo valida en serio (los manifiestos de femag y
fgpy tienen campos que el schema prohibe), y cuando alguien escriba el
validador, todos los manifiestos van a fallar juntos.

Uso:
    python tools/validar_manifiesto_vogel.py
    python tools/validar_manifiesto_vogel.py --app asiento
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys

REPO = "oscarvogel/vogel-releases"


def _api(ruta):
    salida = subprocess.run(
        ["gh", "api", "repos/%s/contents/%s" % (REPO, ruta)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if salida.returncode:
        raise SystemExit("no se pudo leer {}: {}".format(ruta, salida.stderr))
    return json.loads(salida.stdout)


def _api_texto(ruta):
    """El contenido de un archivo, que en la API viene en base64."""
    datos = _api(ruta)
    if not isinstance(datos, dict):
        raise SystemExit("{} no es un archivo".format(ruta))
    return base64.b64decode(datos["content"]).decode("utf-8")


def _aplicar(validacion, tipo, valor, donde, problemas):
    """Lo minimo de JSON Schema para este schema, que es plano."""
    if tipo == "object":
        if not isinstance(valor, dict):
            problemas.append("{}: se esperaba un objeto".format(donde))
            return
        for clave in validacion.get("required", []):
            if clave not in valor:
                problemas.append("{}: falta '{}'".format(donde, clave))
        props = validacion.get("properties", {})
        if validacion.get("additionalProperties") is False:
            for clave in valor:
                if clave not in props:
                    problemas.append(
                        "{}: '{}' esta prohibido por additionalProperties:false"
                        .format(donde, clave))
        for clave, regla in props.items():
            if clave in valor:
                _aplicar(regla, regla.get("type"), valor[clave],
                         "{}.{}".format(donde, clave), problemas)
    elif tipo == "string":
        if not isinstance(valor, str):
            problemas.append("{}: se esperaba un texto".format(donde))
            return
        if "minLength" in validacion and len(valor) < validacion["minLength"]:
            problemas.append("{}: texto demasiado corto".format(donde))
        if "pattern" in validacion and not re.match(validacion["pattern"], valor):
            problemas.append("{}: '{}' no cumple {}".format(
                donde, valor[:60], validacion["pattern"]))
    elif tipo == "boolean":
        if not isinstance(valor, bool):
            problemas.append("{}: se esperaba verdadero/falso".format(donde))
    elif tipo == "integer":
        if not isinstance(valor, int) or isinstance(valor, bool):
            problemas.append("{}: se esperaba un numero entero".format(donde))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", help="solo esta app; sin el, todas")
    args = ap.parse_args()

    schema = json.loads(_api_texto("schema/latest.schema.json"))

    if args.app:
        apps = [args.app]
    else:
        crudo = _api("apps")
        apps = [d["name"] for d in crudo if d["type"] == "dir"]

    print("validando {} app/s contra schema/latest.schema.json\n".format(
        len(apps)))

    salida = 0
    for app in apps:
        problemas = []
        try:
            manifiesto = json.loads(_api_texto("apps/%s/latest.json" % app))
        except SystemExit as e:
            print("  {:<22} no se pudo leer: {}".format(app, e))
            salida = 1
            continue

        _aplicar(schema, "object", manifiesto, app, problemas)

        if problemas:
            salida = 1
            print("  {:<22} {} problema/s".format(app, len(problemas)))
            for p in problemas:
                print("      - {}".format(p))
        else:
            print("  {:<22} OK  (version {})".format(
                app, manifiesto.get("version", "?")))

    print()
    if salida:
        print("hay manifiestos que NO pasan el schema del repo")
    else:
        print("todos los manifiestos pasan el schema")
    return salida


if __name__ == "__main__":
    sys.exit(main())
