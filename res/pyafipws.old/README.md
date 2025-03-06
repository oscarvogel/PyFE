pyafipws
========

PyAfipWs contains Python modules to operate with web services regarding AFIP (Argentina's "IRS") and other government agencies, mainly related to electronic invoicing, several taxes and traceability.

Copyright 2008 - 2022 (C) Mariano Reingart [reingart@gmail.com](mailto:reingart@gmail.com) (creator and maintainter). All rights reserved.

License: LGPLv3+, with "commercial" exception available to include it and distribute with propietary programs

General Information:
--------------------

 * Main Project Site: https://github.com/reingart/pyafipws (git repository)
 * User Manual: (http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs (Spanish)
 * Documentation: https://github.com/reingart/pyafipws/wiki (Spanish/English)
 * Commercial Support: http://www.sistemasagiles.com.ar/ (Spanish)
 * Community Site: http://www.pyafipws.com.ar/ (Spanish)
 * Public Forum: http://groups.google.com/group/pyafipws (community support, no-charge "gratis" access)

Project Structure:
------------------

 * [Python library][1] (a helper class for each webservice for easy use of their methods and attributes)
 * [PyAfipWs][7]: [OCX-like][2] Windows Component-Object-Model interface compatible with legacy programming languages (VB, VFP, Delphi, PHP, VB.NET, etc.)
 * [LibPyAfipWs][8]: [DLL/.so][3] compiled shared library (exposing python methods to C/C++/C#) 
 * [Console][4] (command line) tools using simplified input & ouput files (TXT, DBF, JSON)
 * [PyRece][5] GUI and [FacturaLibre][6] WEB apps as complete reference implementations
 * Examples for Java, .NET (C#, VB.NET), Visual Basic, Visual Fox Pro, Delphi, C, PHP. 
 * Minor code fragment samples for SAP (ABAP), PowerBuilder, Fujitsu Net Cobol, Clarion, etc.
 * Modules for [OpenERP/Odoo][27] - [Tryton][28]
 
Features implemented:
---------------------

 * Supported alternate interchange formats: TXT (fixed lenght COBOL), CSV, DBF (Clipper/xBase/Harbour), XML, JSON, etc.
 * Full automation to request authentication and invoice authorization (CAE, COE, etc.)
 * Advanced XML manipulation, caching and proxy support.
 * Customizable PDF generation and visual designer (CSV templates)
 * Email, barcodes (PIL), installation (NSIS), configuration (.INI), debugging and other misc utilities

Web services supported so far:
------------------------------

AFIP:

 * [WSAA][10]: authorization & authentication, including digital cryptographic signature
 * [WSFEv1][11]: domestic market (electronic invoice) -[English][12]-
 * [WSMTXCA][22]: domestic market (electronic invoice) -detailing articles and barcodes-
 * [WSCT][22b]: tourism (electronic invoice) -"tax free" VAT refund for tourists- 
 * [WSBFEv1][13]: tax bonus (electronic invoice)
 * [WSFEXv1][14]: foreign trade (electronic invoice) -[English][15]-
 * [WSCTG][16]: agriculture (grain traceability code)
 * [WSLPG][17]: agriculture (grain liquidation - invoice)
 * [WSLTV][17b]: agriculture (green tobacco - invoice)
 * [WSLUM][17c]: agriculture (milk - invoice)
 * [WSLSP][17d]: agriculture (cattle/livestock - invoice)
 * [WSCDC][22]: invoice verification
 * [Taxpayers' Registe][26]: database to check sellers and buyers register

ARBA:

 * [COT][20]: Provincial Operation Transport Code (aka electronic Shipping note)

ANMAT/SEDRONAR/SENASA (SNT):

 * [TrazaMed][21]: National Medical Drug Traceability Program
 * [TrazaRenpre][24]: Controlled Chemical Precursors Traceability Program
 * [TrazaFito][25]: Phytosanitary Products Traceability Program

Installation Instructions:
--------------------------

Notes:
 * Python 3.9 is recommended for new apps: https://www.python.org/downloads/
 * Python 2.7 is still supported for legacy apps but compatibility will be removed soon

You could see the `.github` directory for detailed workflows and automated commands to build the project.

## Quick-Start

These instructions are for Ubuntu/Debian. In Windows you can use PowerShell.

You can download the compressed file: https://github.com/reingart/pyafipws/archive/main.zip and unzip it.

Then install dependencies and the project itself:
```
pip download https://github.com/reingart/pyafipws/archive/main.zip
python -m zipfile -e main.zip  .
cd pyafipws-main
pip install -r requirements.txt --user
python setup.py install
```

You'll need a digital certificate (.crt) and private key (.key) to authenticate 
(see [certificate generation][29] for more information and instructions).
Provisionally, you can use author's testing certificate/key:
```
wget https://www.sistemasagiles.com.ar/soft/pyafipws/reingart.zip -O reingart.zip
python -m zipfile -e reingart.zip .
```

You should copy and configure `rece.ini` to set up paths and URLs:
```
cp conf/*.ini .
```

Then, you could execute `WSAA` script to authenticate (getting Token and Sign)
and `WSFEv1` to process an electronic invoice:
```
python -m pyafipws.wsaa
python -m pyafipws.wsfev1 --prueba
```

With the last command, you should get the Electronic Autorization Code (CAE) 
for testing purposes (sample invoice data, do not use in production!).

## Virtual environment (testing):

The following commands clone the repository, creates a virtualenv and install
the packages there (including the latest versions of the dependencies) to avoid
conflicts with other libraries:
```
git clone https://github.com/reingart/pyafipws.git
cd pyafipws
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run `python setup_win.py py2exe` to build in windows and "compile" executables.
See the GitHub Actions for specific steps and more details.

Just execute `pytest` to run automated Python tests.
For Windows, see `tests/powershell` directory for Pester tests.

## Dependency installation (development):

For SOAP webservices [PySimpleSOAP](https://github.com/pysimplesoap/pysimplesoap) is
needed (spin-off of this library, inspired by the PHP SOAP extension):

```
git clone https://github.com/pysimplesoap/pysimplesoap.git -b stable_py3k
cd pysimplesoap
python setup.py install
```

Use "stable_py3k" branch reingart (see `requirements.txt` for more information)

For PDF generation, you will need the [PyFPDF](https://github.com/reingart/pyfpdf)
(PHP's FPDF library, python port):

```
git clone https://github.com/reingart/pyfpdf.git
cd pyfpdf
python setup.py install
```

On Windows, you can see available installers released for evaluation purposes on
[Download Releases](https://github.com/reingart/pyafipws/releases)

For more information see the source code installation steps in the 
[wiki](https://github.com/reingart/pyafipws/wiki/InstalacionCodigoFuente)


 [1]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaPython
 [2]: http://www.sistemasagiles.com.ar/trac/wiki/OcxFacturaElectronica
 [3]: http://www.sistemasagiles.com.ar/trac/wiki/DllFacturaElectronica
 [4]: http://www.sistemasagiles.com.ar/trac/wiki/HerramientaFacturaElectronica
 [5]: http://www.sistemasagiles.com.ar/trac/wiki/PyRece
 [6]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaLibre
 [7]: http://www.sistemasagiles.com.ar/trac/wiki/PyAfipWs
 [8]: http://www.sistemasagiles.com.ar/trac/wiki/LibPyAfipWs
 [10]: http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs#ServicioWebdeAutenticaciónyAutorizaciónWSAA
 [11]: http://www.sistemasagiles.com.ar/trac/wiki/ProyectoWSFEv1
 [12]: https://github.com/reingart/pyafipws/wiki/WSFEv1
 [13]: http://www.sistemasagiles.com.ar/trac/wiki/BonosFiscales
 [14]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaExportacion
 [15]: https://github.com/reingart/pyafipws/wiki/WSFEX
 [16]: http://www.sistemasagiles.com.ar/trac/wiki/CodigoTrazabilidadGranos
 [17]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionPrimariaGranos
 [17b]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionTabacoVerde
 [17c]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionUnicaMensualLecheria
 [17d]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionSectorPecuario
 [20]: http://www.sistemasagiles.com.ar/trac/wiki/RemitoElectronicoCotArba
 [21]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadMedicamentos
 [22]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaMTXCAService
 [22b]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaComprobantesTurismo 
 [23]: http://www.sistemasagiles.com.ar/trac/wiki/ConstatacionComprobantes
 [24]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadPrecursoresQuimicos
 [25]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadProductosFitosanitarios
 [26]: http://www.sistemasagiles.com.ar/trac/wiki/PadronContribuyentesAFIP
 [27]: https://github.com/reingart/openerp_pyafipws
 [28]: https://github.com/tryton-ar/account_invoice_ar
 [29]: http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs#Certificados
