# coding=utf-8
"""Como se abre el PDF de un comprobante.

Solo Windows necesita algo especial, y por que
-----------------------------------------------
`os.startfile` (o `subprocess` con `xdg-open` en Linux, `open` en macOS) le
pasa el archivo al programa que el sistema tenga asociado a `.pdf`, y
despues ese programa decide. En Linux y macOS eso anda bien. En Windows no:
Foxit PDF Reader, que es de lo mas usado, corre como instancia unica, asi que
si ya tiene un documento abierto **ignora el segundo archivo sin avisar
nada**. El operador le da Imprimir, no se abre nada, y no hay forma de saber
si fallo la impresion o se quedo colgado el visor: el PDF se genero y quedo
guardado en `facturas/`, que es lo unico que paso. Cerrar la ventana de Foxit
no alcanza, porque el proceso sigue vivo en la bandeja del sistema.

En Windows el PDF se abre con el navegador, que abre una ventana nueva
siempre. En el resto se usa el mecanismo de cada sistema, que ya funciona.

Dos trampas que se comieron este codigo antes
---------------------------------------------
- `webbrowser.open` NO sirve para esto. En Windows su `WindowsDefault.open` es
  un `os.startfile(url)` envuelto en un try, asi que abrir una URL `file://`
  con el termina en el mismo visor de PDF. Devuelve True y no abria el
  navegador nunca. Por eso se busca el ejecutable.

- No hay que usar `cmd /c start`: hay que entrecomillar a mano, las rutas con
  espacios y acentos se rompen, y es inyeccion de comandos con una ruta que
  viene de la base. `os.startfile` ya es `ShellExecuteW`, o sea el shell de
  Windows sin esa parte mala.

Si no se puede abrir con ninguno, se devuelve None para que quien llame pueda
avisar en vez de dejar al operador creyendo que salio.
"""
import logging
import os
import platform
import subprocess

# (nombre, ruta relativa dentro de Program Files, Program Files (x86) o
# AppData\Local). Chrome y Edge pueden caer en cualquiera de las tres segun
# como se hayan instalado, asi que se buscan en las tres.
NAVEGADORES = (
    ("chrome", os.path.join("Google", "Chrome", "Application", "chrome.exe")),
    ("edge", os.path.join("Microsoft", "Edge", "Application", "msedge.exe")),
    ("firefox", os.path.join("Mozilla Firefox", "firefox.exe")),
)


def ruta_de_navegador():
    """El ejecutable del primer navegador instalado. None si no hay ninguno.

    Solo se usa en Windows. En el resto el sistema ya tiene su visor y no
    hay el problema que motiva esto.
    """
    bases = (os.environ.get("ProgramFiles"),
             os.environ.get("ProgramFiles(x86)"),
             os.environ.get("LOCALAPPDATA"))
    for _nombre, relativa in NAVEGADORES:
        for base in bases:
            if not base:
                continue
            ruta = os.path.join(base, relativa)
            if os.path.isfile(ruta):
                return ruta
    return None


def _abrir_con_el_sistema(ruta, imprimir=False):
    """El programa que el sistema tenga asociado. 'sistema' o None.

    En Windows `os.startfile` es `ShellExecuteW`. En macOS es `open` y en
    Linux `xdg-open`, que son los equivalentes de cada sistema.
    """
    try:
        sistema = platform.system()
        if sistema == "Darwin":
            # `open` no tiene forma de mandar a la impresora.
            subprocess.Popen(["open", ruta])
        elif sistema == "Windows":
            os.startfile(ruta, 'print' if imprimir else '')
        else:
            subprocess.Popen(["xdg-open", ruta])
        return 'sistema'
    except Exception as error:
        logging.error("no se pudo abrir %s con el visor del sistema: %s",
                      ruta, error)
        return None


def abrir_pdf(ruta, imprimir=False):
    """Abre un PDF. Devuelve 'navegador', 'sistema' o None si no se pudo.

    Con `imprimir` se va derecho al visor del sistema con el verbo de
    impresion: el navegador no se puede mandar a la impresora de forma
    confiable, y mandar a la impresora equivocada es peor que no mandar.
    """
    if not ruta or not os.path.isfile(ruta):
        logging.error("no hay PDF para abrir: %r", ruta)
        return None

    ruta = os.path.abspath(ruta)

    if not imprimir and platform.system() == "Windows":
        navegador = ruta_de_navegador()
        if navegador:
            try:
                subprocess.Popen([navegador, ruta])
                return 'navegador'
            except Exception as error:  # pragma: no cover - depende del equipo
                logging.debug("el navegador no abrio %s: %s", ruta, error)

    return _abrir_con_el_sistema(ruta, imprimir)
