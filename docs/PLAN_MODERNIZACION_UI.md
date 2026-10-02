# Plan de modernización de interfaz — PyFE / Vogel Gestión Simple

Fecha: 2026-10-02
Rama de trabajo al momento del análisis: `codex/vogel-gestion-simple-mvp`
Alcance: modernizar, hacer más amigable y más profesional la **interfaz** de PyFE,
sin tocar la lógica contable ni el protocolo con ARCA.

---

## 1. Diagnóstico: qué está pasando hoy

La app **no tiene diseño**. No es que el diseño sea feo: es que no existe capa de
diseño. Todo se ve como PyQt5 se ve por defecto sobre Windows. Eso hace que cada
pantalla sea distinta, sin jerarquía y con un piso de profesionalidad muy bajo.

### 1.1 Los temas existen pero están muertos

Hay 7 archivos de estilos en `temas/` (`qdark.css`, `darkblue.css`, `aqua.css`,
`ubuntu.css`, etc.) y un combo `ComboTema` en `libs/ComboBox.py:245` que los lista.
Pero **nadie los aplica nunca**:

- `controladores/Main.py:87` → `self.EstableceTema()` está comentado.
- `main.py:144` → `QApplication(args)` se crea sin stylesheet; la línea que
  elegía estilo nativo (`-style Cleanlooks`) también está comentada (línea 143).

Resultado: corre con el estilo por defecto de Windows, y los `.css` son código
muerto. Este es el punto de apalancamiento más importante del plan: **un solo
stylesheet global cambia la apariencia de las 30+ pantallas de golpe**, sin
tocar ninguna vista.

### 1.2 La ventana principal está rota, no solo fea

`vistas/Main.py:13` abre la ventana en **620×150 px**, pero mete **9 botones en una
sola fila** `QHBoxLayout` (línea 20). Medido con el código real:

| Métrica | Valor |
|---|---|
| `sizeHint()` con fuente por defecto | **1618 px** de ancho |
| `sizeHint()` con Segoe UI 9 | **1117 px** de ancho |
| Ancho con el que se abre | **620 px** |

O sea: el contenido necesita hasta 1618 px y la ventana ofrece 620. En un monitor
de 1366 el último botón ("Salir") ya queda apretado; en un monitor de 1280, en
una notebook con escalado 125%, o con zoom, **se corta**. No es una cuestión
estética: es un bug de layout.

Además los 9 botones son **pares entre sí**: mismo tamaño, mismo peso, sin
agrupación. No hay "lo importante" ni "lo accesorio". Todo el producto tiene el
mismo peso visual, que es la definición de interfaz poco profesional.

### 1.3 Hay functionality muerta en la UI

`controladores/Main.py:287` define `onClickBtnCompras()`, pero:

- no existe ningún `btnCompras` en `vistas/Main.py`,
- no está en `conectarWidgets()` (`controladores/Main.py:90-99`).

**Consecuencia:** cinco funcionalidades completas son inalcanzables desde la
interfaz — Proveedores, Centro de Costos, Carga de Facturas de Proveedor,
IVA Compras y RG 3685 Compras. Hay un módulo entero de compras escrito, probado y
publicado que el usuario no puede abrir. Esto no estails de diseño: es un
agujero funcional que seArrange al rehacer el menú.

### 1.4 Iconografía incoherente

- Se usa `imagenes/if_bill_416404.png` **dos veces**: en "Nueva venta" y en
  "Comprobantes" (`vistas/Main.py:22` y `:31`).
- Mezcla de estilos y épocas: íconos `flaticon` con números en el nombre
  (`if_kuser_1400.png`), un Excel verde, una lupa con personas para "AFIP/ARCA",
  flecha verde de salida, ícono de people-circle para "Configuración".
- Resolución de rutas inconsistente: 22 usos de `"imagenes/..."` hardcodeado
  contra 74 usos del helper `imagen(...)`. Los hardcodeados son relativos al cwd,
  y el cwd de un `.exe` de una sola pieza no es el de la app — es el lugar desde
  donde el usuario hizo doble clic. En el ejecutable compilado, los íconos de las
  pantallas que usan ruta hardcodeada se pierden o se rompen.

### 1.5 Detalles de terminología y estado

- **Faltan acentos en toda la UI**: "Configuracion", "Comprobantes", "Codigo",
  "Emision de Factura", "Categorias monotributo", "Recategorizacion". En un
  producto que se vende a estudios contables, esto se lee como artesanía.
- **No se ve si la app está en homologación o producción.** `main.py:154` lo
  anuncia por `print()` a la consola — que el usuario nunca ve. En un sistema que
  emite comprobantes fiscales, que el modo sea ambiguo en pantalla es un riesgo
  operativo, no un detalle de estilo.
- Título con degradado azul→cian en cada pantalla (`libs/Etiquetas.py:32`,
  `qlineargradient`). Es el recurso visual por defecto de la era Windows Vista y
  es exactamente lo que hace que la app se lea como antigua.
- No hay barra de estado, ni indicador de connectivity con ARCA, ni última
  sincronización, ni breadcrumbs: el usuario no sabe en qué pantalla está ni qué
  está pasando.

### 1.6 Estado técnico

- **PyQt5 5.15.2** (Riverbank). Sigue manteniéndose, pero el ecosistema se movió
  a PyQt6/PySide6, y PyQt6 ya es 6.8. No es urgente, pero cada año nuevo cuesta
  más.
- Tests: 15 archivos, todos concentrados en lo agregado último (secretos DPAPI,
  instalador, primer arranque, venta simple). **No hay un solo test de UI ni de
  estilos.** Un restyle sin tests de humo visual es exactamente el tipo de cambio
  que se rompe en silencio.

---

## 2. Enfoque recomendado

**No reescribir. Modernizar la piel y el armazón, por capas, sin reescribir
lógica.**

Reescribir 30+ pantallas de un sistema fiscal que factura contra ARCA es la forma
más rápida de romper algo que hoy funciona. La ruta de menor riesgo y mayor
impacto es:

1. Una capa de diseño (tokens + QSS) queMejora **todas** las pantallas a la vez.
2. Un armazón de navegación nuevo solo en la ventana principal.
3. Un set de componentes base, que se va propagando pantalla por pantalla.
4. PyQt6 al final, o nunca, si el sistema sigueSteps funcionando.

Cada fase es independiente y entregable. Se puede parar después de cualquiera de
ellas y el usuario ya tiene un sistema visiblemente mejor.

---

## 3. Plan por fases

### Fase 0 — Fundaciones: capa de diseño (el mayor retorno)

**Objetivo:** que la app deje de verse como PyQt5 crudo, sin tocar una sola vista.

- Crear `temas/pyfe.css` como stylesheet único, con **design tokens**:
  paleta (primario, superficie, borde, éxito, advertencia, error, texto
  secundario), escala de espaciado, radios de esquina, tipografía y alturas de
  control.
- **Unificar la resolución de recursos**: extender el helper `imagen()` para que
  resuelva correctamente desde el bundle de PyInstaller y eliminar los 22 usos de
  `"imagenes/..."` hardcodeado. Esto además **arregla un bug real del ejecutable**.
- Activar el tema en `main.py` y **borrar los 7 `.css` muertos**, reemplazándolos
  por el sistema de tokens (o dejarlos solo como base de lectura, sin prometer un
  selector de temas que no funciona).
- Tipografía: una sola familia para toda la app. Corregir acentos en los strings
  de UI.

**Por qué va primero:** una sola línea de código cambia la apariencia de las 30+
pantallas. Es la diferencia entre "cambió la app" y "cambiaron 3 pantallas".

**Riesgo:** bajo. Es aditivo; si el QSS tiene un selector mal escrito, ese widget
queda con el estilo por defecto y no se rompe nada.
**Esfuerzo estimado:** 1–2 días.
**Aceptación:** la app abre con tipografía y espaciado consistentes; ningún ícono
falta en el ejecutable compilado.

---

### Fase 1 — Armazón nuevo de la ventana principal

**Objetivo:** convertir la pantalla de entrada en un shell de navegación real, y
de paso arreglar el desborde y recuperar el módulo de Compras.

- Reemplazar la fila de 9 botones por **sidebar de navegación** con secciones
  agrupadas por dominio, no por orden de desarrollo:
  - **Facturación** → Venta rápida, Comprobantes, Remitos, Reimpresiones
  - **Compras** → Proveedores, Carga de comprobantes, IVA Compras, RG 3685
  - **Clientes** → ABM, Cuenta corriente
  - **Stock** → Productos, Grupos, Informes
  - **ARCA / AFIP** → Diagnóstico, Consulta CUIT, Constatación, CAE, Importación
  - **Configuración** → Parámetros, Firma de correo, Certificados
- **Esto destapa las 5 funciones muertas del §1.3**: al armar la navegación por
  dominios, el bloque Compras entra con su botón y sus controladores ya escritos.
- Eliminar el patrón de `QMenu` pegado a la posición del cursor: la navegación
  debe ser visible, no escondida tras un clic.
- **Barra de estado** con: modo homologación/producción, CUIT y punto de venta,
  estado de conexión con ARCA, última copia de resguardo.
- **Chip de homologación permanente** en el header, con color distinto
  (hoy el modo solo existe en un `print()` invisible).

**Por qué va segundo:** es la pantalla que el usuario ve 50 veces por día, y es
donde está el bug de desborde.

**Riesgo:** medio en rango, bajo en código. Se toca el punto de entrada de todas
las funciones, así que hay que probar que las ~30 pantallas siguen abriendo.
**Esfuerzo estimado:** 2–3 días.
**Aceptación:** la ventana entra en 1024×768 sin cortar; los 6 dominios navegan;
las 5 funciones de Compras abren; el modo homo/producción es visible siempre.

---

### Fase 2 — Sistema de componentes

**Objetivo:** que las pantallas se vean como un mismo producto, no como 30
pantallas parecidas.

Rediseñar las clases base de `libs/`, que son la superficie de contacto real con
el 90% de las pantallas:

| Componente | Archivo | Qué cambiar |
|---|---|---|
| Botones | `libs/Botones.py` | Jerarquía primaria / secundario / terciario / peligro. Hoy todo es el mismo `QPushButton`. Botón de acción principal destacado. |
| Campos | `libs/EntradaTexto.py` | Altura, foco visible, estado de error, placeholder coherente. Hoy el color de foco es un inline `Dodgerblue` (línea 87). |
| Tablas | `libs/Grillas.py` | Alternancia de filas, encabezado, selección, zebra, alineación numérica a la derecha, totales. Es la pantalla que más se usa después de la venta. |
| Títulos | `libs/Etiquetas.py` | Sacar el degradado azul→cian. Reemplazar por jerarquía tipográfica real. |
| Formularios | `libs/Formulario.py` | Ancho de columna consistente, agrupación, botones de acción alineados a la derecha. |
| Combos / checks / spinner | `ComboBox.py`, `Checkbox.py`, `Spinner.py` | Altura y foco coherentes con los campos. |

Y limpiar el CSS inline disperso: hay `setStyleSheet("background-color: Dodgerblue")`
repartido en 7 archivos. Eso es deuda de estilos: cada uno es un parche. Con
tokens, se reemplaza por clases semánticas (`.campo--error`, `.campo--foco`).

**Riesgo:** medio. Cada componente base afecta muchas pantallas. Mitigación:
avanzar componente por componente, con el smoke test de §4.
**Esfuerzo estimado:** 3–5 días.
**Aceptación:** los 6 componentes con tokens aplicados; sin CSS inline de color
duplicado; foco de teclado visible en todos los controles.

---

### Fase 3 — Iconografía y coherencia visual

**Objetivo:** eliminar el "clipart aleatorio".

- Set único de íconos, un mismo trazo y un mismo peso. SVG en lugar de PNG
  (escala sin pérdida y se tiñen con `fill` desde el QSS, en vez de tener
  íconos de colores distintos por tema).
- Reemplazar los duplicados (el de factura usado dos veces) y las repurposiciones
  sin sentido (Excel para "Reportes", people-circle para "Configuración").
- Ícono de la aplicación y del instalador coherentes. Hoy conviven
  `logo_oscar_sin_fondo.png`, `logo-servin.jpg`, `logoafipfondoblanco.png` y
  `Logo S-01.png` en la misma carpeta.
- **Corregir todos los textos sin acento** en la interfaz y en títulos de ventana.

**Esfuerzo estimado:** 1–2 días.

---

### Fase 4 — Flujos y feedback (la parte "amigable")

**Objetivo:** que la app se sienta rápida y que el usuario no quede a ciegas.

- **Estado visible de operaciones largas**: hoy una emisión contra ARCA es una
  espera sin feedback. Agregar progreso con la etapa real ("autenticando",
  "enviando a ARCA", "obteniendo CAE", "generando PDF").
- **Errores accionables**: cuando ARCA rechaza, decir qué hacer, no sólo mostrar
  el código. Hoy el diagnóstico existe (`DiagnosticoAfip`) y se muestra en un
  `showAlert` de texto plano.
- **Confirmaciones donde duele**: emisión fiscal irreversible, borrados.
- **Atajos de teclado** en los flujos frecuentes (venta rápida).
- **Buscar** en lugar de navegar: con ~30 funciones, el buscador es más moderno
  y más rápido que cualquier menú.

**Esfuerzo estimado:** 3–4 días.
**Aceptación:** ninguna operación contra ARCA queda sin feedback visible.

---

### Fase 5 — PyQt5 → PyQt6 (decisión a tomar, no urgente)

**Recomendación: diferir.** Es la fase más costosa y la de menor retorno visual.
El salto a PyQt6 rompe la API (`exec_` → `exec`, `QDesktopWidget` fuera, cambios
en enums) y obliga a tocar las 30+ pantallas por código, no por estilo, con lo
que significa recargar todo el riesgo de un restyle en un solo momento.

Vale la pena **solo si** hay un motivo fuerte: fin de soporte de PyQt5, o una
dependencia que lo exija. Si se hace, va como fase propia, después de tener el
producto ya moderno y con tests, nunca mezclada con el restyle.

---

## 4. Red de seguridad: antes de tocar estilos

Un restyle sin verificación se rompe en silencio (un selector que no matchea, una
fuente que no existe, un ícono que no se empaqueta). Antes de la Fase 0:

- **Smoke test de ventanas**: instanciar las ~30 vistas offscreen
  (`QT_QPA_PLATFORM=offscreen`, como se hizo para este diagnóstico) y afirmar que
  ninguna revienta al construirse. Es barato y captura la mayoría de las
  regresiones de estilo.
- **Test de recursos**: afirmar que todo ícono referenciado existe en disco. Es
  el bug del ejecutable, detectado antes de empaquetar.
- **Capturas de referencia**: guardar PNGs de las pantallas clave antes y después,
  para poder comparar sin depender de la memoria.
- **Prueba real del instalador** después de la Fase 0, porque es donde se rompen
  las rutas de recursos.

**Regla del plan:** ninguna fase se da por terminada hasta que el `.exe` compilado
abre y se ve correcta. La UI se prueba en la app empaquetada, no en el repo.

---

## 5. Orden de ejecución y effort total

| # | Fase | Esfuerzo | Riesgo | Impacto visual |
|---|---|---|---|---|
| 0 | Fundaciones: tokens + QSS + recursos | 1–2 días | Bajo | **Muy alto** (30+ pantallas) |
| 1 | Armazón: sidebar + barra de estado | 2–3 días | Medio | Alto |
| 2 | Sistema de componentes (`libs/`) | 3–5 días | Medio | Alto |
| 3 | Iconografía + textos | 1–2 días | Bajo | Medio |
| 4 | Flujos, feedback, búsqueda | 3–4 días | Medio | Medio |
| 5 | PyQt6 (diferible) | 5–8 días | Alto | Bajo |

**Total hasta la Fase 4: 10–16 días de trabajo.**

Los Quick wins de las primeras 48 horas son, en orden: activar un QSS con tokens
(verde), arreglar las rutas de íconos del ejecutable (verde, y es un bug),
corregir acentos (verde, es trivial), y poner el chip de homologación/producción
(verde, y reduce riesgo operativo real).

---

## 6. Pendientes y preguntas abiertas

- [ ] **Decidir si PyFE se sigue distribuyendo con PyQt5 o se planifica PyQt6.**
      Es la única decisión que cambia el resto del plan.
- [ ] Confirmar si el módulo de **Compras** estaba deliberadamente oculto o si es
      un olvido. El plan asume que es un olvido y lo expone en la sidebar.
- [ ] Definir la identidad visual: ¿se mantiene la marca actual (Servin / Vogel) o
      hay identidad gráfica nueva? Los tokens quedan parametrizados, así que
      cambiarla después es barato, pero conviene saberlo antes de la Fase 0.
- [ ] ¿Se conserva el selector de temas?hoy promete 7 temas que no funcionan.
      Recomendación: sacar el selector, dejar un solo tema profesional.

---

## Bitácora

- **2026-10-02** — Auditoría inicial de la interfaz, sin modificar código de la
  aplicación. Serenderizaron la ventana principal de forma aislada (offscreen, sin
  base de datos y sin conexión a ARCA) para medirla y verla. Se documentó el
  diagnóstico y el plan.

  Artefactos de análisis, no forman parte de la aplicación:
  - `_preview_main.py` — script de render offscreen
  - `preview_main_620.png`, `preview_main_1366.png` — capturas

  **Nota de seguridad:** no se lanzó la aplicación real porque `sistema.ini` está
  en modo producción (`homo = N`) y arrastra la base de datos viva. Todo el
  análisis visual se hizo sobre las clases de vista aisladas, sin tocar datos.

  Bugs encontrados en el análisis, pendientes de arreglo:
  1. La ventana principal se abre en 620 px con contenido que necesita 1618 px.
  2. `onClickBtnCompras` no está conectado a ningún botón: 5 módulos
     (Proveedores, Centro de Costos, Carga de Proveedor, IVA Compras, RG 3685
     Compras) son inalcanzables desde la UI.
  3. 22 rutas de íconos hardcodeadas se rompen en el ejecutable compilado.
  4. Los 7 estilos de `temas/` son código muerto.
  5. El modo homologación/producción no es visible en la interfaz.
  6. Textos de UI sin acentos.
