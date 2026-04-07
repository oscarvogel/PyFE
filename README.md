# PyFE — Facturación Electrónica Argentina

Sistema de escritorio para la emisión y gestión de **Facturas Electrónicas** en Argentina, compatible con Responsables Inscriptos, Exentos y Monotributistas. Desarrollado en **Python 3 + PyQt5**.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/UI-PyQt5-ff69b4.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-green.svg)](LICENSE)

> ⚠️ Requiere las librerías de [PyAfipWs](https://github.com/reingart/pyafipws) (branch `py3k`) instaladas para la comunicación con los Web Services de AFIP.

---

## ✨ Funcionalidades

- **Emisión de comprobantes** — Facturas A, B, C, Notas de Crédito/Débito
- **Consulta de CAE** — Estado y validación de comprobantes autorizados
- **Padrón AFIP** — Consulta de datos de contribuyentes en tiempo real
- **Remitos** — Gestión y emisión de remitos electrónicos
- **CITI** — Generación de archivos CITI de Compras y Ventas
- **RG 3685** — Informes de compras y ventas
- **Libro de IVA** — Ventas y Compras
- **Cuenta Corriente** — Gestión de clientes y saldos
- **Recibos** — Emisión de recibos
- **FCE** — Factura de Crédito Electrónica MiPyMEs
- **Categorías Monotributo** — ABM y informe de recategorización
- **Email** — Envío de comprobantes por email a clientes
- **Importación** — Importación de datos desde AFIP
- **Respaldo** — Backup y restauración de base de datos
- **Migración** — Asistente de migración de base de datos

## 📸 Capturas de Pantalla

| Pantalla Principal | Emisión de Factura |
|:---:|:---:|
| ![Pantalla principal](imagenes/pyfe-pantalla-ppal.png) | ![Emisión](imagenes/pyfe-pantalla-emision.png) |

## 🚀 Instalación

### Requisitos previos

- **Python 3.8+**
- **MySQL** o **SQLite 3** como backend de base de datos
- [PyAfipWs](https://github.com/reingart/pyafipws) (branch `py3k`) — librerías de conexión con AFIP

### Paso a paso

```bash
# 1. Clonar el repositorio
git clone https://github.com/oscarvogel/PyFE.git
cd PyFE

# 2. (Opcional pero recomendado) Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar PyAfipWs
git clone --branch py3k https://github.com/reingart/pyafipws.git
cd pyafipws
pip install .
cd ..

# 5. Configurar
# Editar fe.ini con los datos de tu empresa, CUIT, certificados AFIP, etc.

# 6. Ejecutar
python main.py
```

### Compilar ejecutable (Windows)

```bash
python setup.py build
```

O con PyInstaller directamente:

```bash
pyinstaller --onefile --windowed --icon=imagenes/icono.ico main.py
```

## ⚙️ Configuración

El archivo principal de configuración es `fe.ini`:

| Sección | Propósito |
|---|---|
| `[param]` | Conexión a base de datos (MySQL/SQLite), modo homologación/producción |
| `[WSFEv1]` | CUIT, punto de venta, categoría IVA, URLs de AFIP |
| `[WSAA]` | Rutas de certificados y claves para autenticación |
| `[FACTURA]` | Datos de la empresa, membrete, CBU/Alias FCE |
| `[EMAIL]` | Configuración de correo para envío de facturas |

### Certificados AFIP

Los certificados se guardan en la carpeta `certificados/`:
- `certificado_homologacion.crt` — Certificado de prueba
- `certificado_*.crt` — Certificado de producción
- `clave_privada_homologacion.key` — Clave privada de homologación
- `vogel.key` (o similar) — Clave privada de producción

> 🔐 **Nunca** comitees tus claves privadas. Asegurate de que estén en `.gitignore`.

## 🗂️ Estructura del proyecto

```
PyFE/
├── main.py                 # Punto de entrada
├── fe.ini                  # Configuración principal
├── requirements.txt        # Dependencias Python
├── controladores/          # Lógica de negocio (MVC)
│   ├── Main.py             # Controlador principal
│   ├── FE.py               # Integración con Web Services AFIP
│   ├── Facturas.py         # Gestión de comprobantes
│   ├── Clientes.py         # ABM clientes
│   ...
├── modelos/                # Modelos de base de datos (Peewee ORM)
├── vistas/                 # Interfaces gráficas PyQt5
├── libs/                   # Utilidades y helpers
├── certificados/           # Certificados AFIP
├── conf/                   # Configuración adicional
├── plantillas/             # Templates de PDFs
├── imagenes/               # Recursos gráficos
├── citi/                   # Archivos CITI generados
├── remitos/                # Remitos generados
└── excel/                  # Exportaciones Excel
```

## 🛠️ Tecnologías

- **UI:** PyQt5
- **ORM:** Peewee
- **Base de datos:** MySQL / SQLite
- **PDF:** FPDFv1 + fpdf
- **Excel:** XlsxWriter
- **QR:** qrcode
- **WS AFIP:** PySimpleSOAP + PyAfipWs
- **Empaquetado:** PyInstaller

## 📄 Licencia

[MIT](LICENSE)

## 👨‍💻 Autor

**Oscar Vogel** — [github.com/oscarvogel](https://github.com/oscarvogel)

## 🤝 Contribuir

1. Forkeá el repo
2. Creá una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commiteá tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Pusheá la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrí un Pull Request
