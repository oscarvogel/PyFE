# Factura con marca parametrizada

La factura usa la plantilla fiscal habitual (`plantillas/factura_qr.csv`) y puede sumar una capa visual de marca por parametros de sistema.

Por defecto la marca esta desactivada para no afectar instalaciones de otros clientes.

## Parametros

Los parametros se leen desde `ParamSist`:

- `FACTURA_MARCA_ACTIVA`: `S` para activar, `N` o vacio para desactivar.
- `FACTURA_MARCA_FORMATO`: ruta absoluta o relativa a la plantilla CSV de factura. Ejemplo: `plantillas/factura_marca.csv`.
- `FACTURA_MARCA_LOGO`: ruta absoluta o relativa al logo del cliente.
- `FACTURA_MARCA_FONDO`: ruta absoluta o relativa a una imagen A4 de fondo.
- `FACTURA_MARCA_WEB`: texto corto para mostrar en el encabezado.
- `FACTURA_MARCA_LEYENDA`: texto corto para mostrar al pie.
- `FACTURA_MARCA_COLOR_PRIMARIO`: color HEX, ejemplo `#0F2A44`.
- `FACTURA_MARCA_COLOR_SECUNDARIO`: color HEX, ejemplo `#0B2035`.
- `FACTURA_MARCA_COLOR_ACENTO`: color HEX, ejemplo `#F2A900`.
- `FACTURA_MARCA_COLOR_TEXTO_SECUNDARIO`: color HEX, ejemplo `#8EA8C3`.

## Ejemplo Vogel Consultoria

Assets versionables incluidos:

- `plantillas/logo-vogel-ejemplo.png`
- `plantillas/factura-fondo-vogel-ejemplo.png`

Parametros sugeridos:

```text
FACTURA_MARCA_ACTIVA=S
FACTURA_MARCA_FORMATO=plantillas/factura_marca.csv
FACTURA_MARCA_LOGO=plantillas/logo-vogel-ejemplo.png
FACTURA_MARCA_FONDO=plantillas/factura-fondo-vogel-ejemplo.png
FACTURA_MARCA_WEB=vogelconsultoria.com.ar
FACTURA_MARCA_LEYENDA=Datos y procesos para decidir mejor.
FACTURA_MARCA_COLOR_PRIMARIO=#0F2A44
FACTURA_MARCA_COLOR_SECUNDARIO=#0B2035
FACTURA_MARCA_COLOR_ACENTO=#F2A900
FACTURA_MARCA_COLOR_TEXTO_SECUNDARIO=#8EA8C3
```
