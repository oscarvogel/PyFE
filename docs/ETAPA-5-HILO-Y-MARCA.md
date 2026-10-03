# Etapa 5 — Emisión en segundo plano y cambio de marca

Fecha: 2026-10-03
Etapas anteriores: `docs/ETAPA-4-FLUJOS.md`, `docs/ETAPA-3-COMPONENTES.md`
Alcance: dos pedidos concretos, más lo que apareció al hacerlos.

---

## 1. La emisión ya no congela la ventana

### Qué se hacía

Emitir una factura contra ARCA tarda: hay que autenticarse, conectarse, mandar
la factura y pedir el CAE. Todo eso pasaba en el hilo de la interfaz, así que
durante esos segundos la ventana estaba muerta. Con `processEvents()` se
seguía dibujando, pero los clics no respondían y no se podía trabajar en otra
cosa.

### Por qué no se mandaba `CreaFE` tal cual a un hilo

Porque `CreaFE` mezclaba tres cosas que tienen reglas distintas:

| Qué | ¿Puede ir a otro hilo? |
|---|---|
| Llamadas de red a ARCA | Sí, es lento justamente por eso |
| Widgets (`self.view.*`) | **No**: Qt no permite tocarlos desde otro hilo |
| La base (`self.cliente.percepcion`) | **No**: peewee no es thread-safe |

Si se hubiera mandado el controlador entero al hilo, el worker habría tocado
widgets y base desde allá. Eso no es un error visible: Qt a veces lo deja pasar
y peewee a veces también, hasta que se corrompe algo en un momento que nadie
relaciona con esto.

### La solución

`CreaFE` quedó partida en tres, y lo único que cruza al hilo es un `dict` de
datos planos:

```
_datos_emision()     hilo PRINCIPAL   lee la pantalla y la base
_autorizar()         hilo de TRABAJO  solo habla con ARCA
_aplicar_resultado() hilo PRINCIPAL   escribe el resultado en los widgets
```

`GrabaFactura` toma la foto de los datos, arranca el hilo, espera, y cuando
vuelve el resultado **guarda la factura en el hilo principal** — porque
`GrabaFE` escribe en la base y peewee no es thread-safe.

Los datos se leen una sola vez, antes de arrancar el hilo, y con el botón
deshabilitado. Eso es lo que hace seguro la foto: no hay forma de que alguien
cambie el importe mientras ARCA procesa.

### Un bug que hacía todo esto inútil, en silencio

El worker se creaba con la vista como padre, como dice la documentación de Qt
para "mantenerlo vivo". El problema es que **Qt no deja mover a otro hilo un
QObject que tenga padre**:

```
QObject::moveToThread: Cannot move objects with a parent
```

Y lo importante: **no lanza excepción**. Escribe eso en la consola y sigue. El
worker se quedaba en el hilo principal, las llamadas a ARCA seguían corriendo
acá, y la ventana se seguía congelando. El código parecía enhebrado, los tests
pasaban, y la app se comportaba exactamente como antes del cambio.

Lo detectó emitir una factura de verdad y ver en qué hilo había corrido el
código. Hay un test que fija que el worker se cree sin padre.

### El caso que no se puede recuperar

Si el hilo muere sin devolver nada —se cortó la conexión justo después de
mandarla, se cerró la ventana—, **no se sabe si ARCA autorizó**. En ese caso el
código no toca la base y avisa con la duda explícita:

> Puede que ARCA la haya autorizado y el programa haya cerrado antes de recibir
> la respuesta. **NO la emita de nuevo**: entre en Comprobantes y vea si
> aparece.

Porque volver a emitir un comprobante ya autorizado da error, y anular uno
autorizado es otro trámite.

---

## 2. Salió la marca anterior

Quedaba "Servin LGSM" en lugares que no son código morto:

| Dónde | Qué pasaba |
|---|---|
| `libs/Constantes.py` | Host y usuario de SMTP fijos en el código |
| `libs/Utiles.py` | El reporte de errores iba a `fe@servinlgsm.com.ar` |
| `controladores/FPDFv1.py` | El **creador del PDF** en la metadata del archivo |
| `controladores/IVAVentas.py` | El pie del correo de ventas al cliente |
| `licencia.txt` | El contacto de soporte comercial |
| `plantillas/factura_qr.csv` | Impreso en cada factura (ya estaba en la Etapa 4) |

### El reporte de errores era lo más delicado

No era solo un texto: el reporte automático de errores de **los clientes**
seguía mandándose a una casilla que ya no es de nadie de este proyecto. O se
perdía, o llegaba a un buzón ajeno.

Ahora salen de **Parámetros del sistema** (`SERVER_SMTP`, `USUARIO_SMTP`,
`CLAVE_SMTP`, `PUERTO_SMTP`), y si no están configurados, de las constantes.

**El servidor queda vacío a propósito.** El SMTP de Ferozo es específico de
cada cuenta y no se publica por DNS: lo muestra el panel (*Email → Cuentas*)
y lo manda por correo al contratarlo. Se verificó que `0110632.ferozo.com`
**no resuelve en DNS**, y tampoco ninguna variante razonable
(`smtp.…`, `mail.…`, `.com.ar`). Con un host inventado, la app falla al
reportar un error — que es el peor momento para fallar. Vacío, el programa
anota en el log **qué parámetro falta**, con el nombre exacto, para que se
pueda ir a tocarlo.

Lo que sí quedó, de lo que se pasó:

| Parámetro | Valor | Por qué |
|---|---|---|
| `USUARIO_SMTP` | `info@vogelconsultoria.com.ar` | El dado por vos |
| `PUERTO_SMTP` | `465` | Ferozo documenta SSL implícito en 465; `PyEmail` usa `SMTP_SSL` en ese puerto |
| `SERVER_SMTP` | *(vacío)* | Hay que tomarlo del panel |
| `CLAVE_SMTP` | *(vacío)* | **Nunca en el código.** Va en la máquina donde corre |

### Un bug de pyafipws que dejaba el error inútil

`pyemail.py` deja `self.Excepcion = traceback.format_exception_only`: **la
función, sin llamar**. Si eso se pasaba al log, al log le quedaba
`<built-in function format_exception_only>` en vez del mensaje real del error
— justo lo que se necesita leer cuando algo falló. `libs/Utiles.py` lo trae a
texto antes de usarlo.

### Lo que NO se tocó, a propósito

`pyafipws/` es código de Mariano Reingart y el proyecto deriva de ahí. GPL
obliga a conservar la atribución:

- `licencia.txt` línea 3: el aviso de PyAfipWS.
- `licencia.txt` líneas 5: la autoría (Jose Oscar Vogel).
- `controladores/pyqr.py`: el copyright del código original.
- Los links a la documentación de sistemasagiles en `WSConstComp.py`.
- Las bitácoras de etapas anteriores, que son registro histórico.

Cambiar eso no sería "limpiar la marca": sería romper la licencia.

---

## 3. La emisión contra ARCA, de verdad

Con el par de certificados de homologación (`homo.crt` / `homo.key`, CUIT
20-23347203-5) y la base SQLite de prueba:

```
hilo principal        : 34376
hilo de _autorizar()  : 40852      <- distintos
CAE en pantalla       : 86400944642602
resultado             : A
```

Y consultado de vuelta a ARCA, el comprobante existe.

**Herramienta nueva:** `tools/probar_emision_hilo.py`. Emite pasando por el
QThread y además **imprime en qué hilo corrió cada parte**, que es la única
forma de demostrar que el hilo existe y no solo parece.

---

## Tests

**268 en verde.** Los nuevos sobre el hilo:

| Test | Qué fija |
|---|---|
| `test_el_worker_no_tiene_padre` | El bug que hacía la emisión enhebrada inútil |
| `test_el_worker_avisca_las_etapas_por_senal` | Las etapas cruzan por señal, no tocando el dialogo |
| `test_lo_que_va_al_hilo_son_datos_planos` | Al hilo no va el controlador |
| `test_el_neto_se_calcula_segun_la_categoria_de_iva` | El neto se calcula antes de cruzar |
| `test_cancelar_la_confirmacion_no_emite` | Cancelar no toca nada |
| `test_el_cae_rechazado_no_se_escribe_en_la_pantalla` | Un rechazo no inventa un CAE |
| `test_sin_clave_no_se_intenta_conectar` | Sin configurar, el log dice QUÉ falta |
| `test_el_reporte_no_da_la_direccion_anterior` | El reporte no vuelve a Servin |

## Verificación

- `python -m pytest tests\` → 266 en verde
- `tools/probar_emision_hilo.py` → emite en homologación y confirma el hilo
- `tools/consultar_cae.py` → el comprobante existe en ARCA
- `cmd /c compila.bat` + ejecutable → verificado en la app

---

## Pendiente

- **`requirements.txt` sigue pidiendo `fpdf==1.7.2`**, pero el código ya
  funciona con fpdf2 (ver Etapa 4). Conviene actualizar el pin, con lo que
  implica en el empaquetado.
- **Falta cargar `SERVER_SMTP` y `CLAVE_SMTP`** en Parámetros del sistema de
  cada instalación donde se quiera recibir el reporte de errores. El host sale
  del panel de Ferozo (*Email → Cuentas*).
- **La emisión a `QThread` ya no es pendiente.** Queda, si algún día se
  quiere, partir `GrabaFE` en una transacción única con rollback, que es
  asunto aparte del hilo.
- **Issue #32** sigue esperando la decisión de producto.
