Attribute VB_Name = "Module1"
' Ejemplo de Uso de Interface COM con Web Service Factura Electr�nica Mercado Interno AFIP
' Seg�n RG2904 Art�culo 4 Opci�n A (con detalle, CAE tradicional)
' 2010 (C) Mariano Reingart <reingart@gmail.com>
' Licencia: GPLv3

Sub Main()
    Dim WSAA As Object, WSMTXCA As Object
    
    On Error GoTo ManejoError
    
    ' Crear objeto interface Web Service Autenticaci�n y Autorizaci�n
    Set WSAA = CreateObject("WSAA")
    
    ' Generar un Ticket de Requerimiento de Acceso (TRA) para WSMTXCA
    tra = WSAA.CreateTRA("wsmtxca")
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
    ta = WSAA.CallWSAA(cms, "") ' Homologaci�n

    ' Imprimir el ticket de acceso, ToKen y Sign de autorizaci�n
    Debug.Print ta
    Debug.Print "Token:", WSAA.Token
    Debug.Print "Sign:", WSAA.Sign
    
    ' Una vez obtenido, se puede usar el mismo token y sign por 24 horas
    ' (este per�odo se puede cambiar)
    
    ' Crear objeto interface Web Service de Factura Electr�nica Mercado Interno
    Set WSMTXCA = CreateObject("WSMTXCA")
    ' Setear tocken y sing de autorizaci�n (pasos previos)
    WSMTXCA.Token = WSAA.Token
    WSMTXCA.Sign = WSAA.Sign
    
    ' CUIT del emisor (debe estar registrado en la AFIP)
    WSMTXCA.Cuit = "20267565393"
    
    ' Conectar al Servicio Web de Facturaci�n
    ok = WSMTXCA.Conectar("") ' homologaci�n
        
    Debug.Print WSMTXCA.Version
    Debug.Print WSMTXCA.InstallDir
    ' recupero lista de puntos de venta CAE ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarPuntosVentaCAE()
        Debug.Print x
    Next
    
    Debug.Print WSMTXCA.XmlResponse
    
    ' Prueba de tablas referenciales de par�metros

    ' recupero tabla de par�metros de moneda ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarMonedas()
        Debug.Print x
    Next

    ' recupero tabla de tipos de comprobantes("id: descripci�n")
    For Each x In WSMTXCA.ConsultarTiposComprobante()
        Debug.Print x
    Next
    
    ' recupero tabla de tipos de documento ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarTiposDocumento()
        Debug.Print x
    Next
    
    ' recupero tabla de alicuotas de iva ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarAlicuotasIVA()
        Debug.Print x
    Next
    
    ' recupero tabla de condiciones de iva ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarCondicionesIVA()
        Debug.Print x
    Next
    
    ' recupero tabla de unidades de medida ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarUnidadesMedida()
        Debug.Print x
    Next
    
    ' recupero tabla de tipos de tributos ("id: descripci�n")
    For Each x In WSMTXCA.ConsultarTiposTributo()
        Debug.Print x
    Next
        
        
    ' busco la cotizaci�n del dolar (ver Param Mon)
    ctz = WSMTXCA.ConsultarCotizacionMoneda("DOL")
    MsgBox "Cotizaci�n D�lar: " & ctz
    
    
    Exit Sub
ManejoError:
    ' Si hubo error:
    Debug.Print Err.Description            ' descripci�n error afip
    Debug.Print Err.Number - vbObjectError ' codigo error afip
    Select Case MsgBox(Err.Description, vbCritical + vbRetryCancel, "Error:" & Err.Number - vbObjectError & " en " & Err.Source)
        Case vbRetry
            Debug.Print WSMTXCA.Traceback
            Debug.Print WSMTXCA.XmlRequest
            Debug.Print WSMTXCA.XmlResponse
            Debug.Assert False
            Resume
        Case vbCancel
            Debug.Print Err.Description
    End Select
    Debug.Print WSMTXCA.XmlRequest
    Debug.Assert False

End Sub
