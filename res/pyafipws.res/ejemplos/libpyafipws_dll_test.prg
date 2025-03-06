&& Ejemplo de Uso de Biblioteca Din�mica LibPyAfipWS DLL en Windows
&& para: Web Service de Autenticaci�n y Autorizacion
&&       Web Service Factura Electr�nica Mercado Interno AFIP
&&       seg�n RG2485 (sin detalle, Version 1)
&& 2013 (C) Mariano Reingart <reingart@gmail.com>
&& Licencia: GPLv3

&& NOTA: este ejemplo es solo para usos avanzados, ver:
&&       http://www.sistemasagiles.com.ar/trac/wiki/LibPyAfipWs
&&       Para Visual Basic, Visual Fox Pro y similares se recomienda la interfaz COM:
&&       http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs

&& Usar la ruta completa a la DLL (por ej. C:\Archivos ...\libpyafipws.dll)

DECLARE STRING test IN ..\LIBPYAFIPWS 	
DECLARE STRING WSAA_CreateTRA IN ..\LIBPYAFIPWS STRING @ service, LONG @ ttl 

&& Llamo a la Prueba Gen�rica
s = test()
? s
            
&& Generar un Ticket de Requerimiento de Acceso (TRA) para WSFEv1
ttl = 36000 && tiempo de vida = 10hs hasta expiraci�n
tra = WSAA_CreateTRA("wsfe", ttl)
    
? TRA
