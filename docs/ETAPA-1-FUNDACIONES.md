# Etapa 1 — Fundaciones de la interfaz (Fase 0 del plan)

Fecha: 2026-10-02 → 2026-10-02
Rama: `codex/vogel-gestion-simple-mvp`
Plan de referencia: `docs/PLAN_MODERNIZACION_UI.md`

---

## Qué se hizo

Se implementó completa la **Etapa 1 (Fase 0)**: la app pasa de no tener ninguna
capa de estilo a tener un tema único, aplicado globalmente, con iconos propios y
textos corregidos. Se verificó sobre el **ejecutable compilado**, no solo en el
repositorio.

### 1. Sistema de tokens y tema único

`temas/pyfe.css` es ahora la única capa de estilo. Se aplica una sola vez sobre
la `QApplication` (`libs/tema.py`, invocado desde `main.py`), así que las 30+
pantallas heredan el mismo tema sin pedirlo una por una.

Paleta, tipografía, espaciado, bordes, radios, estados de foco, error y
deshabilitado. El contrato de tokens está documentado al final del propio CSS,
que es la fuente de verdad.

El estilo base pasó a **Fusion**: el de Windows deja controles con relieve y
degradados que el stylesheet no alcanza a tapar, y sus bordes cambian según la
versión de Windows.

### 2. Los 7 temas muertos, eliminados

Había 7 `.css` en `temas/` y **nadie los aplicaba nunca**:

- `libs/ComboBox.py:245` tenía un `ComboTema` que los offería, pero ningún código
  leía la selección.
- `controladores/Main.py` llamaba a `EstableceTema()`, que estaba comentado.
- `libs/Formulario.py` aplicaba un `.css` por diálogo, leyendo el parámetro
  `TEMA` de la base, dentro de un `except: pass`.

Ese último punto era un problema serio: `Configuración` mostraba un desplegable
**"Tema"** con 7 opciones que no hacían nada. Un usuario elegía "dark" y la app
no cambiaba nada. Se eliminó el control, su lectura y su guardado, y los 7 `.css`
se borraron.

### 3. Recursos: se arregló un bug del ejecutable

`libs/recursos.py` nuevo. Antes, los iconos se resolvían con
`ubicacion_sistema()`, que lee `iniciosistema` del `sistema.ini`. Eso se rompe de
dos maneras: si la instalación se copia a otra carpeta el valor apunta a la ruta
de la máquina original, y con un `.exe` de una sola pieza el cwd es desde donde
el usuario hizo doble clic.

Ahora se prueban varias carpetas base y se usa la primera donde exista el
archivo. Es autocurativo: un `sistema.ini` viejo se ignora.

Además había **22 llamadas con la ruta escrita a mano** (`imagen='imagenes/x.png'`),
que son justo las que se perdían al empaquetar. Todas pasan por el helper.

`tests/test_recursos_ui.py` lo verifica sobre el árbol de sintaxis real: 97
referencias, 0 hardcodeadas, 0 faltantes.

### 4. Empaquetado

`temas/` **no se copiaba a `dist/`**. Sin ese arreglo, el ejecutable de los
clientes arrancaba sin ningún estilo: exactamente el problema que se vino a
arreglar. Se agregó a `compila.bat` y `installer/verificar_dist.py` ahora exige
`pyfe.css` y los recursos gráficos del tema.

### 5. Set de iconos nuevo

28 iconos SVG monoline, un solo trazo, un solo grosor, grilla de 24×24, mismo
color (`tools/generar_iconos.py`). Los viejos eran clipart de distintas épocas
mezclado en la misma barra, con el mismo calendario rojo en "Nueva venta" y en
"Comprobantes".

Como hay ~75 pantallas pidiendo iconos por el nombre del PNG viejo, en vez de
tocarlas una por una se puso un **puente de traducción** en `imagen()`: toda la
app pasó al set coherente de una vez, y las pantallas se van migrando al API
nuevo `icono()` a medida que se tocan. El test mide el avance.

### 6. Limpieza visual

- **Degradado azul→cian** de cada título (`libs/Etiquetas.py`): era el recurso
  que hacía que la app se leyera como de la era Windows Vista. Ahora la jerarquía
  es tipográfica.
- **Fondo azul `Dodgerblue`** al perder el foco (`libs/EntradaTexto.py`,
  `libs/Spinner.py`): dejaba la pantalla llena de rectángulos azul fuerte. El foco
  y los estados los maneja el tema.
- **Colores de validación** dispersos en 7 archivos (azul = ok, amarillo = no
  encontrado): ahora son estados semánticos (`ok` / `error` / `aviso`) y el color
  lo decide el tema.
- **Tablas**: se pintaba celda por celda en blanco, lo que tapaba el color
  alternado y hacía imposible cualquier tema distinto. Ahora usa la paleta, con
  filas alternadas y encabezado fijo.
- **Botones "OK" / "Cancel"** en inglés en 4 diálogos: el proyecto ya los traducía
  a mano en otros dos. Se unificó con `botonera_dialogo()`.
- **Textos sin acento** en 28 lugares de la interfaz.

### 7. Bugs arreglados que no eran de estilo

1. **La ventana principal no cabía en pantalla.** Los 9 botones en una fila
   pedían 1618 px y se abría en 620. Con el tema nuevo, el padding de los botones
   lo llevaba a **1836 px** — el tema empeoraba el bug. Ahora es una grilla 3×3
   de ~620 px.
2. **`onClickBtnCompras` no estaba conectado a ningún botón.** Cinco módulos
   completos (Proveedores, Centro de Costos, Carga de Proveedor, IVA Compras,
   RG 3685 Compras) eran inalcanzables desde la UI. Sigue sin exposed en el plan
   de la Etapa 2 (sidebar).
3. **Rutas de íconos rotas en el ejecutable** (los 22 hardcodeados).

### 8. Red de seguridad

- `tests/test_recursos_ui.py` — escanea el AST de los 152 `.py`: ningún ícono
  inexistente, ninguna ruta a mano, y mide la migración de iconos.
- `tests/test_smoke_ui.py` — monta 7 pantallas offscreen y verifica que se
  construyen, que **no desbordan** y que el tema está aplicado de verdad.
- `tools/render_ui.py` — renderiza pantallas a PNG sin base ni ARCA, para
  iterar sin levantar la app. Avisa si una ventana necesita más ancho del pedido.
- `tools/generar_iconos.py` — genera el set de iconos, con hoja de contactos.
- `tools/armar_sandbox.py` — instalación de prueba aislada en homologación, con
  base vacía, por si hay que correr la app sin tocar la de producción.

**Suite: 141 tests, todos en verde.**

---

## Cómo se verificó

| Qué | Cómo |
|---|---|
| Estilos | Render offscreen con fuentes reales de Windows (`docs/ui/`) |
| Pantallas | Smoke test: construcción + desborde, 7 vistas |
| Iconos | Test de recursos sobre el AST + hoja de contactos |
| **App real** | `compila.bat` + ejecutable corrido en pantalla |
| Distribución | `installer/verificar_dist.py` |

La prueba de la app real se hizo sobre una **copia aislada** de `dist/`, nunca
sobre la instalación del usuario: el `sistema.ini` del repositorio está en modo
**producción** (`homo = N`) con los datos de facturación reales, y no se corrió
la app contra esa base ni un minuto. El ejecutable se launched sin configuración,
así que arrancó en el asistente de primer arranque; se completó con una base
vacía y se verificó la pantalla principal.

---

## Bugs encontrados durante el trabajo

Se anotan porque son la clase de cosa que no se ve en el código:

1. **La app revienta con los `.py` en latin1.** `controladores/Facturas.py`,
   `FE.py`, `Remitos.py` ya tenían caracteres de reemplazo y `pyqr.py`,
   `WSConstComp.py` no son UTF-8. Un script de reemplazo automático los habría
   **corrupto permanentemente**. El script de acentos quedó con una guarda que
   los salta y los avisa.
2. **El reemplazo automático de acentos partió palabras.** Sin límites de
   palabra, "Seleccionar" quedó "Selecciónar", "Reimpresiones" quedó
   "Reimpresiónes", "Observaciones" quedó "Observaciónes". Corregido a mano, 14
   casos.
3. **`Formulario.__init__` importa `ParamSist` sin usarlo.** Se dejó el import a
   propósito: importar el módulo registra el modelo en peewee y casi todas las
   vistas importan `Formulario`. Sacarlo podía cambiar el orden de registro.
4. **La flecha del desplegable:** primero salió un **cuadrado negro** (Qt no
   dibuja triángulos con bordes CSS en un subcontrol), después **desapareció**
   (con un `QComboBox` estilizado, Fusion no pinta el indicador). Se resolvió
   generando un chevron propio y resolviendo las `url()` del CSS a rutas
   absolutas al cargar el tema, porque Qt las busca contra el cwd.

---

## Pendientes

### Para la Etapa 2 (siguiente)

- [ ] **Sidebar de navegación** con los 6 dominios, reemplazando los 9 botones
      parejos. Es lo que destapa los 5 módulos de Compras que hoy no se pueden
      abrir.
- [ ] **Barra de estado** con homologación/producción, CUIT, punto de venta y
      estado de ARCA. El modo sigue solo en un `print()` que el usuario nunca ve.
- [ ] Propagar `estilo='primario' | 'peligro'` al resto de las pantallas. La
      jerarquía existe (`Boton(estilo=...)`); solo está aplicada en
      `VentaSimple`.
- [ ] Seguir migrating los ~75 `imagen('x.png')` a `icono('nombre')` y borrar el
      puente de `MAPEO_ICONOS_VIEJOS` cuando el contador llegue a cero.
- [ ] Revisar el ancho de las columnas numéricas de las tablas y el ancho de
      `Cantidad` en la venta.

### Decisiones que le tocan al usuario

- [ ] **Compras:** ¿el módulo estaba oculto a propósito o es un olvido? El plan
      asume olvido.
- [ ] ¿Se quiere conservar la marca actual (Servin / Vogel) o hay identidad
      gráfica nueva? Los tokens quedan parametrizados, así que cambiarla después
      es barato, pero conviene saberlo.
- [ ] La carpeta `imagenes/` tiene 4 logos distintos (`logo_oscar_sin_fondo.png`,
      `logo-servin.jpg`, `logoafipfondoblanco.png`, `Logo S-01.png`) y 3 `.ico`.
      Falta decidir cuál es la marca.

### Diferido con motivo

- [ ] **PyQt5 → PyQt6.** Diferido a propósito: rompe la API, obliga a tocar las
      30+ pantallas *por código* y recarga todo el riesgo de un restyle en un
      solo momento. Es la fase más cara con el menor retorno visual. Solo si
      aparece un motivo fuerte (fin de soporte, o una dependencia que lo exija).

### Riesgo operativo sin resolver

- [ ] **El modo homologación/producción no es visible en la interfaz.** En un
      sistema que emite comprobantes fiscales, que sea ambiguo en pantalla es un
      riesgo, no un detalle de estilo. Entra en la Etapa 2 con la barra de estado.

---

## Cómo seguir trabajando con esto

```bash
# Ver una pantalla sin levantar la app ni tocar la base
python tools\render_ui.py            # todas
python tools\render_ui.py VentaSimple

# Regenerar los iconos (despues de editar el set)
python tools\generar_iconos.py
python tools\generar_iconos.py --preview    # hoja de contactos en docs/ui/

# Levantar la app contra una base vacia, en homologacion
python tools\armar_sandbox.py
cd _sandbox_prueba && python main.py

# Tests
python -m pytest tests\ -q
```

**Regla de la etapa:** la UI se prueba en el ejecutable compilado, no en el
repositorio. Un selector mal escrito en el CSS no da error: el control queda sin
estilo en silencio, y eso no se detecta hasta que lo mira un cliente.
