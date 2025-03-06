Attribute VB_Name = "Module1"
' Ejemplo de Uso de Interface COM con Web Service Factura Electr�nica Exportaci�n AFIP
' 2010 (C) Mariano Reingart <reingart@gmail.com>

Sub Main()
    Dim WSAA As Object, WSFEX As Object
    
    On Error GoTo ManejoError
    
    ' Crear objeto interface Web Service Autenticaci�n y Autorizaci�n
    Set WSAA = CreateObject("WSAA")
    
    ' Generar un Ticket de Requerimiento de Acceso (TRA) para WSFEX
    tra = WSAA.CreateTRA("wsfex")
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
    ta = WSAA.CallWSAA(cms, "https://wsaahomo.afip.gov.ar/ws/services/LoginCms") ' Homologaci�n

    ' Imprimir el ticket de acceso, ToKen y Sign de autorizaci�n
    Debug.Print ta
    Debug.Print "Token:", WSAA.Token
    Debug.Print "Sign:", WSAA.Sign
    
    ' Una vez obtenido, se puede usar el mismo token y sign por 24 horas
    ' (este per�odo se puede cambiar)
    
    ' Crear objeto interface Web Service de Factura Electr�nica de Exportaci�n
    Set WSFEX = CreateObject("WSFEX")
    ' Setear tocken y sing de autorizaci�n (pasos previos)
    WSFEX.Token = WSAA.Token
    WSFEX.Sign = WSAA.Sign
    
    ' CUIT del emisor (debe estar registrado en la AFIP)
    WSFEX.Cuit = "20267565393"
    
    ' Conectar al Servicio Web de Facturaci�n
    ok = WSFEX.Conectar("http://wswhomo.afip.gov.ar/WSFEX/service.asmx") ' homologaci�n
        
    ' Prueba de tablas referenciales de par�metros
        
    ' recupero tabla de par�metros de moneda ("id: descripci�n")
    For Each x In WSFEX.GetParamMon()
        Debug.Print x
    Next

    ' recupero tabla de tipos de comprobantes("id: descripci�n")
    For Each x In WSFEX.GetParamTipoCbte()
        Debug.Print x
    Next
    
    ' recupero tabla de tipos de exportaci�n ("id: descripci�n")
    For Each x In WSFEX.GetParamTipoExpo()
        Debug.Print x
    Next
    
    ' recupero tabla de idiomas de comprobantes ("id: descripci�n")
    For Each x In WSFEX.GetParamIdiomas()
        Debug.Print x
    Next
    
    ' recupero tabla de unidades de medida ("id: descripci�n")
    For Each x In WSFEX.GetParamUMed()
        Debug.Print x
    Next
    
    ' recupero tabla de terminos de comercio exterior ("id: descripci�n")
    For Each x In WSFEX.GetParamIncoterms()
        Debug.Print x
    Next
        
    ' recupero tabla de c�digo de pais destino ("codigo: descripci�n")
    For Each x In WSFEX.GetParamDstPais()
        Debug.Print x
    Next
    
    ' recupero tabla de cuit de pais destino ("cuit: descripci�n")
    For Each x In WSFEX.GetParamDstCUIT()
        Debug.Print x
    Next
        
    ' busco la cotizaci�n del dolar (ver Param Mon)
    ctz = WSFEX.GetParamCtz("DOL")
    MsgBox "Cotizaci�n D�lar: " & ctz
    
    Exit Sub
ManejoError:
    ' Si hubo error:
    Debug.Print Err.Description            ' descripci�n error afip
    Debug.Print Err.Number - vbObjectError ' codigo error afip
    Select Case MsgBox(Err.Description, vbCritical + vbRetryCancel, "Error:" & Err.Number - vbObjectError & " en " & Err.Source)
        Case vbRetry
            Debug.Assert False
            Resume
        Case vbCancel
            Debug.Print Err.Description
    End Select
    Debug.Print WSFEX.XmlRequest
    Debug.Assert False

End Sub
