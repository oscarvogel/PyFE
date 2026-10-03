# Etapa 2 — Navegación y estado (Fase 1 del plan)

Fecha: 2026-10-02
Rama: `codex/vogel-gestion-simple-mvp`
Etapa anterior: `docs/ETAPA-1-FUNDACIONES.md`
Plan de referencia: `docs/PLAN_MODERNIZACION_UI.md`

---

## Qué se hizo

La pantalla principal dejó de ser una fila de 9 botones. Ahora es un armazón con
**barra lateral por dominios, área de contenido y barra de estado**, y todo lo que
la app puede hacer quedó expuesto a la vista.

Lo más importante de esta etapa no es el aspecto: es que **destapó 5 módulos
completos que eran inalcanzables** y que ahora hay un test que impide que vuelva
a pasar.

---

## 1. El problema que había

La pantalla anterior eran 9 botones iguales. Cada uno abría un `QMenu` que
aparecía **pegado a la posición del cursor**, y el controlador comparaba el
`QAction` devuelto con una cadena de `if/elif`.

Detrás de esos 9 botones había **36 acciones distintas**, y el orden no seguía
ninguna lógica de uso: dependía del orden en que se fueron escribiendo los
controladores.

Y faltaba lo peor: `onClickBtnCompras()` estaba definido en
`controladores/Main.py` pero **no había ningún botón que lo llamara**. Cinco
módulos enteros —Proveedores, Centros de costo, Carga de comprobantes, IVA
compras y RG 3685 compras— con su controlador, su vista y sus tablas, escritos y
probados, **sin forma de abrirlos**. El código funcionaba perfecto y era
inalcanzable.

Nada en el código hacía ruido por eso. No hay excepción, no hay warning: un
módulo sin botón no se ve desde ningún lado.

---

## 2. La navegación nueva

`vistas/Main.py` declara `SECCIONES`, que es la **única fuente de verdad** de lo
que la app puede hacer:

| Sección | Acciones |
|---|---|
| Facturación | Venta rápida, Comprobantes, Remitos, Recibos, Reimprimir factura, Reimprimir remito |
| **Compras** | **Proveedores, Centros de costo, Cargar comprobantes, IVA compras, RG 3685 compras** |
| Fiscal | IVA ventas, RG 3685 ventas, Importar comprobantes |
| Clientes | Alta y modificación, Cuenta corriente, Enviar por email |
| Stock | Productos, Grupos, Impuestos, Ventas por grupo |
| ARCA / AFIP | Diagnóstico, Consulta de CUIT, Constatación, Consulta de CAE, Rinde CAEA |
| Monotributo | Categorías, Informe de recategorización |
| Catálogos | Localidades, Tipos de comprobante, Tipos de documento, Tipos de responsable |
| Configuración | Configuración de inicio, Parámetros, Firma de correo, Certificados |

**36 acciones, 9 secciones, todas agrupadas por lo que el usuario quiere hacer y
no por el orden en que se escribieron los controladores.**

Las 5 de Compras era el requisito: estaban escritas, solo faltaba exponerlas.
También se recoupó **Enviar por email**, que tampoco tenía acceso.

Se descubrió además que `ObtieneCAEAView` es una pantalla a medio hacer (tiene
vista pero ni controlador ni llamada al web service) y que `CtaCteController` es
un cascarón vacío. **No se agregaron a la navegación a propósito**: un botón que
abre una pantalla cuyo botón principal no hace nada es peor que un botón que no
está. Quedan anotadas como pendientes.

### Cómo se cablea

La vista emite una clave; el controlador tiene un mapa `clave -> destino`:

```python
"proveedores": lambda: self._abrir(ProveedoresController, usar_exec=False),
```

Eso sustituye al patrón de `QMenu` + `if/elif` sobre `QAction`, y trae una
ventaja concreta: **agregar una acción es agregar dos líneas** (una en la vista,
una en el mapa) y **una acción sin destino es detectable**.

---

## 3. El modo homologación/producción, en pantalla

Este era el punto más serio del plan. El sistema emite comprobantes fiscales y el
modo **solo se anunciaba con un `print()` a una consola que el usuario nunca
ve**. Que no quede la duda de si se está por facturar a AFIP de verdad no es un
detalle de estilo.

Ahora:

- **Chip permanente en el encabezado**, con texto explícito y color distinto:
  ámbar `HOMOLOGACIÓN · no factura a AFIP` / rojo `PRODUCCIÓN · factura a AFIP`.
- **Barra de estado** con modo, CUIT, punto de venta, estado de ARCA, fecha del
  último resguardo y versión.

---

## 4. Bugs encontrados y arreglados

### 3.1 Los botones de la barra lateral no hacían nada

El más importante de la etapa, y el más barato de no ver.

`ItemNavegacion` se creaba, se dibujaba, se le ponía el ícono y se agregaba al
`QButtonGroup`, pero **faltaba el `boton.clicked.connect(...)`**. El clic
marcaba el botón y no pasaba nada más, sin error en ninguna parte.

Se encontró clickeando en el **ejecutable compilado**, no leyendo el código ni
mirando un render: en un render offscreen el botón se ve perfecto, porque el
problema no es de dibujo sino de cableado. Y no aparecía en el log, porque el
ejecutable se compila con `-w` (sin consola).

**Agregado:** `test_todos_los_botones_de_la_barra_emiten_su_clave` hace clic de
verdad sobre los 36 botones y comprueba que cada uno emita **su** clave. Se
verificó que el test falla si se saca el `connect` (mensaje: *"el boton 'Venta
rápida' emitio [] en vez de su propia clave"*).

### 3.2 Un error al abrir una pantalla moría en silencio

`onNavegar` corre dentro de un slot de Qt. Si una pantalla fallaba al
construirse, la excepción se perdía: con `-w` no hay consola donde se vea, y el
usuario solo ve que "no pasa nada". Ahora se muestra un aviso con el tipo de
error y se loguea el traceback.

Es un agujero general de este proyecto: `inicializar_y_capturar_excepciones` se
aplica a los métodos de los controladores, pero la navegación era el único
punto de entrada sin cubrir.

### 3.3 La ventana no entraba en una pantalla de 1024

El test de desborde lo detectó: con la barra lateral de 252 px, la ventana pedía
**1040 px** de ancho. Medido y ajustado a 228 px → 1016 px.

### 3.4 `Importar comprobantes` salía sin ícono y desalineado

La sección pedía un icono llamado `importar` que no existía en el set. Se
agregó al generador y ahora hay un test que verifica que **todo ícono de la
navegación exista de verdad** y que **todos los botones se vean con ícono** en
la vista armada (no solo en la lista), que es lo que detecta el caso en que el
archivo existe pero `QIcon` no lo carga.

---

## 5. Iconos: se cerró la migración de la Etapa 1

La Etapa 1 había dejado un **puente de traducción** en `libs.recursos`: `imagen()`
convertía los nombres viejos (`'new.png'`, `'delete.png'`) al set nuevo. Hacía
que todo se viera coherente sin tocar 75 llamadas, pero dejaba una tabla
permanente que nadie iba a entender dentro de seis meses.

Ahora:

- **72 llamadas migradas** de `imagen('x.png')` a `icono('nombre')`.
- **Puente eliminado.**
- Set ampliado de 28 a **43 íconos**, con los 14 de la barra de texto
  enriquecido (deshacer, copiar, pegar, negrita, alineaciones...).
- Copiar y Pegar tienen íconos propios: en un editor de texto la acción es lo que
  se distingue, y un ícono genérico de "documento" para los dos no dice nada.
- Quedan 3 llamadas a `imagen()` a propósito, documentadas en el test: el ícono
  de la ventana, el logo de ARCA que se estampa en el PDF y el logo provincial
  de la carga de compras. No son iconos de interfaz, son contenido.

---

## 6. Jerarquía de acciones en el resto de las pantallas

El tema ya distinguía acción principal / destructiva / terciaria, pero solo
estaba aplicado en 2 pantallas. Ahora está en **19**, incluida `vistas/ABM.py`,
que es la base de todos los ABM (grupos, impuestos, localidades, tipos de
documento, proveedores...): el cambio se ve en todas de una.

La regla aplicada por script, con una restricción deliberada: **un solo botón
principal por pantalla**. Si una pantalla tenía dos candidatos, no se marca
ninguno, porque dos acciones principales equivalen a ninguna. Pasó con
`Clientes.py` (tenía "Cargar" y "Agregar" en la misma barra) y quedó anotado
para que lo decida alguien que conozca el flujo.

---

## 7. Dato sucio encontrado en la configuración

`[FACTURA] cuit` tiene el valor **`Cuit 20-12345678-9`**, con el rótulo pegado
adentro de un copiar y pegado desde una etiqueta de pantalla. La barra de estado
lo mostraba como "CUIT Cuit 20-12345678-9".

**No rompe la facturación:** el CUIT que se usa para emitir sale de `[WSFEv1]` y
ese está limpio. La vista ahora filtra el valor para no mostrar basura.

**Pendiente para vos:** corregir `[FACTURA] cuit` en `sistema.ini` desde
Configuración, que es donde se edita.

---

## 7. Marca: el logo de Vogel Consultoria

La carpeta `imagenes/` tenía **4 logos distintos y 3 `.ico`**
(`logo_oscar_sin_fondo.png`, `logo-servin.jpg`, `logoafipfondoblanco.png`,
`Logo S-01.png`, `logo.ico`, `servin.ico`, `Logo S-01.ico`) y no se sabía cuál
era el bueno. Se adoptó el logo de **Vogel Consultoria** y se puso en todas
partes, generado desde un único original:

| Dónde | Archivo |
|---|---|
| Original | `imagenes/marca/logo-vogel.png` |
| Icono de la app (barra de tareas, ventanas) | `logo-16/24/32/48/64/128/256.png` |
| Icono del `.exe` y del instalador | `imagenes/marca/logo-vogel.ico` (7 resoluciones) |
| Encabezado del shell | `marca-48.png` (isotipo recortado) |
| Documentos | `marca-completa-{200,400}.png` |

Todo sale de `tools/generar_marca.py`, para que si se reemplaza el original y no
se regenera, el test de recursos lo diga.

**El recorte del isotipo está medido, no estimado.** El original tiene un símbolo
arriba y el nombre abajo, con un corte claro entre `y=752` y `y=817`; las
fracciones del recorte salen de ahí. Con un recorte a ojo se colaba un pedazo
de la palabra "VOGEL" abajo del símbolo.

En la interfaz el logo va sobre una placa con el navy de la marca (`#031A3E`),
que es el fondo del propio archivo: sin la placa, el cuadrado se ve como un
parche blanco pegado en el encabezado.

### Decisión pendiente, es tuya

El `PyFE.iss` sigue con `AppName "PyFE"` y `AppPublisher "Servin LGSM"`, y el
logo dice **Vogel Consultoria**. También `sistema.ini` tiene
`nombre_sistema = Servin - Sistema Factura Electronica`, que es lo que aparece
en el título de la ventana y en los avisos.

**No lo cambié por mi cuenta:** renombrar el producto es una decisión comercial,
no de interfaz. Decime y lo alineo en los tres lugares.

---

## 8. La paleta pasó a ser la de la marca

El tema usaba un azul genérico (`#1F5FA9`) que no era de nadie, mientras el
logo tenía su propia paleta. Se sacaron los colores **contando píxeles del
logo**, no a ojo:

| Token | Color | De dónde sale | Contraste verificado |
|---|---|---|---|
| Navy | `#031A3E` | fondo del logo | blanco encima: **17.2:1** |
| Azul | `#0863C6` | la barra del logo | blanco encima: **5.8:1** |
| Dorado | `#F4A807` | los nodos del isotipo | texto oscuro encima: **8.2:1** |
| Peligro | `#C62F35` | elegido por contraste | blanco encima: **5.4:1** |

### Cómo se aplica

- **El encabezado lleva el navy de la marca**, que es el mismo fondo del logo.
  Por eso el logo **no lleva placa ni marco**: se funde con el encabezado. Es la
  misma razón por la que antes hacía falta una placa — el PNG tiene fondo
  propio — y ahora no hace falta porque el fondo se eligió igual.
- **La app sigue siendo clara.** El navy entra solo por arriba y el dorado por
  el chip de homologación. Oscurecer toda la app la volvería cansada de leer
  con veinte columnas de una tabla fiscal.
- **Sidebar con un tinte de navy apenas perceptible** (`#EEF2F8`): la lista de 36
  acciones tiene que leerse rápido.
- **El chip de homologación pasó a dorado con texto oscuro.** El dorado es
  "atención: estás probando". El de producción es rojo con texto blanco.

### Un bug que la paleta destapó

Puse el subtítulo del encabezado en azul claro sobre el navy, pero **el mismo
`objectName` se usa en el panel de bienvenida**, que es claro: ahí el texto
quedó casi invisible. Lo acoté a `QFrame[objectName="encabezado"] QLabel[...]`.

### El test de contraste

`test_la_paleta_contrasta` recalcula el contraste WCAG desde los colores reales
del tema y exige 4.5:1 (AA) en ocho pares. **No es decorativo: ya atrapó un
error real.** El rojo del chip de producción lo elegí a ojo como `#E5484D` y
daba 3.91:1 con el texto blanco encima, por debajo del mínimo. Ahora es
`#C62F35` (5.4:1), que además se ve más serio para lo que significa.

---

## 9. Iconos que no se pierden en su propio fondo

Al probar el ejecutable se vio que el botón **"Nuevo"** de los ABM (el azul de
la barra, la acción principal) tenía el icono **azul sobre fondo azul**: se veía
el texto y un manchón, nada más.

Y en el botón de borrar pasaba lo simétrico: el texto en rojo pero el icono en
azul, o sea el dibujo decía otra cosa.

**Qt no sabe recolorear un `QIcon` desde el stylesheet**, así que la solución no
es de CSS: el set ahora se genera tres veces con la misma geometría y distinto
color de trazo.

| Carpeta | Para qué |
|---|---|
| `imagenes/iconos/*.svg` | Normal, sobre fondo claro |
| `imagenes/iconos/blanco/*.svg` | Botón primario (fondo azul) |
| `imagenes/iconos/peligro/*.svg` | Botón destructivo |

Y `Boton` elige solo: si recibe `estilo='primario'` o `estilo='peligro'`, toma
la variante que corresponde, mirando el nombre del archivo para funcionar
tanto si la llamada pasa `'nuevo'` como si pasa la ruta ya resuelta.

El test `test_los_iconos_de_botones_no_se_pierden_en_su_fondo` compara **pixel a
pixel** el icono del botón contra la variante esperada, así que si alguien
revierte el comportamiento sin querer, se ve.

---

## Cómo se verificó

| Qué | Cómo |
|---|---|
| Estructura de la navegación | `tests/test_navegacion.py`, 14 tests |
| Que los botones hagan algo | Clic real sobre los 36, en el test y en el `.exe` |
| Que no falte ningún destino | El test lee el mapa del controlador por `ast` |
| Que los iconos existan | Test sobre el set + vista armada |
| Desborde | Smoke de vistas, contra 1024×768 |
| **App real** | `compila.bat` + ejecutable corrido en pantalla |

**Suite: 161 tests, todos en verde** (empezaban en 120).

Como en la Etapa 1, la prueba de la app real se hizo sobre una **copia aislada**
de `dist/`: el `sistema.ini` del repositorio está en modo **producción** con los
datos reales y no se corrió la app contra esa base.

---

## Pendientes

### Para la Etapa 3 (sistema de componentes)

- [ ] **REDISEÑAR LA PANTALLA DE EMISIÓN DE COMPROBANTE.** Es lo que el usuario
      pidió cambiar y lo que más le cuesta hoy. Prioridad de esa etapa, con el
      objetivo de que **emitir una factura sea rápido**.

      Lo que se observó en la pantalla actual, para arrancar el rediseño con
      algo concreto y no desde "no me gusta":

      1. **El flujo es "cargar todo y después emitir".** Pide cliente,
         comprobante, período facturado, forma de pago, artículos, alícuotas,
         otros tributos, observaciones y autorización antes de poder emitir.
         Para una factura simple son demasiados pasos.
      2. **"Autorización AFIP" ocupa espacio siempre**, aunque la autorización
         pasa al final. Mientras se carga la factura no sirve de nada.
      3. **"Agrega" tiene el mismo tamaño que "Borrar"** y ocupa media fila:
         agregar un renglón a la grilla no es una acción de ese peso.
      4. **Los totales están a la derecha, desalineados**, y el botón Emitir
         está abajo a la izquierda. El ojo tiene que saltar de un extremo al
         otro para leer el total y decidir.
      5. **La fila superior mezcla cosas sin jerarquía**: Comprobante, Nº,
         Cpbte Rel y Fecha en la misma línea, con Nº y Cpbte Rel
         deshabilitados.
      6. **No dice si la factura está lista para emitirse.** Falta un resumen
         de lo que falta.

      **Pregunta abierta para esa etapa:** ¿la pantalla tiene que ser "cargar
      todo con detalle" o "emitir rápido y completar después"? De ahí sale la
      mayor parte del diseño, así que conviene responderlo antes de tocar una
      línea.

- [ ] Buscador en la barra lateral. Con 36 acciones hoy se navega con scroll,
      y es la pieza que más mejora con el tiempo.
- [ ] Revisar el ancho de las columnas numéricas de las tablas y el de `Cantidad`
      en la venta.
- [ ] `Clientes.py`: definir cuál de "Cargar" / "Agregar" es la acción principal.
- [ ] Con 36 acciones, un **buscador** va a ser necesario; hoy se navega con
      scroll. Es la pieza que más mejora con 30+ funciones.

### Decisiones que te tocan

- [ ] **Nombre del producto:** `AppName "PyFE"`, `AppPublisher "Servin LGSM"` y
      `nombre_sistema = Servin - Sistema Factura Electronica` siguen con el
      nombre viejo, mientras el logo dice Vogel Consultoria.
- [ ] `ObtieneCAEAView` está a medio hacer (vista sin controlador ni llamada al
      web service). ¿Se completa o se borra?
- [ ] `CtaCteController` es un cascarón vacío. ¿Se completa o se borra?
- [ ] `EmailClienteController` tiene `idcliente = 1` fijo: edita siempre los
      correos del cliente 1. Necesita contexto de cliente, así que quedó fuera
      de la navegación.
- [ ] Corregir `[FACTURA] cuit` en `sistema.ini` (tiene "Cuit " pegado).

### Riesgo operativo

- [ ] La barra de estado dice **"ARCA: sin consultar"**. Está bien que sea
      honesto, pero lo útil sería consultarlo y mostrar el último resultado.
      Conviene hacerlo con un botón explícito, no automático al arrancar, para no
      pegarle a ARCA sin querer.

### Diferido con motivo

- [ ] **PyQt5 → PyQt6**, igual que en la Etapa 1: es la fase más cara con el
      menor retorno visual, y mezclarla con el restyle recarga todo el riesgo en
      un solo momento.
