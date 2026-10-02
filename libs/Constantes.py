COND_VTA = {'T':'Transferencia','C':'Cheque'}

ALICUOTA_AFIP = {0:"0003", 10.5:"0004", 21:"0005", 27:"0006", 2.5:"0009"}

COMPEXPORTA = [1, 2, 3, 6, 7, 8, 11, 12, 13, 39, 81, 82, 83, 201,202,203,206,207,208,211,212,213]

CODIGO_RI = 1

COMPROBANTES_FCE = [201,202,203,206,207,208,211,212,213]

SERVER_SMTP = 'mail.servinlgsm.com.ar'
USUARIO_SMTP = 'fe@servinlgsm.com.ar'
CLAVE_SMTP = ''
PUERTO_SMTP = ''

# -- Identidad del producto ------------------------------------------------
#
# El producto se vende a estudios contables y a pequenas empresas, que son
# clientes distintos entre si. Por eso el nombre NO lleva la marca de nadie:
# lo que se ve en el titulo de las ventanas y en los avisos es configurable
# por instalacion (param.nombre_sistema), y estos son solo los valores por
# defecto de una instalacion nueva.
NOMBRE_PRODUCTO = "Asiento"
EMPRESA_DESARROLLO = "Vogel Consultoria"
SITIO_EMPRESA = "vogelconsultoria.com.ar"

# 10 digitos: 3744 es el prefijo de La Pampa, asi que 3744-667526 es un fijo.
# Se escribe en formato internacional para que un cliente de otra provincia
# pueda llamarlo: los fijos llevan +54 + area + numero, SIN el 9 (ese 9 es
# solo para los celulares).
WHATSAPP_EMPRESA = "+54 3744 66-7526"

# Pie de la pagina: credito de quien hizo el programa.
#
# Va en el pie y NO en el bloque del emisor. La diferencia importa: el bloque
# del emisor identifica a quien factura, y ese es el cliente. Esta linea es un
# credito de quien hizo el programa, que es practica comun en el software de
# gestion, y por eso lleva las palabras "Desarrollo de".
CREDITO_SOFTWARE = "Desarrollo de {empresa} · {sitio} · WhatsApp {whatsapp}".format(
    empresa=EMPRESA_DESARROLLO,
    sitio=SITIO_EMPRESA,
    whatsapp=WHATSAPP_EMPRESA,
)
