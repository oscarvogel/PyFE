# Emitir contra ARCA: el bug que impedía facturar

Fecha: 2026-10-03
Alcance: `libs/Compatibilidad.py`, `tests/test_compatibilidad.py`.
Cómo se apareció: al apretar **Emitir factura** en *Nueva venta* saltó

```
TypeError: aplicar_compatibilidad_pysimpleoap.<locals>.
wsdl_parse_sin_cache_pickle() got an unexpected keyword argument 'debug'
```

**No lo causó el trabajo de las pantallas.** El archivo viene del commit
`080f3ea` ("Fix ARCA billing diagnostics and packaging") y la app **no podía
emitir una sola factura** desde antes de tocar nada.

---

## Qué pasaba

`libs/Compatibilidad.py` parchea `pysimplesoap` para que el WSDL no deje un
pickle de cache. El parche declaraba una firma fija:

```python
def wsdl_parse_sin_cache_pickle(self, url, cache=False):
    return wsdl_parse_original(self, url, cache=False)
```

Pero la firma real de la versión instalada es:

```python
SoapClient.wsdl_parse(self, url, debug=False, cache=False)
```

y `SoapClient.__init__` la llama así:

```python
self.services = wsdl and self.wsdl_parse(wsdl, debug=trace, cache=cache)
```

`debug` no existe en el shim → `TypeError` **al construir el cliente SOAP**,
que es el primer paso de emitir. La app entera no podía facturar, con la base
llena de clientes y productos y los certificados correctos.

Es incompatibilidad de versión: el shim se escribió contra una versión de
`pysimplesoap` cuyo `wsdl_parse` no tenía `debug`, y la instalada sí lo tiene.

---

## Por qué 304 tests en verde no lo detectaron

Porque el test que existía **nunca llamaba a la función**:
```python
def test_compatibilidad_pysimplesoap_desactiva_cache_pickle_wsdl():
    aplicar_compatibilidad_pysimplesoap()
    assert getattr(SoapClient.wsdl_parse, "_pyfe_sin_cache_pickle", False) is True
```

Comprueba que el shim esté *instalado*. No que *funcione*. Es la misma
enfermedad del test que parcheaba `buscar_cliente` (un método que nadie
llama): la suite entera en verde, y el camino roto.

Consecuencia más incómoda: **el camino de emisión no lo cubría ningún test**.
Todo lo que se probaba era la aritmética de los totales y la pantalla; el
`SOAP` real, la versión de la librería, la conexión, nada.

---

## La solución

El shim ya no tiene firma propia: se adapta a la de la versión instalada.

```python
@functools.wraps(original)
def wsdl_parse_sin_cache_pickle(self, url, *args, **kwargs):
    kwargs.pop("cache", None)
    if args and cache_es_el_ultimo:
        args = args[:-1]
    kwargs["cache"] = False
    return original(self, url, *args, **kwargs)
```

Tres decisiones que no son obvias:

1. **`url` va declarado, no dentro de `*args`.** La primera versión lo metía en
   `*args` y "sacar el último argumento" se comía la URL en vez del cache. Hay
   un test que lo fija: si el shim se come el argumento equivocado, falla.
2. **Si `cache` llega por posición hay que sacarlo antes** de pasarlo por
   keyword, o Python se queja de valor repetido. En qué posición está se
   **mira de la firma instalada** con `inspect`, no se supone: ese es el
   propósito de un shim de compatibilidad.
3. **`functools.wraps`** hace que `inspect.signature` siga viendo la firma real
   del original, que es lo que permite validar la llamada con `bind()`.

---

## Verificación

| Qué | Cómo |
|---|---|
| La firma aguanta la llamada real | `inspect.signature(...).bind(obj, url, debug=True, cache=True)` — **falla antes del arreglo** |
| El shim apaga el cache y pasa el resto | shim con un doble que registra lo que recibe |
| El cache por posición | shim contra la firma antigua |
| Conexión real | `FEv1.Conectar(...)` → bajó el WSDL de `wswhomo.afip.gov.ar` |
| Login real | `FEv1.Autenticar()` → devolvió ticket de acceso de WSAA |
| **Emisión real** | `tools/probar_emision_hilo.py` → **CAE 86400944647369, resultado A** |
| **Existe en ARCA** | `tools/consultar_cae.py` → comprobante 10, tipo 6, AUTORIZADO, mismo CAE |
| Suite | **307 tests** |

Detalle de la emisión de prueba: corrió en un hilo distinto al principal
(2676 contra 41568) en 0,9 segundos, o sea que la ventana no se congela.

---

## Pendientes

- [x] **El camino de emisión sigue sin tener tests de contrato.** Ahora hay uno
      que valida la firma del shim contra la versión instalada, que es lo que
      se rompió. Lo que no hay es una prueba que arme el cliente SOAP de verdad:
      se puede agregar sin tocar la red, interrumpiendo el transporte y
      comprobando que llega hasta `wsdl_parse` con los argumentos correctos.
- [x] **`pyafipws` está dentro del repo** (`C:\Programacion\PyFE\pyafipws`), no
      instalado como dependencia. Ver la sección siguiente.
- [ ] **`requirements.txt` sigue pidiendo `fpdf==1.7.2`** y hay PyFPDF y fpdf2
      instalados los dos (avisa en cada corrida). Es el pendiente que ya estaba
      en la Etapa 5.
- [ ] **Conviene una prueba de humo de arranque** que diga qué versión de
      `pysimplesoap` encontró y con qué firma, para que un cambio de librería
      se note en el log y no en pantalla cuando alguien intente facturar.

---

# pyafipws: de "clon que alguien bajó" a instalable

## Lo que había

`pyafipws` no estaba en `requirements.txt` ni en el repo. Estaba en el
`.gitignore`, porque es un **clon git anidado** de `reingart/pyafipws`. Y en
el clon había, sin commitear en ningún lado:

- `8aeed1e` — *Handle ARCA single event responses*
- ~70 líneas de trabajo sobre `wsfev1.py`, `wscdc.py`, `ws_sr_padron.py`,
  `wsaa.py`, `pyemail.py` y `pyfepdf.py` para el formato de ARCA 2025
  (`FeDetReq` como objeto, respuestas de un solo evento, limpieza de vacíos).

Esos cambios son **lo único que hace que la app pueda emitir**. Un `rm -rf` del
clon, un `git clean`, o cambiar de máquina, y PyFE deja de facturar sin dejar
rastro: `import pyafipws` falla y no hay ningún paso documentado que lo
reconstruya.

**PyPI no sirve como salida.** El paquete `PyAfipWs` está congelado en
2.7.1874, subido en 2016, sin nada de ARCA 2025. Por eso el clon existe.

## La trampa que casi se cuela

Lo primero que se hizo fue pinear en el script el commit del clon de
desarrollo (`8aeed1e`). **Ese commit no existe en GitHub**: la rama `2025`
pública termina en `36d4c86`. El script fallaba con
`pathspec '8aeed1e' did not match any file(s) known to git` — un error que no
dice nada de que el problema es el pin.

Se detectó bajando pyafipws de GitHub en una carpeta limpia y tratando de
aplicar el parche, no leyendo el código. Hay un test que lo corta ahora:
`test_el_commit_pineado_existe_en_el_remoto`.

## La solución: clon pineado + parche versionado + script

- **`tools/instalar_pyafipws.py`** deja el clon en el estado correcto:
  clona `reingart/pyafipws` rama `2025`, hace checkout del commit público
  `36d4c86`, y aplica el parche. Verificado de punta a punta bajando de GitHub
  en una carpeta limpia.
- **`pyafipws_arca_2025.patch`** (267 líneas) vive en la raíz de PyFE, o sea
  versionado y revisable. Es el diff entre el commit público y el estado que
  emite hoy.
- **`--verificar`** no toca nada: importa la clase y pregunta si tiene los
  métodos de ARCA 2025. Es lo que mira el test de la suite.
- **`--destino`** permite probar el montaje en una carpeta descartable sin
  tocar el clon de desarrollo. Con eso se probó el camino de "máquina nueva".

Los cambios de ARCA 2025 quedaron además **commiteados en el clon**
(`8cf471b`), así que no dependen del parche para existir.

### Verificación

| Qué | Cómo |
|---|---|
| Clon de GitHub + pin + parche | `tools/instalar_pyafipws.py --destino <carpeta>` en una carpeta nueva |
| El parche aplica sobre el commit público | `git apply` sobre un clon limpio en `36d4c86` |
| El clon parcheado = el que emite hoy | 6 de 7 archivos idénticos; el séptimo difiere solo en finales de línea |
| El pin es obtenible | `git merge-base --is-ancestor` contra la punta del remoto |
| La app sigue emitiendo | `tools/probar_emision_hilo.py` → **CAE 86400944648904, resultado A** |
| Suite | 3 tests nuevos sobre el estado del clon |

Un detalle que salió en el camino: el `wsfev1.py` del clon de desarrollo tiene
finales de línea mezclados (CRLF y LF en el mismo archivo, 1711 de 1826). El
montaje desde cero los deja todos en LF, o sea que el camino reproducible
**embaraza** el clon en vez de dejarlo igual.

## Cómo se usa en una máquina nueva

```
pip install -r requirements.txt
python tools\instalar_pyafipws.py
python tools\instalar_pyafipws.py --verificar
```

Eso es lo que antes no existía.
