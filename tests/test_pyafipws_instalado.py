# coding=utf-8
"""Que pyafipws esté montado como para poder emitir, y que siga estándolo.

Por que existe este archivo
---------------------------
`pyafipws` no está en `requirements.txt` ni en el repo: está en el
`.gitignore` porque es un clon aparte de `reingart/pyafipws`, y en PyPI quedó
congelado en 2016. O sea que la emisión contra ARCA depende de un clon que
nadie instala, en una máquina, con cambios a mano. Ya pasó: había dos commits
—incluidos los arreglos del formato de ARCA 2025— que existían solo en el
disco, y sin esto nadie se enteraba hasta apretar "Emitir factura".

Estos tests miran lo que importa: que el clon esté, que tenga los arreglos, y
que el commit pineado exista en el remoto (que es la trampa: pinear un commit
local da un error que no dice nada).
"""

import importlib.util
import os
import subprocess
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def _cargar_script():
    ruta = os.path.join(RAIZ, "tools", "instalar_pyafipws.py")
    spec = importlib.util.spec_from_file_location("instalar_pyafipws", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_clon_de_pyafipws_esta_y_tiene_los_arreglos_de_arca_2025():
    """Sin esto, la app no puede emitir y no hay forma de saberlo antes.

    El mensaje del assert dice que hacer, asi que el que se encuentra con el
    test en rojo no tiene que leer el codigo para salir del paso.
    """
    modulo = _cargar_script()
    ok, problema = modulo.verificar(silencioso=True)
    assert ok, (
        "pyafipws no esta listo para emitir.\n  {}\n"
        "  Se arregla con: python tools/instalar_pyafipws.py".format(problema))


def test_el_commit_pineado_existe_en_el_remoto():
    """La trampa: pinear un commit que solo existe en esta maquina.

    Pinear `8aeed1e` (el commit del clon de desarrollo) hace que el script
    falle en cualquier otra maquina con "pathspec did not match any file known
    to git", que no dice nada de que el problema es el pin. Este test corta
    eso antes de que llegue a una maquina de un cliente.
    """
    modulo = _cargar_script()

    remoto = subprocess.run(("git", "ls-remote", modulo.ORIGEN, "refs/heads/" + modulo.RAMA),
                            capture_output=True, text=True)
    if remoto.returncode != 0:
        pytest.skip("sin red: no se puede mirar el remoto")

    lineas = [l for l in remoto.stdout.splitlines() if l.strip()]
    assert lineas, "la rama {} no existe en {}".format(modulo.RAMA, modulo.ORIGEN)
    puntero_remoto = lineas[0].split()[0]

    base = modulo.COMMIT_BASE
    # El pin tiene que ser un SHA completo: una abreviatura se puede resolver
    # distinto segun que commits haya, y un dia deja de resolver.
    assert len(base) == 40, (
        "el commit pineado deberia ser el SHA completo, no '{}'".format(base))

    # Lo que se pregunta es si el commit pinado se puede BAJAR de la rama
    # publica. Con la punta del remoto en la mano, la forma barata de saberlo
    # es preguntar si es ancestro de ella, y eso se responde con el clon local
    # (que ya tiene el historial del remoto). Si el pin es un commit local
    # como 8aeed1e, el clon lo tiene pero la rama publica no: es descendiente
    # de la punta, no ancestro, y el test lo dice.
    clon = os.path.join(RAIZ, "pyafipws")
    if not os.path.isdir(os.path.join(clon, ".git")):
        pytest.skip("no hay clon local contra el que comparar")

    ancestro = subprocess.run(
        ("git", "-C", clon, "merge-base", "--is-ancestor", base, puntero_remoto),
        capture_output=True, text=True)
    if ancestro.returncode == 128:
        pytest.skip("el clon local no conoce el commit del remoto")
    assert ancestro.returncode == 0, (
        "el commit pineado {} no se puede bajar de la rama {} de GitHub "
        "(punta {})\n"
        "  O el pin quedo viejo, o se pinteo un commit que solo existe en esta "
        "maquina: el script no va a funcionar en ningun lado mas.".format(
            base[:12], modulo.RAMA, puntero_remoto[:12]))


def test_el_parche_que_arma_el_clon_esta_en_el_repo():
    """El parche es la mitad de la reproducibilidad.

    Sin el, un clon nuevo queda en el commit de 2016 del formato viejo y no
    hay forma de saber que es lo que falta.
    """
    modulo = _cargar_script()
    parche = os.path.join(RAIZ, modulo.ARCHIVO_PARCHE)
    assert os.path.isfile(parche), (
        "falta {}. Es lo que hace que un clon nuevo sirva para emitir.".format(
            modulo.ARCHIVO_PARCHE))
    # Y que no este vacio: un parche de 0 bytes "aplica" y no arregla nada.
    assert os.path.getsize(parche) > 1000, "el parche esta vacio o es trivial"
