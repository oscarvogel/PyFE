# Vogel Gestion Simple - MVP Comercios Generales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir `O:\pyfe` en un MVP de escritorio para comercios generales donde realizar una venta sea rapido, claro y con pocos campos obligatorios.

**Architecture:** Mantener PyQt5, Peewee y la base actual de PyFE. El MVP agrega una experiencia nueva encima del nucleo existente: tablero inicial, venta simple, cliente ocasional, busqueda rapida de articulos y emision usando la logica AFIP/PDF actual. Evitar reescritura web o SaaS en esta etapa.

**Tech Stack:** Python, PyQt5, Peewee, SQLite/MySQL segun `sistema.ini`, pyafipws, pytest para pruebas nuevas de logica pura.

---

## Contexto Verificado

Carpeta de idea: `O:\ideas_proyectos\vogel_gestion_simple_pyfe`

Repositorio base: `O:\pyfe`

Estado actual relevante:

- `O:\pyfe` es una app PyQt5 clasica con `vistas`, `controladores`, `modelos` y `libs`.
- La pantalla principal actual esta en `O:\pyfe\vistas\Main.py`.
- El menu principal y sus accesos estan en `O:\pyfe\controladores\Main.py`.
- La emision de factura electronica esta concentrada en `O:\pyfe\controladores\Facturas.py`.
- El formulario actual de factura esta en `O:\pyfe\vistas\Facturas.py`.
- Articulos estan en `O:\pyfe\modelos\Articulos.py`.
- Clientes estan en `O:\pyfe\modelos\Clientes.py`.
- Cabecera y detalle de factura estan en `O:\pyfe\modelos\Cabfact.py` y `O:\pyfe\modelos\Detfact.py`.
- Remitos/proformas existen en `O:\pyfe\modelos\Remitos.py` y `O:\pyfe\controladores\Remitos.py`.
- No hay stock real por movimientos en el codigo actual.
- No hay entidades de taller, vehiculos ni ordenes de trabajo.

Estado de cuidado antes de implementar:

- `O:\pyfe` tiene cambios sin commitear.
- Hay cambios en `compila.bat`, `controladores/ConsultaCAE.py`, `sistema.ini` y `version.txt`.
- Hay archivos nuevos bajo `certificados`, `imagenes`, `pyafipws.zip` y `sistema copy.ini`.
- No mezclar esos cambios con el MVP sin revisarlos primero.
- La venv `O:\pyfe\.venv` apunta a una ruta vieja (`C:\Users\OSCAR24\...`). Antes de ejecutar pruebas desde venv, recrearla o usar un Python valido.

---

## Principios Del MVP

1. La primera pantalla debe ofrecer una accion obvia: **Nueva venta**.
2. Una venta comun no debe exigir navegar por menus contables o fiscales.
3. El usuario debe poder vender a consumidor final sin cargar cliente previamente.
4. El usuario debe poder buscar productos por codigo, nombre o codigo de barras.
5. El total debe verse grande y actualizarse inmediatamente.
6. La emision AFIP debe reutilizar lo ya existente para reducir riesgo.
7. Stock real y taller quedan fuera del primer MVP, salvo dejar puntos de extension claros.
8. No tocar certificados ni datos productivos durante desarrollo.

---

## File Structure

### Crear

- `O:\pyfe\tests\test_venta_simple_totales.py`
  - Pruebas de calculo de renglones y totales sin PyQt.

- `O:\pyfe\tests\test_venta_simple_cliente.py`
  - Pruebas de datos minimos para consumidor final.

- `O:\pyfe\controladores\venta_simple_totales.py`
  - Logica pura para calcular subtotal, IVA, tributos y total desde renglones simples.

- `O:\pyfe\controladores\venta_simple_cliente.py`
  - Logica pura para obtener datos de cliente ocasional/consumidor final.

- `O:\pyfe\vistas\VentaSimple.py`
  - Vista PyQt5 simplificada para venta.

- `O:\pyfe\controladores\VentaSimple.py`
  - Controlador de venta simple, coordinando busqueda, calculos y emision.

- `O:\pyfe\docs\vogel_gestion_simple_mvp.md`
  - Documento corto para dejar registrado el alcance dentro del repo PyFE.

### Modificar

- `O:\pyfe\controladores\Main.py`
  - Agregar acceso principal `Nueva venta`.

- `O:\pyfe\vistas\Main.py`
  - Modernizar la pantalla principal con botones mas orientados a comercio.

- `O:\pyfe\controladores\Facturas.py`
  - Agregar un punto de entrada reutilizable desde `VentaSimpleController` sin duplicar AFIP/PDF.

- `O:\pyfe\requirements.txt`
  - Agregar `pytest` solo si no existe.

### No tocar en el MVP

- `O:\pyfe\sistema.ini`
- `O:\pyfe\certificados\`
- `O:\pyfe\pyafipws\`
- `O:\pyfe\dist\`
- `O:\pyfe\build\`
- `O:\pyfe\sistema.db` salvo que se trabaje con copia de desarrollo.

---

## Task 0: Preparar Terreno Sin Mezclar Cambios

**Files:**

- Inspect: `O:\pyfe`
- Do not modify application code in this task.

- [ ] **Step 1: Guardar evidencia del estado actual**

Run:

```powershell
cd O:\pyfe
git status --short
git diff --stat
```

Expected:

```text
Debe mostrar cambios existentes antes del MVP. No deben borrarse ni revertirse.
```

- [ ] **Step 2: Crear rama de trabajo**

Run:

```powershell
cd O:\pyfe
git switch -c vogel-gestion-simple-mvp
```

Expected:

```text
Switched to a new branch 'vogel-gestion-simple-mvp'
```

If the branch already exists:

```powershell
git switch vogel-gestion-simple-mvp
```

- [ ] **Step 3: Separar mentalmente cambios previos**

Run:

```powershell
cd O:\pyfe
git diff -- compila.bat controladores/ConsultaCAE.py version.txt
git diff -- sistema.ini
```

Expected:

```text
Confirmar que esos cambios no pertenecen al MVP de venta simple.
```

- [ ] **Step 4: Inicializar CodeGraph en PyFE si falta**

Run:

```powershell
cd O:\pyfe
codegraph init -i
```

Expected:

```text
Indice creado o actualizado correctamente.
```

- [ ] **Step 5: Commit solo si se crea metadata de CodeGraph que deba versionarse**

Run:

```powershell
cd O:\pyfe
git status --short
```

Expected:

```text
No commit si solo se genero cache local ignorada. Si hay archivos versionables de config, revisarlos antes.
```

---

## Task 1: Agregar Pruebas Base De Totales

**Files:**

- Create: `O:\pyfe\tests\test_venta_simple_totales.py`
- Create later: `O:\pyfe\controladores\venta_simple_totales.py`

- [ ] **Step 1: Crear prueba fallida para total con IVA incluido**

Create `O:\pyfe\tests\test_venta_simple_totales.py`:

```python
from decimal import Decimal

from controladores.venta_simple_totales import RenglonVenta, calcular_totales


def test_calcula_total_con_precio_final_e_iva_incluido():
    renglones = [
        RenglonVenta(
            codigo="1",
            detalle="Articulo prueba",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("121.00"),
            iva=Decimal("21"),
        )
    ]

    totales = calcular_totales(renglones, contribuyente_responsable_inscripto=True)

    assert totales.subtotal == Decimal("200.00")
    assert totales.iva == Decimal("42.00")
    assert totales.total == Decimal("242.00")
```

- [ ] **Step 2: Ejecutar prueba y confirmar que falla por modulo inexistente**

Run:

```powershell
cd O:\pyfe
python -m pytest tests\test_venta_simple_totales.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'controladores.venta_simple_totales'
```

- [ ] **Step 3: Crear implementacion minima**

Create `O:\pyfe\controladores\venta_simple_totales.py`:

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class RenglonVenta:
    codigo: str
    detalle: str
    cantidad: Decimal
    precio_unitario: Decimal
    iva: Decimal


@dataclass(frozen=True)
class TotalesVenta:
    subtotal: Decimal
    iva: Decimal
    total: Decimal


def _moneda(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_totales(renglones, contribuyente_responsable_inscripto=True):
    subtotal = Decimal("0")
    iva_total = Decimal("0")
    total = Decimal("0")

    for renglon in renglones:
        importe_final = Decimal(renglon.cantidad) * Decimal(renglon.precio_unitario)
        total += importe_final

        if contribuyente_responsable_inscripto:
            divisor = Decimal("1") + (Decimal(renglon.iva) / Decimal("100"))
            neto = importe_final / divisor
            iva_total += importe_final - neto
            subtotal += neto
        else:
            subtotal += importe_final

    return TotalesVenta(
        subtotal=_moneda(subtotal),
        iva=_moneda(iva_total),
        total=_moneda(total),
    )
```

- [ ] **Step 4: Ejecutar prueba y confirmar que pasa**

Run:

```powershell
cd O:\pyfe
python -m pytest tests\test_venta_simple_totales.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
cd O:\pyfe
git add tests\test_venta_simple_totales.py controladores\venta_simple_totales.py
git commit -m "test: add venta simple total calculations"
```

---

## Task 2: Definir Cliente Ocasional Para Venta Simple

**Files:**

- Create: `O:\pyfe\tests\test_venta_simple_cliente.py`
- Create: `O:\pyfe\controladores\venta_simple_cliente.py`

- [ ] **Step 1: Crear prueba para consumidor final**

Create `O:\pyfe\tests\test_venta_simple_cliente.py`:

```python
from controladores.venta_simple_cliente import cliente_consumidor_final


def test_cliente_consumidor_final_tiene_datos_minimos_para_afip():
    cliente = cliente_consumidor_final()

    assert cliente.nombre == "Consumidor Final"
    assert cliente.documento == ""
    assert cliente.tipo_doc_afip == 99
    assert cliente.es_consumidor_final is True
```

- [ ] **Step 2: Ejecutar prueba y confirmar que falla por modulo inexistente**

Run:

```powershell
cd O:\pyfe
python -m pytest tests\test_venta_simple_cliente.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'controladores.venta_simple_cliente'
```

- [ ] **Step 3: Crear implementacion minima**

Create `O:\pyfe\controladores\venta_simple_cliente.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ClienteVentaSimple:
    nombre: str
    documento: str
    tipo_doc_afip: int
    es_consumidor_final: bool


def cliente_consumidor_final():
    return ClienteVentaSimple(
        nombre="Consumidor Final",
        documento="",
        tipo_doc_afip=99,
        es_consumidor_final=True,
    )
```

- [ ] **Step 4: Ejecutar prueba y confirmar que pasa**

Run:

```powershell
cd O:\pyfe
python -m pytest tests\test_venta_simple_cliente.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
cd O:\pyfe
git add tests\test_venta_simple_cliente.py controladores\venta_simple_cliente.py
git commit -m "feat: add consumidor final helper for simple sales"
```

---

## Task 3: Crear Vista De Venta Simple

**Files:**

- Create: `O:\pyfe\vistas\VentaSimple.py`

- [ ] **Step 1: Crear vista PyQt con flujo de venta simple**

Create `O:\pyfe\vistas\VentaSimple.py`:

```python
# coding=utf-8
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.GroupBox import Agrupacion
from libs.Utiles import imagen
from modelos.Formaspago import ComboFormapago


class VentaSimpleView(Formulario):
    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Nueva venta")
        self.resize(980, 640)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Nueva venta")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.agrupaCliente = Agrupacion(titulo="Cliente")
        self.layoutCliente = QGridLayout()
        self.checkConsumidorFinal = QCheckBox("Consumidor final")
        self.checkConsumidorFinal.setChecked(True)
        self.textCliente = EntradaTexto(placeholderText="Buscar cliente por nombre, CUIT o DNI")
        self.textDocumento = EntradaTexto(placeholderText="CUIT/DNI")
        self.layoutCliente.addWidget(self.checkConsumidorFinal, 0, 0)
        self.layoutCliente.addWidget(Etiqueta(texto="Cliente"), 0, 1)
        self.layoutCliente.addWidget(self.textCliente, 0, 2)
        self.layoutCliente.addWidget(Etiqueta(texto="Documento"), 0, 3)
        self.layoutCliente.addWidget(self.textDocumento, 0, 4)
        self.agrupaCliente.setLayout(self.layoutCliente)
        self.layoutPpal.addWidget(self.agrupaCliente)

        self.agrupaArticulo = Agrupacion(titulo="Agregar producto")
        self.layoutArticulo = QGridLayout()
        self.textArticulo = EntradaTexto(placeholderText="Codigo, nombre o codigo de barras")
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textCantidad.setText("1")
        self.btnAgregar = Boton(texto="Agregar", imagen=imagen("new.png"), tamanio=QSize(16, 16), autodefault=False)
        self.layoutArticulo.addWidget(Etiqueta(texto="Producto"), 0, 0)
        self.layoutArticulo.addWidget(self.textArticulo, 0, 1)
        self.layoutArticulo.addWidget(Etiqueta(texto="Cantidad"), 0, 2)
        self.layoutArticulo.addWidget(self.textCantidad, 0, 3)
        self.layoutArticulo.addWidget(self.btnAgregar, 0, 4)
        self.agrupaArticulo.setLayout(self.layoutArticulo)
        self.layoutPpal.addWidget(self.agrupaArticulo)

        self.gridVenta = Grilla(tamanio=10)
        self.gridVenta.ArmaCabeceras(cabeceras=["Cant.", "Codigo", "Detalle", "Unitario", "IVA", "SubTotal"])
        self.gridVenta.enabled = True
        self.gridVenta.columnasHabilitadas = [0, 1, 2, 3, 4]
        self.layoutPpal.addWidget(self.gridVenta)

        self.layoutTotales = QHBoxLayout()
        self.cboFormaPago = ComboFormapago()
        self.textTotal = EntradaTexto(tamanio=16, enabled=False)
        self.textTotal.setText("0.00")
        self.layoutTotales.addWidget(Etiqueta(texto="Forma de pago"))
        self.layoutTotales.addWidget(self.cboFormaPago)
        self.layoutTotales.addWidget(Etiqueta(texto="Total"))
        self.layoutTotales.addWidget(self.textTotal)
        self.layoutPpal.addLayout(self.layoutTotales)

        self.layoutBotones = QHBoxLayout()
        self.btnEmitir = Boton(texto="Emitir factura", imagen=imagen("save.png"), autodefault=False)
        self.btnPresupuesto = Boton(texto="Guardar presupuesto", imagen=imagen("new.png"), autodefault=False)
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnEmitir)
        self.layoutBotones.addWidget(self.btnPresupuesto)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)
```

- [ ] **Step 2: Verificar importacion de la vista**

Run:

```powershell
cd O:\pyfe
python -c "from vistas.VentaSimple import VentaSimpleView; print(VentaSimpleView.__name__)"
```

Expected:

```text
VentaSimpleView
```

- [ ] **Step 3: Commit**

Run:

```powershell
cd O:\pyfe
git add vistas\VentaSimple.py
git commit -m "feat: add simple sale view"
```

---

## Task 4: Crear Controlador De Venta Simple

**Files:**

- Create: `O:\pyfe\controladores\VentaSimple.py`
- Modify later: `O:\pyfe\controladores\Facturas.py`

- [ ] **Step 1: Crear controlador inicial con calculo de total**

Create `O:\pyfe\controladores\VentaSimple.py`:

```python
# coding=utf-8
from decimal import Decimal

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, calcular_totales
from libs import Ventanas
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones
from modelos.Articulos import Articulo
from vistas.VentaSimple import VentaSimpleView


class VentaSimpleController(ControladorBase):
    def __init__(self):
        super(VentaSimpleController, self).__init__()
        self.view = VentaSimpleView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.cerrarformulario)
        self.view.btnAgregar.clicked.connect(self.agregar_articulo)
        self.view.btnEmitir.clicked.connect(self.emitir_factura)

    @inicializar_y_capturar_excepciones
    def agregar_articulo(self, *args, **kwargs):
        busqueda = self.view.textArticulo.text().strip()
        if not busqueda:
            Ventanas.showAlert("Venta", "Ingrese un producto")
            return

        articulo = self.buscar_articulo(busqueda)
        if not articulo:
            Ventanas.showAlert("Venta", "Producto no encontrado")
            return

        cantidad = Decimal(self.view.textCantidad.text() or "1")
        precio = Decimal(str(articulo.preciopub))
        iva = Decimal(str(articulo.tipoiva.iva))
        subtotal = cantidad * precio

        self.view.gridVenta.AgregaItem(items=[
            str(cantidad),
            str(articulo.idarticulo),
            articulo.nombre,
            str(precio),
            str(iva),
            str(subtotal),
        ])
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
        self.recalcular_total()

    def buscar_articulo(self, busqueda):
        try:
            return Articulo.get_by_id(busqueda)
        except Exception:
            pass

        try:
            return Articulo.get(Articulo.codbarra == busqueda)
        except Exception:
            pass

        return Articulo.select().where(Articulo.nombre.contains(busqueda)).first()

    def obtener_renglones(self):
        renglones = []
        for fila in range(self.view.gridVenta.rowCount()):
            renglones.append(RenglonVenta(
                codigo=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Codigo")),
                detalle=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Detalle")),
                cantidad=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Cant."))),
                precio_unitario=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Unitario"))),
                iva=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="IVA"))),
            ))
        return renglones

    def recalcular_total(self):
        responsable_inscripto = int(LeerIni(clave="cat_iva", key="WSFEv1")) == 1
        totales = calcular_totales(self.obtener_renglones(), responsable_inscripto)
        self.view.textTotal.setText(str(totales.total))

    def emitir_factura(self):
        Ventanas.showAlert("Venta", "La emision desde venta simple se conecta en la siguiente tarea")
```

- [ ] **Step 2: Verificar importacion del controlador**

Run:

```powershell
cd O:\pyfe
python -c "from controladores.VentaSimple import VentaSimpleController; print(VentaSimpleController.__name__)"
```

Expected:

```text
VentaSimpleController
```

- [ ] **Step 3: Commit**

Run:

```powershell
cd O:\pyfe
git add controladores\VentaSimple.py
git commit -m "feat: add simple sale controller"
```

---

## Task 5: Agregar Acceso Principal Nueva Venta

**Files:**

- Modify: `O:\pyfe\vistas\Main.py`
- Modify: `O:\pyfe\controladores\Main.py`

- [ ] **Step 1: Modificar vista principal para agregar boton Nueva venta**

In `O:\pyfe\vistas\Main.py`, import and create the button before `Clientes`:

```python
self.btnVentaSimple = BotonMain(texto='&Nueva venta', imagen='imagenes/if_bill_416404.png')
self.layoutBotones.addWidget(self.btnVentaSimple)
```

Expected placement:

```python
self.groupBoxBotones = Agrupacion()
self.layoutBotones = QHBoxLayout()

self.btnVentaSimple = BotonMain(texto='&Nueva venta', imagen='imagenes/if_bill_416404.png')
self.layoutBotones.addWidget(self.btnVentaSimple)

self.btnClientes = BotonMain(texto='&Clientes', imagen='imagenes/if_kuser_1400.png')
self.layoutBotones.addWidget(self.btnClientes)
```

- [ ] **Step 2: Modificar controlador principal**

In `O:\pyfe\controladores\Main.py`, add import:

```python
from controladores.VentaSimple import VentaSimpleController
```

In `conectarWidgets`, add:

```python
self.view.btnVentaSimple.clicked.connect(self.onClickBtnVentaSimple)
```

Add method:

```python
def onClickBtnVentaSimple(self):
    venta = VentaSimpleController()
    venta.exec_()
```

- [ ] **Step 3: Verificar importacion de Main**

Run:

```powershell
cd O:\pyfe
python -c "from controladores.Main import Main; print(Main.__name__)"
```

Expected:

```text
Main
```

- [ ] **Step 4: Commit**

Run:

```powershell
cd O:\pyfe
git add vistas\Main.py controladores\Main.py
git commit -m "feat: add nueva venta entry point"
```

---

## Task 6: Conectar Venta Simple Con Facturacion Existente

**Files:**

- Modify: `O:\pyfe\controladores\Facturas.py`
- Modify: `O:\pyfe\controladores\VentaSimple.py`

Decision tecnica: no duplicar la llamada AFIP. Crear un metodo de carga en `FacturaController` que permita prellenar la factura actual desde renglones simples y luego usar `GrabaFactura()`.

- [ ] **Step 1: Agregar metodo de precarga en FacturaController**

In `O:\pyfe\controladores\Facturas.py`, inside `class FacturaController`, add:

```python
def cargar_venta_simple(self, cliente_id=None, renglones=None, forma_pago_id=None):
    if cliente_id:
        self.view.validaCliente.setText(str(cliente_id))
        self.CargaDatosCliente()

    if forma_pago_id:
        self.view.cboFormaPago.setText(str(forma_pago_id))

    self.view.gridFactura.setRowCount(0)
    for renglon in renglones or []:
        self.view.gridFactura.AgregaItem(items=[
            str(renglon.cantidad),
            str(renglon.codigo),
            renglon.detalle,
            str(renglon.precio_unitario),
            str(renglon.iva),
            str(renglon.cantidad * renglon.precio_unitario),
        ])

    self.SumaTodo()
```

- [ ] **Step 2: Modificar VentaSimpleController.emitir_factura**

Replace `emitir_factura` in `O:\pyfe\controladores\VentaSimple.py`:

```python
def emitir_factura(self):
    renglones = self.obtener_renglones()
    if not renglones:
        Ventanas.showAlert("Venta", "Agregue al menos un producto")
        return

    from controladores.Facturas import FacturaController

    factura = FacturaController()
    cliente_id = None
    if not self.view.checkConsumidorFinal.isChecked():
        cliente_id = self.view.textCliente.text().strip()

    factura.cargar_venta_simple(
        cliente_id=cliente_id,
        renglones=renglones,
        forma_pago_id=self.view.cboFormaPago.text(),
    )
    factura.exec_()
```

- [ ] **Step 3: Verificar importaciones**

Run:

```powershell
cd O:\pyfe
python -c "from controladores.VentaSimple import VentaSimpleController; from controladores.Facturas import FacturaController; print('ok')"
```

Expected:

```text
ok
```

- [ ] **Step 4: Ejecutar pruebas**

Run:

```powershell
cd O:\pyfe
python -m pytest tests -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
cd O:\pyfe
git add controladores\Facturas.py controladores\VentaSimple.py
git commit -m "feat: prefill invoice from simple sale"
```

---

## Task 7: Mejorar Pantalla Principal Para Comercios

**Files:**

- Modify: `O:\pyfe\vistas\Main.py`
- Modify: `O:\pyfe\controladores\Main.py` only if labels/actions change.

Objetivo visual: que el sistema abra como una herramienta de comercio, no como un menu tecnico de factura electronica.

- [ ] **Step 1: Cambiar titulo**

In `O:\pyfe\vistas\Main.py`, replace window title:

```python
self.setWindowTitle('Vogel Gestion Simple')
```

Replace title label with:

```python
self.lblTitulo = EtiquetaTitulo(texto="Vogel Gestion Simple")
```

- [ ] **Step 2: Reordenar botones**

Order:

```text
Nueva venta
Clientes
Productos
Comprobantes
Cuentas
Reportes
Configuracion
Salir
```

For this MVP, map existing actions:

- `Nueva venta` -> `VentaSimpleController`
- `Clientes` -> existing `onClickBtnCliente`
- `Productos` -> existing `onClickBtnArticulo`
- `Comprobantes` -> existing `onClickBtnFactura`
- `Cuentas` -> existing `ConsultaCtaCteController`
- `Reportes` -> existing IVA ventas / informe ventas por grupo menu
- `Configuracion` -> existing `onClickBtnSeteo`

- [ ] **Step 3: Evitar menus tecnicos en la primera vista**

Keep AFIP tools accessible inside Configuracion or Comprobantes. Do not show AFIP as first-level commercial action unless the user asks for it.

- [ ] **Step 4: Verificar importacion**

Run:

```powershell
cd O:\pyfe
python -c "from vistas.Main import MainView; print(MainView.__name__)"
```

Expected:

```text
MainView
```

- [ ] **Step 5: Commit**

Run:

```powershell
cd O:\pyfe
git add vistas\Main.py controladores\Main.py
git commit -m "feat: simplify main dashboard for commerce"
```

---

## Task 8: Prueba Manual Del Flujo De Venta

**Files:**

- No code changes unless bugs are found.

- [ ] **Step 1: Ejecutar app en modo desarrollo**

Run:

```powershell
cd O:\pyfe
python main.py
```

Expected:

```text
La app abre la pantalla principal Vogel Gestion Simple.
```

- [ ] **Step 2: Validar flujo Nueva venta**

Manual checks:

```text
1. Click en Nueva venta.
2. Dejar Consumidor final marcado.
3. Buscar producto por codigo existente.
4. Agregar cantidad 1.
5. Confirmar que aparece renglon.
6. Confirmar que Total se actualiza.
7. Click Emitir factura.
8. Confirmar que abre formulario de factura prellenado.
```

- [ ] **Step 3: Validar que el formulario anterior sigue disponible**

Manual checks:

```text
1. Volver al menu principal.
2. Entrar a Comprobantes o Facturacion.
3. Abrir Emision de Factura.
4. Confirmar que el flujo viejo sigue funcionando.
```

- [ ] **Step 4: Registrar bugs encontrados**

Create or append `O:\pyfe\docs\vogel_gestion_simple_mvp.md`:

```markdown
# Vogel Gestion Simple MVP

## Alcance

MVP para comercios generales con foco en venta simple.

## Validacion manual

- Pantalla principal abre correctamente:
- Nueva venta abre correctamente:
- Producto se agrega por codigo:
- Total se recalcula:
- Factura se prellena:
- Flujo anterior de factura sigue disponible:

## Bugs detectados

- Ninguno registrado en esta pasada.
```

- [ ] **Step 5: Commit docs**

Run:

```powershell
cd O:\pyfe
git add docs\vogel_gestion_simple_mvp.md
git commit -m "docs: record simple sale mvp validation"
```

---

## Task 9: Pulir Venta Simple Antes De Mostrar A Cliente

**Files:**

- Modify: `O:\pyfe\vistas\VentaSimple.py`
- Modify: `O:\pyfe\controladores\VentaSimple.py`

- [ ] **Step 1: Enter agrega producto**

In `VentaSimpleController.conectarWidgets`, add:

```python
self.view.textArticulo.returnPressed.connect(self.agregar_articulo)
self.view.textCantidad.returnPressed.connect(self.agregar_articulo)
```

- [ ] **Step 2: Doble click o boton borrar renglon**

Add button in `VentaSimpleView`:

```python
self.btnBorrar = Boton(texto="Borrar renglon", imagen=imagen("delete.png"), tamanio=QSize(16, 16), autodefault=False)
self.layoutBotones.addWidget(self.btnBorrar)
```

Add controller connection:

```python
self.view.btnBorrar.clicked.connect(self.borrar_renglon)
```

Add method:

```python
def borrar_renglon(self):
    fila = self.view.gridVenta.currentRow()
    if fila >= 0:
        self.view.gridVenta.removeRow(fila)
        self.recalcular_total()
```

- [ ] **Step 3: Validar cantidad numerica positiva**

In `agregar_articulo`, replace quantity parsing:

```python
try:
    cantidad = Decimal(self.view.textCantidad.text() or "1")
except Exception:
    Ventanas.showAlert("Venta", "La cantidad debe ser numerica")
    return

if cantidad <= 0:
    Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
    return
```

- [ ] **Step 4: Ejecutar pruebas**

Run:

```powershell
cd O:\pyfe
python -m pytest tests -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
cd O:\pyfe
git add vistas\VentaSimple.py controladores\VentaSimple.py
git commit -m "feat: polish simple sale interactions"
```

---

## Task 10: Empaquetar Prueba Interna

**Files:**

- Modify only if needed: `O:\pyfe\compila.bat`
- Read: `O:\pyfe\version.txt`

- [ ] **Step 1: Revisar cambios previos de build**

Run:

```powershell
cd O:\pyfe
git diff -- compila.bat version.txt
```

Expected:

```text
Confirmar si los cambios previos de -F y version corresponden al paquete que se quiere probar.
```

- [ ] **Step 2: Compilar solo cuando el flujo manual este validado**

Run:

```powershell
cd O:\pyfe
.\compila.bat
```

Expected:

```text
dist\main o dist\main.exe generado segun compila.bat vigente.
```

- [ ] **Step 3: Probar ejecutable generado**

Run:

```powershell
cd O:\pyfe
Get-ChildItem dist -Recurse -Filter main.exe
```

Then open the executable manually from the returned path.

Manual checks:

```text
1. Abre Vogel Gestion Simple.
2. Nueva venta abre.
3. Se puede agregar producto.
4. Total se calcula.
5. Formulario de factura se prellena.
```

- [ ] **Step 4: No commitear certificados ni sistema.ini**

Run:

```powershell
cd O:\pyfe
git status --short
```

Expected:

```text
No incluir sistema.ini, certificados, bases ni dist/build salvo decision explicita.
```

---

## Fuera De Alcance Para Este MVP

- Stock real por movimientos.
- Modulo taller.
- Vehiculos por cliente.
- Ordenes de trabajo.
- SaaS web.
- Sincronizacion cloud.
- Multiempresa avanzada.
- Redisenar todo el sistema visual.

---

## Siguiente Plan Recomendado Despues Del MVP

Cuando la venta simple este validada con uso real, crear un segundo plan para **stock por movimientos**:

- `MovimientoStock`
- entrada manual
- salida por factura
- salida por remito si corresponde
- ajuste
- stock minimo
- reporte de faltantes

Ese plan debe tocar modelos y migraciones, por lo que conviene hacerlo despues de estabilizar el flujo comercial basico.

---

## Self-Review

- Spec coverage: el plan cubre comercios generales, venta simple, consumidor final, busqueda de productos, total visible, acceso principal y reutilizacion del flujo AFIP existente.
- Placeholder scan: no quedan tareas con alcance indefinido; las decisiones diferidas estan marcadas como fuera de alcance o siguiente plan.
- Type consistency: `RenglonVenta`, `TotalesVenta`, `VentaSimpleView` y `VentaSimpleController` se definen antes de usarse.
- Risk check: el plan evita modificar certificados, `sistema.ini`, pyafipws y datos productivos.
