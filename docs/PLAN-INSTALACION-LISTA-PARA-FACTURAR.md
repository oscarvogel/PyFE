# Instalación lista para facturar

Plan, escrito antes de tocar código. Fecha: 2026-10-03.

La pregunta que lo origina: la instalación inicial hoy pide la base de datos y
pocos datos más, pero debería **dejar el sistema preparado para salir a
facturar** (valores iniciales, cliente consumidor final, tipos de IVA, etc.) y
además permitir **configurar los datos de la empresa después**, porque hoy viven
en `sistema.ini`.

Todo lo de abajo está verificado corriendo el código, no leyendo. Al final está
la bitácora de cómo se comprobó cada cosa.

---

## 1. Qué hace hoy la instalación, en orden

| Momento | Qué pasa | Dónde |
|---|---|---|
| Arranque | Se fija la carpeta de trabajo y se crea la `QApplication` | `main.py:105-125` |
| Arranque | Si no hay configuración, corre el asistente **antes** de tocar la base | `main.py:16-41` |
| Asistente | Pide base, datos fiscales, cat. IVA, pto. de venta, rutas de certificados | `vistas/PrimerArranque.py` |
| Asistente | Escribe `sistema.ini` y pone el marcador `configurado = S` | `libs/instalacion.py:101-174` |
| Arranque | Se crea el schema y se siembran los maestros desde `data/*.csv` | `controladores/Main.py:106-107` → `MigracionBaseDatos.py:132-217` |
| Después | Los datos de empresa se editan en *Configuración* | `vistas/Configuracion.py`, `controladores/Configuracion.py` |

**Lo bueno que ya existe y no hay que rehacer:**

- El asistente de primer arranque, con tests en `tests/test_instalacion.py`.
- **La siembra de datos maestros ya está hecha**: 14 CSV en `data/` que traen
  tipos de IVA, tipos de documento, tipos de responsable, tipos de comprobante,
  formas de pago, provincias, localidades, unidad, impuestos, centro de costos,
  grupos, artículos, cajeros y el **cliente CONSUMIDOR FINAL**.
- El diagnóstico de conexión a ARCA (`controladores/DiagnosticoAfip.py`), que
  además dice *qué hacer*, no sólo *qué pasó*.

**O sea: la mayor parte de lo que pedís ya está implementado.** El problema no es
la falta de siembra, es que la siembra está desconectada del asistente, hay datos
que el asistente nunca escribe, y nada verifica al final que la instalación quedó
completa.

---

## 2. Hallazgos

### 2.1 El CUIT que se usa para facturar no lo escribe nadie — **bloqueante**

El asistente escribe `FACTURA.cuit` (`libs/instalacion.py:140`). Pero al
emitir, el CUIT que viaja a ARCA es `WSFEv1.cuit`:

- `controladores/Facturas.py:576` → `controladores/Facturas.py:635` → `wsfev1.Cuit`
- `controladores/FE.py:92` y `FE.py:182`
- `controladores/DiagnosticoAfip.py:72`
- y sale impreso en la factura (`Facturas.py:900`, `Facturas.py:1048`)

`WSFEv1.cuit` llega al request de ARCA en `Auth.Cuit`
(`pyafipws/wsfev1.py:421`, y en las otras 14 llamadas).

**Ningún archivo del repo escribe `WSFEv1.cuit`.** En una instalación nueva queda
`00000000000`, que es lo que trae `sistema.ini.example:21`.

Consecuencia: se instala, se completa el asistente, y la app **no puede emitir**.
El `DiagnosticoAfip` tampoco lo detecta, porque sólo mira que el CUIT no esté
vacío, y `00000000000` no lo está (`DiagnosticoAfip.py:151`).

El propio banco de pruebas tiene que escribirlo a mano
(`tools/armar_prueba_facturacion.py:129`), lo que confirma que es obligatorio y
que nadie lo automatizó.

### 2.2 Las migraciones fallan siempre en una base nueva, y nadie lo ve

`MigracionBaseDatos.Migrar()` usa `MySQLMigrator` sin mirar qué base hay
(`controladores/MigracionBaseDatos.py:56`), pero en una instalación nueva los
modelos ya crean el schema final. Entonces `MigrarVersion1..7` corre y falla
siempre. Reproducido:

```
duplicate column name: impuesto
near "CONSTRAINT": syntax error
near "MODIFY": syntax error
duplicate column name: ing_brutos
duplicate column name: condicion_iva_receptor_id
```

`RealizaMigraciones` se come cada excepción (`:112-121`) y después
`GuardarParametro("VERSION_DB", "7")` sella la versión igual (`:85`).

Resultado: en una base nueva el sistema de migraciones es un no-op, el log se
llena de tracebacks y la versión queda marcada como si todo hubiera salido bien.

### 2.3 El asistente pide datos que después no se pueden corregir

- **Punto de venta**: el asistente lo escribe (`instalacion.py:148`) y
  *Configuración* ni lo lee ni lo escribe.
- **Inicio de actividades**: el asistente lo escribe (`instalacion.py:142`) y
  *Configuración* tampoco.
- **Condición frente al IVA** (`FACTURA.iva`): se usa en el pie de la factura
  (`Facturas.py:1050`) y **nadie lo escribe nunca**, ni el asistente ni
  *Configuración*. En una instalación nueva sale en blanco en cada factura.

Si se carga mal, el usuario tiene que editar `sistema.ini` a mano.

### 2.4 La lista de categorías de IVA está en tres lugares y no coinciden

| Lugar | Cuántas |
|---|---|
| `vistas/PrimerArranque.py:22-31` (`CATEGORIAS_IVA`) | 8 |
| `libs/ComboBox.py:195-203` (`ComboTipoRespIVA`, la de *Configuración*) | 3 (1, 4, 6) |
| `data/tiporesp.csv` (lo que se siembra en la base) | 4 (1, 2, 3, 4) |

El asistente ofrece el 5 (No Inscripto), el 8, el 9, el 10 y el 13, pero **no hay
fila de esos en `tiporesp`**, así que un cliente de esas categorías no se puede
guardar. Y *Configuración* sólo ofrece 3. Es el mismo problema del refactor de
orden de carga: la lista vivía en varios lugares y cada agregado produjo una
pérdida silenciosa.

### 2.5 Faltan alícuotas de IVA

`data/tipoiva.csv` tiene 3: 21, 10.5 y 0. **Faltan 27, 5 y 2.5**, verificado en
una instalación nueva simulada. Un comercio que venda alimentos, medicina o
artículos básicos no puede facturar.

### 2.6 Nada verifica que la instalación quedó completa

El asistente dice "Guardar y continuar" y la app sigue. La siembra ocurre en el
arranque siguiente, en un paso aparte, y si `data/` no viaja con el `.exe` el
usuario obtiene una app configurada que no puede emitir, sin ningún mensaje.
`installer/verificar_dist.py` y `tests/test_datos_maestros.py` vigilan el
**build**, pero no hay chequeo en **runtime**.

### 2.7 Todos los clientes se declaran como Consumidor Final ante ARCA — **bloqueante**

Este apareció al verificar la decisión del catálogo, y es peor que los anteriores.

`condicion_iva_receptor_id` es el campo que viaja a ARCA con cada comprobante
(`controladores/Facturas.py:567` y `Facturas.py:1176-1183`) y **es obligatorio**
desde que entró en vigor la RG 5616: el manual de ARCA dice que hasta el 6 de
abril de 2025 era opcional y que a partir de ahí se rechazan los comprobantes sin
ese dato.

El modelo lo declara con default 5 (`modelos/Tiporesp.py:19`, que es
**Consumidor Final**), y la siembra **no lo carga**:

```python
# controladores/MigracionBaseDatos.py:155-159
campos=[Tiporesp.idtiporesp, Tiporesp.nombre, Tiporesp.discrimina, Tiporesp.tipoiva,
        Tiporesp.obligacuit, Tiporesp.factura, Tiporesp.notacredito, Tiporesp.notadebito,
        Tiporesp.tipoivaepson],
```

`condicion_iva_receptor_id` no está en la lista, así que sus 4 filas quedan en el
default. Verificado en la instalación nueva simulada: las 4 filas quedaron en 5.

O sea que en una instalación recién hecha, a un Responsable Inscripto con CUIT
se le manda `condicion_iva_receptor_id = 5` (Consumidor Final), incompatible con
el tipo de documento 80. Lo único que lo corrige hoy es que alguien entre al ABM
de tipos de responsable y lo cambie a mano (`vistas/ABMTipoResponsable.py:31`).

### 2.8 Una lectura de configuración con la sección equivocada

`controladores/Facturas.py:681`:

```python
LeerIni(clave='cat_iva', key='cuit')
```

`key` es el nombre de la sección, y `'cuit'` no es una sección: son `param`,
`WSFEv1`, `WSAA`, `FACTURA`, `WSCDC` y `RESPALDO`. `LeerIni` se come la excepción y
devuelve `''`. Está en el camino del comprobante asociado de una FCE, así que
pasa medio desapercibido.

---

## 3. Decisiones tomadas

### 3.1 El CUIT emisor: una sola clave

`FACTURA.cuit` es la clave canónica. Se agrega un helper único y todos los
lectores pasan por él. `WSFEv1.cuit` se completa una sola vez, y **sólo** si hoy
está vacía o tiene un valor de relleno.

La regla del helper, para no romper ninguna instalación que hoy funciona:

| `FACTURA.cuit` | `WSFEv1.cuit` | Devuelve | Además |
|---|---|---|---|
| real | relleno o vacía | la real | completa `WSFEv1.cuit` una vez |
| relleno o vacía | real | la real | completa `FACTURA.cuit` una vez |
| iguales | | esa | — |
| **dos reales y distintas** | | la de `FACTURA.cuit` | **no sobrescribe ninguna**: avisa por log y lo muestra el chequeo de instalación |
| ninguna real | | `''` | el chequeo de instalación lo reporta como faltante |

"Real" = 11 dígitos, no todos ceros, y dígito verificador válido. Lo decide
`libs.Utiles.validar_cuit`, que ya existe.

### 3.2 Catálogo: el juego completo de ARCA

Se siembran los 10 códigos de condición de IVA del receptor y las 6 alícuotas.
Verificado contra el manual de ARCA (WS BFEV1, anexo 3.1) y el Libro IVA Digital:

| Código | Condición de IVA del receptor | Clase A | B |
|---|---|---|---|
| 1 | Responsable Inscripto | sí | |
| 4 | Sujeto Exento | sí | sí |
| 5 | Consumidor Final | | sí |
| 6 | Responsable Monotributo | | sí |
| **7** | **Sujeto No Categorizado** | | sí |
| 8 | Proveedor del Exterior | | sí |
| 9 | Cliente del Exterior | | sí |
| 10 | IVA Liberado - Ley 19.640 | sí | |
| 13 | Monotributista Social | | sí |
| 16 | Monotributo Trabajador Independiente Promovido | sí | |

**Son 10, no 8.** Las 8 del asistente eran casi el juego completo, pero le
faltaban el 7 (Sujeto No Categorizado) y el 16. Se incorporan los 10.

Alícuotas: se suman 27 %, 5 % y 2.5 % a las tres actuales (21, 10.5 y 0).

> Salvedad para verificar antes de escribir el CSV: los códigos de alícuota del
> Libro IVA Digital (0003 a 0009) **no son** los de WSFE. Antes de dar por buenos
> los códigos de 27, 5 y 2.5 conviene bajarlos con `FEParamGetTiposIva`, que el
> cliente ya expone (`pyafipws/wsfev1.py:1276`), en vez de confiar en la tabla.

### 3.3 Certificado opcional, con lista de pendientes al cerrar

El asistente no cambia. Al aceptar, se corre el chequeo de la Fase 5 y se
muestra lo que falta, con dónde se carga cada cosa.

### 3.4 Dónde vive el catálogo

Un módulo Python es la fuente única (`libs/catalogos.py`), y los CSV se validan
contra él con un test. Motivo: el CSV viaja al `.exe` junto con el código, así que
no hay ventaja operativa en dejar la lista en el archivo; y el problema de hoy
vino justamente de tener la lista en tres lugares a la vez.

---

## 4. Fases

Cada fase es un PR. Ninguna cambia comportamiento sin que haya un test que lo
diga.

**Estado al 2026-10-03: 0, 2 y 5 implementadas.** Quedan 1, 3, 4 y 6.

### Fase 0 — Que el CUIT sea el que se carga (bloqueante, va sola) — **HECHA**

- `libs/instalacion.py`: helper `cuit_emisor()` con la tabla de la sección 3.1,
  más `normalizar_cuit_emisor()` que hace el completado único.
- Se llama una vez al arrancar, después de que el asistente resolvió.
- Lectores a cambiar: `Facturas.py:576, 900, 1048`, `FE.py:92, 148`,
  `CargaFacturasProveedor.py:180`, `DiagnosticoAfip.py:72`,
  `GeneraCertificados.py:20`.
- `guardar_config_inicial` deja de ser el que escribe `WSFEv1.cuit` (queda a cargo
  del completado).
- `DiagnosticoAfip` pasa a rechazar un CUIT de relleno, no sólo uno vacío.
- **Verificación**: test que corre el asistente con un CUIT y comprueba que lo que
  se lee para emitir es ese; más los cinco casos de la tabla 3.1; más el
  simulacro de instalación nueva.

### Fase 1 — Que los datos de la empresa se puedan corregir después

- Sumar a *Configuración*: punto de venta, inicio de actividades y condición
  frente al IVA.
- `FACTURA.iva` deja de ser un texto libre y pasa a salir de `cat_iva`, con la
  etiqueta del catálogo único.
- **Verificación**: test de ida y vuelta por cada campo nuevo, en el mismo estilo
  que `tests/test_instalacion.py`.

### Fase 2 — Que cada cliente vaya a ARCA con su condición de IVA correcta — **HECHA**

Cierra el hallazgo 2.7. Va antes que el catálogo porque es lo que hace que los
comprobantes se rechacen.

- `MigracionBaseDatos` carga `condicion_iva_receptor_id` en la siembra, con el
  valor que corresponde a cada tipo de responsable.
- Para bases ya sembradas, un paso que rellene el default 5 **sólo** donde siga
  en 5 y el tipo no sea Consumidor Final: si alguien ya lo corrigió a mano, no se
  pisa.
- `data/tiporesp.csv` pasa a traer la columna.
- **Verificación**: test que siembre una base desde cero y compruebe el valor de
  las 4 filas, más el caso de la base ya sembrada.

### Fase 3 — Un solo catálogo, completo

- `libs/catalogos.py` con la lista única: códigos de condición de IVA del
  receptor, con nombre, si obliga CUIT y qué clase de comprobante admite.
- `CATEGORIAS_IVA` y `ComboTipoRespIVA` leen de ahí.
- `data/tiporesp.csv` y `data/tipoiva.csv` se completan y se validan contra el
  catálogo (los 10 códigos, las 6 alícuotas).
- Se corrige de paso `Facturas.py:681`, el `key='cuit'` del hallazgo 2.8: es una
  línea y está en el camino de la FCE.
- **Verificación**: test que recorra el catálogo y falle si alguna fila del CSV se
  quedó atrás. Es el test que evita el próximo forgetting.

### Fase 4 — Completar los maestros

- Alícuotas 27, 5 y 2.5, y los tipos de responsable que falten, según 3.2.
- **Verificación**: test que migre una base desde cero y compruebe que están las
  alícuotas y las condiciones de IVA que el catálogo declara. Ojo con la lección de
  `vogel-gestion`: un fixture armado a mano no prueba lo que producen las
  migraciones.

### Fase 5 — Un chequeo de "listo para facturar" al cerrar la instalación — **HECHA**

- Al terminar el asistente, correr un chequeo: base creada, maestros sembrados,
  CUIT emisor real, certificados del modo activo, punto de venta, y los dos CUIT
  que discrepan (de la tabla 3.1).
- Reutilizar la forma de `DiagnosticoAfip` (una lista de pasos con `ok`, `detalle`
  y `que_hacer`) pero como un chequeo **local**, sin llamar a ARCA.
- Mostrar el resultado como lista de pendientes con la acción concreta, no como un
  error.
- **Verificación**: tests de cada paso con y sin el dato.

### Fase 6 — Que las migraciones no finjan

- Elegir el migrador según la base, o decidir explícitamente que en una base nueva
  no corren migraciones (porque el schema ya sale de los modelos) y sólo se
  siembran los maestros.
- No sellar `VERSION_DB` si alguna migración falló, o al menos dejarlo asentado.
- Reducir el log de una instalación nueva a cero tracebacks.
- **Verificación**: el simulacro de instalación nueva, que hoy muestra 5 errores.

---

## 5. Bitácora de verificación

Lo que se corrió para llegar a estos hallazgos:

- Lectura del flujo: `main.py`, `libs/instalacion.py`, `vistas/PrimerArranque.py`,
  `controladores/MigracionBaseDatos.py`, `controladores/Configuracion.py`,
  `vistas/Configuracion.py`, `controladores/DiagnosticoAfip.py`,
  `modelos/Tiporesp.py`, `modelos/ModeloBase.py`.
- Estado de la base de trabajo (`sistema.db`, de desarrollo): maestros poblados.
  Se descartó como evidencia porque es una base legada migrada (`exporta=0` donde
  el CSV dice `1`).
- **Simulación de una instalación nueva de verdad** en una carpeta temporal, con
  el `sistema.ini` que escribe el asistente y una base vacía:
  `_sandbox_prueba/plan_instalacion_nueva.py`. Resultado: quedan 6 tipos de
  documento (incluido CUIT), 3 alícuotas, 4 tipos de responsable **con
  `condicion_iva_receptor_id = 5` en las cuatro**, 2 formas de pago, 16
  comprobantes, 3 localidades y el CONSUMIDOR FINAL con `tiporesp=3, formapago=1,
  percepcion=1, dni=11111111`; `VERSION_DB` queda en 7 y las 5 migraciones fallan.
  La carpeta `_sandbox_prueba/` está en `.gitignore`.
- Rastreo de los lectores de CUIT y del `Auth.Cuit` de pyafipws.
- Tabla de condiciones de IVA del receptor contra el manual de ARCA (WS BFEV1,
  anexo 3.1) y el Libro IVA Digital.

## 6. Pendientes

- **Orden sugerido**: Fase 0 → Fase 2 → Fase 5. Son las tres que hacen que una
  instalación nueva pueda emitir de verdad. La 2 va antes que la 3 porque
  mientras todos los clientes salgan como Consumidor Final, corregir el catálogo
  no sirve de nada.
- Sin definir: si los artículos de ejemplo (`Servicios`, `Productos`) se dejan en
  una instalación nueva o también pasan a ser decisión del usuario.
- Sin definir: qué pasa con las instalaciones viejas que ya tienen
  `VERSION_DB = 7` y nunca corrieron una migración en condiciones limpias.
- Sin definir: si conviene una opción de menú para volver a correr el chequeo de
  la Fase 5 una vez que el usuario cargó los certificados. Hoy el aviso sale
  en cada arranque mientras falte algo, y calla cuando ya no falta.

---

## 7. Bitácora de implementación (2026-10-03)

### Lo que entró

| Fase | Archivos | Qué hace |
|---|---|---|
| 0 | `libs/instalacion.py` | `cuit_es_real()`, `cuit_emisor()`, `normalizar_cuit_emisor()` |
| 0 | `main.py` | normaliza el CUIT en las dos ramas del arranque (nueva y vieja) |
| 0 | `Facturas.py`, `FE.py`, `Remitos.py`, `PadronAfip.py`, `CargaFacturasProveedor.py`, `GeneraCertificados.py`, `DiagnosticoAfip.py` | todos los lectores de `WSFEv1.cuit` pasan por el helper |
| 0 | 4 herramientas de `tools/` | leen el CUIT por el helper, no por la clave vieja |
| 0 | `DiagnosticoAfip.py` | rechaza un CUIT de relleno, no sólo uno vacío |
| 2 | `libs/catalogos.py` | catálogo único: 10 condiciones de receptor + la condición de cada tipo de responsable |
| 2 | `data/tiporesp.csv` | trae `condicion_iva_receptor_id` con el valor de cada fila |
| 2 | `MigracionBaseDatos.py` | siembra esa columna, y `CorregirCondicionIvaReceptor()` para bases viejas |
| 5 | `libs/listo_para_facturar.py` | el chequeo local, en 8 pasos, con su `que_hacer` |
| 5 | `Main.py` | corre el chequeo después de sembrar y avisa si falta algo |

### Tres cosas que aparecieron al implementarlo

1. **El primer grep de lectores de `WSFEv1.cuit` se había quedado corto.** Faltaban
   `Remitos.py` (tres lugares), `PadronAfip.py` y un uso en la ruta de FCE de
   `Facturas.py`. Aparecieron recién al grepear de nuevo, ya con el patrón
   completo. El conteo final dice que no queda ninguno, verificado con grep.

2. **Había una variable local llamada `cuit_emisor` en `FE.py:149`** que tapaba
   al helper del mismo nombre. Renombrada a `cuit_proveedor`. Si se hubiera
   dejado, el import se habría sombreado en silencio dentro de ese método.

3. **Un bug de configuración en *Configuración* que el plan no tenía:** `cat_iva` se
   guarda y se lee con `ComboTipoRespIVA`, que sólo tiene 3 códigos (1, 4, 6).
   `setIndex` busca por dato, así que si el `cat_iva` de una instalación era 5,
   8, 9, 10 o 13, el combo no lo encontraba, se vaciaba, y al guardar
   `cat_iva` quedaba en blanco. Queda arreglado solo cuando *Configuración*
   pase a leer del catálogo único (Fase 3), no antes.

### Verificación

- La suite pasó de 312 a **354 tests** (42 nuevos: 20 del CUIT, 5 de la
  siembra de la condición, 5 de la corrección sobre base vieja, 12 del chequeo).
- El simulacro de instalación nueva (`_sandbox_prueba/plan_instalacion_nueva.py`)
  ahora da: CUIT emisor `20123456786` (real, ya no `00000000000`) y condiciones
  de receptor `6 / 1 / 5 / 4` (Monotributo, Inscripto, Consumidor Final,
  Exento), con `VERSION_DB = 8`.

### Lo que sigue pendiente

- **Fase 1**: *Configuración* no tiene punto de venta, inicio de actividades ni
  condición frente al IVA. El asistente los pide y después no se tocan.
- **Fase 3**: que `CATEGORIAS_IVA` y `ComboTipoRespIVA` lean de
  `libs/catalogos.py`, y corregir de paso el `key='cuit'` de
  `Facturas.py:681` (el `que_hacer` de la línea 681, que devuelve `''`).
- **Fase 4**: alícuotas 27, 5 y 2.5. **Con el aviso del plan:** los códigos hay
  que bajarlos con `FEParamGetTiposIva`, no copiarlos de la tabla del Libro IVA
  Digital, que usa otra numeración.
- **Fase 6**: las 5 migraciones que fallan siempre en una base nueva, y
  `VERSION_DB` que se sella como si todo hubiera salido bien.

