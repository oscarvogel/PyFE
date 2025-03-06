Attribute VB_Name = "Module1"
' Ejemplo de Uso de Interface COM con Web Service Factura Electr�nica Mercado Interno AFIP
' Seg�n RG2904 Art�culo 4 Opci�n B (sin detalle, CAE tradicional)
' 2010 (C) Mariano Reingart <reingart@gmail.com>
' Licencia: GPLv3

Sub Main()
    Dim WSAA As Object, WSFEv1 As Object
    
    On Error GoTo ManejoError
    
    ' Crear objeto interface Web Service Autenticaci�n y Autorizaci�n
    Set WSAA = CreateObject("WSAA")
    
    ' Generar un Ticket de Requerimiento de Acceso (TRA) para WSFEv1
    tra = WSAA.CreateTRA("wsfe")
    Debug.Print tra
    
    ' Especificar la ubicacion de los archivos certificado y clave privada
    Path = CurDir() + "\"
    ' Certificado: certificado es el firmado por la AFIP
    ' ClavePrivada: la clave privada usada para crear el certificado
    Certificado = "..\..\reingart.crt" ' certificado de prueba
    ClavePrivada = "..\..\reingart.key" ' clave privada de prueba
    
    ' Generar el mensaje firmado (CMS)
    cms = WSAA.SignTRA(tra, Path + Certificado, Path + ClavePrivada)
    Debug.Print cms
    
    ' Llamar al web service para autenticar:
    url = "" ' "https://wsaa.afip.gov.ar/ws/services/LoginCms"
    ta = WSAA.CallWSAA(cms, url) ' Homologaci�n

    ' Imprimir el ticket de acceso, ToKen y Sign de autorizaci�n
    Debug.Print ta
    Debug.Print "Token:", WSAA.Token
    Debug.Print "Sign:", WSAA.Sign
    
    ' Una vez obtenido, se puede usar el mismo token y sign por 24 horas
    ' (este per�odo se puede cambiar)
    
    ' Crear objeto interface Web Service de Factura Electr�nica Mercado Interno
    Set WSFEv1 = CreateObject("WSFEv1")
    ' Setear tocken y sing de autorizaci�n (pasos previos)
    WSFEv1.Token = WSAA.Token
    WSFEv1.Sign = WSAA.Sign
    
    ' CUIT del emisor (debe estar registrado en la AFIP)
    WSFEv1.Cuit = "20267565393"
    
    ' Conectar al Servicio Web de Facturaci�n
    wsdl = "" ' "file:///C:/pyafipws/wsfev1_wsdl.xml"
    ok = WSFEv1.Conectar("", wsdl) ' produccion
        
    ' Prueba de tablas referenciales de par�metros

    ' recupero tabla de par�metros de moneda ("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposMonedas()
        Debug.Print x
    Next

    ' recupero tabla de tipos de comprobantes("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposCbte()
        Debug.Print x
    Next
    
    ' recupero tabla de tipos de documento ("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposDoc()
        Debug.Print x
    Next
    
    ' recupero tabla de alicuotas de iva ("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposIva()
        Debug.Print x
    Next
        
    ' recupero tabla de Tipos Opcional ("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposOpcional()
        Debug.Print x
    Next
    
    ' recupero tabla de tipos de tributos ("id: descripci�n")
    For Each x In WSFEv1.ParamGetTiposTributos()
        Debug.Print x
    Next
        
    ' recupero lista de puntos de venta habilitados
    For Each x In WSFEv1.ParamGetPtosVenta()
        Debug.Print x
    Next
    
    ' busco la cotizaci�n del dolar (ver Param Mon)
    ctz = WSFEv1.ParamGetCotizacion("DOL")
    MsgBox "Cotizaci�n D�lar: " & ctz
    
    Exit Sub
ManejoError:
    ' Si hubo error:
    Debug.Print Err.Description            ' descripci�n error afip
    Debug.Print Err.Number - vbObjectError ' codigo error afip
    Select Case MsgBox(Err.Description, vbCritical + vbRetryCancel, "Error:" & Err.Number - vbObjectError & " en " & Err.Source)
        Case vbRetry
            Debug.Print WSFEv1.Excepcion
            Debug.Print WSFEv1.Traceback
            Debug.Print WSFEv1.XmlRequest
            Debug.Print WSFEv1.XmlResponse
            Debug.Assert False
            Resume
        Case vbCancel
            Debug.Print Err.Description
    End Select
    Debug.Print WSFEv1.XmlRequest
    Debug.Assert False

End Sub
