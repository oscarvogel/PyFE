COND_VTA = {'T':'Transferencia','C':'Cheque'}

ALICUOTA_AFIP = {0:"0003", 10.5:"0004", 21:"0005", 27:"0006", 2.5:"0009"}

COMPEXPORTA = [1, 2, 3, 6, 7, 8, 11, 12, 13, 39, 81, 82, 83, 201,202,203,206,207,208,211,212,213]

CODIGO_RI = 1

COMPROBANTES_FCE = [201,202,203,206,207,208,211,212,213]

# -- Envio de correo --------------------------------------------------------
#
# Son los valores por defecto. Cada instalacion puede cambiarlos desde
# Parametros del sistema (SERVER_SMTP, USUARIO_SMTP, CLAVE_SMTP, PUERTO_SMTP),
# y esos mandan sobre estos. Antes estaban fijos en el codigo, con la direccion
# del desarrollador anterior, y el reporte automatico de errores seguia yendo a
# un servidor que ya no era de nadie de este proyecto.
#
# OJO: el host y la casilla reales hay que confirmarlos con quien corresponde.
# Lo que hay aca es el dominio, no una cuenta verificada.
#
# EL SERVIDOR QUEDA VACIO A PROPOSITO. El SMTP de Ferozo es especifico de cada
# cuenta y no se publica por DNS: lo muestra en Email > Cuentas y lo manda por
# correo al contratarlo (0110632.ferozo.com, por ejemplo, NO resuelve). Poner
# un host inventado hace que la app falle justo al reportar un error, que es
# el peor momento para fallar. Vacio, el programa dice que falta configurarlo.
#
# La clave NO va aca: va en Parametros del sistema, en la maquina donde corre.
SERVER_SMTP = ''                              # lo completa el administrador
USUARIO_SMTP = 'info@vogelconsultoria.com.ar'
CLAVE_SMTP = ''                               # nunca en el codigo
PUERTO_SMTP = 465                             # Ferozo: SSL implicito en 465

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
