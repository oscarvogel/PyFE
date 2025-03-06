Attribute VB_Name = "Module1"
' Ejemplo de Uso de Interface COM con Web Service Bono Fiscal Electr�nico AFIP
' 2009 (C) Mariano Reingart <reingart@gmail.com>

Sub Main()
    Dim WSAA As Object, WSBFE As Object
    
    On Error GoTo ManejoError
    
    ' Crear objeto interface Web Service Autenticaci�n y Autorizaci�n
    Set WSAA = CreateObject("WSAA")
    
    ' Generar un Ticket de Requerimiento de Acceso (TRA) para WSBFE
    tra = WSAA.CreateTRA("wsbfe")
    Debug.Print tra
    
    ' Especificar la ubicacion de los archivos certificado y clave privada
    Path = WSAA.InstallDir + "\" ' directorio predeterminado, o usar CurDir()
    ' Certificado: certificado es el firmado por la AFIP
    ' ClavePrivada: la clave privada usada para crear el certificado
    Certificado = "reingart.crt" ' certificado de prueba
    ClavePrivada = "reingart.key" ' clave privada de prueba
    
    ' Generar el mensaje firmado (CMS)
    cms = WSAA.SignTRA(tra, Path + Certificado, Path + ClavePrivada)
    Debug.Print cms
    
    ' Llamar al web service para autenticar:
    ok = WSAA.Conectar("", "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl")  ' Homologaci�n
    ta = WSAA.LoginCMS(cms)

    ' Imprimir el ticket de acceso, ToKen y Sign de autorizaci�n
    Debug.Print ta
    Debug.Print "Token:", WSAA.Token
    Debug.Print "Sign:", WSAA.Sign
    
    ' Una vez obtenido, se puede usar el mismo token y sign por 12 horas
    ' (ver reutilizaci�n de ticket de acceso en el manual)
    
    ' Crear objeto interface Web Service de Factura Electr�nica
    Set WSBFE = CreateObject("WSBFEv1")
    ' Setear tocken y sing de autorizaci�n (pasos previos)
    WSBFE.Token = WSAA.Token
    WSBFE.Sign = WSAA.Sign
    
    ' CUIT del emisor (debe estar registrado en la AFIP)
    WSBFE.Cuit = "20267565393"
    
    ' Conectar al Servicio Web de Facturaci�n
    ok = WSBFE.Conectar("", "http://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL") ' homologaci�n
    
    ' Llamo a un servicio nulo, para obtener el estado del servidor (opcional)
    WSBFE.Dummy
    Debug.Print "appserver status", WSBFE.AppServerStatus
    Debug.Print "dbserver status", WSBFE.DbServerStatus
    Debug.Print "authserver status", WSBFE.AuthServerStatus
       
    ' Establezco los valores de la factura o lote a autorizar:
    fecha = Format(Date, "yyyymmdd")
    tipo_doc = 80: nro_doc = "23111111113"
    zona = 1 ' Nacional (Ver tabla de zonas)
    tipo_cbte = 1 ' Ver tabla de tipos de comprobante
    punto_vta = 5
    ' Obtengo el �ltimo n�mero de comprobante y le agrego 1
    cbte_nro = WSBFE.GetLastCMP(tipo_cbte, punto_vta) + 1 '16
    
    ' Imprimo pedido y respuesta XML para depuraci�n
    Debug.Print WSBFE.XmlRequest
    Debug.Print WSBFE.XmlResponse
    
    fecha_cbte = fecha
    Imp_total = "121.00": imp_tot_conc = "0.00": imp_neto = "100.00"
    impto_liq = "21.00": impto_liq_rni = "0.00": imp_op_ex = "0.00"
    imp_perc = "0.00": imp_iibb = "0.00": imp_perc_mun = "0.00": imp_internos = "0.00"
    imp_moneda_id = "PES" ' Ver tabla de tipos de moneda
    Imp_moneda_ctz = "1" ' cotizaci�n de la moneda (respecto al peso argentino?)
        
    ' Creo una factura (internamente, no se llama al WebService):
    ok = WSBFE.CrearFactura(tipo_doc, nro_doc, _
            zona, tipo_cbte, punto_vta, cbte_nro, fecha_cbte, _
            Imp_total, imp_neto, impto_liq, _
            imp_tot_conc, impto_liq_rni, imp_op_ex, _
            imp_perc, imp_iibb, imp_perc_mun, imp_internos, _
            imp_moneda_id, Imp_moneda_ctz)
    
    ' Agrego un item:
    ncm = "7308.10.00" ' Ver tabla de c�digos habilitados del nomenclador comun del mercosur (NCM)
    sec = "" ' C�digo de la Secretar�a (no usado por el momento)
    ds = "prueba anafe economico" ' Descripci�n completa del art�culo (hasta 4000 caracteres)
    umed = 7 ' un, Ver tabla de unidades de medida
    qty = "2.0" ' cantidad
    precio = "20.00" ' precio neto (facturas A), precio final (facturas B)
    bonif = "5.00" ' descuentos (en positivo)
    iva_id = 5 ' 21%, ver tabla al�cuota de iva
    Imp_total = "60.50" ' importe total final del art�culo (sin descuentos, iva incluido)
    ' lo agrego a la factura (internamente, no se llama al WebService):
    ok = WSBFE.AgregarItem(ncm, sec, ds, qty, umed, precio, bonif, iva_id, Imp_total)
    
    ' agrego otro item:
    ncm = "7308.20.00" ' Ver tabla de c�digos habilitados del nomenclador comun del mercosur (NCM)
    sec = "" ' C�digo de la Secretar�a (no usado por el momento)
    ds = "Prueba" ' Descripci�n completa del art�culo (hasta 4000 caracteres)
    umed = 1 ' kg, Ver tabla de unidades de medida
    qty = "1.0" ' cantidad
    precio = "50.00" ' precio neto (facturas A), precio final (facturas B)
    bonif = "0.00" ' descuentos (en positivo)
    iva_id = 5 ' 21%, ver tabla al�cuota de iva
    Imp_total = "60.50" ' importe total final del art�culo (sin descuentos, iva incluido)
    ' lo agrego a la factura (internamente, no se llama al WebService):
    ok = WSBFE.AgregarItem(ncm, sec, ds, qty, umed, precio, bonif, iva_id, Imp_total)
    
    ' Verifico que no haya rechazo o advertencia al generar el CAE
    ' Llamo al WebService de Autorizaci�n para obtener el CAE
    'id = "99000000000100" ' n�mero propio de transacci�n
    ' obtengo el �ltimo ID y le adiciono 1
    id = CStr(CDec(WSBFE.GetLastID()) + CDec(1))
    cae = WSBFE.Authorize(id)
        
    Debug.Print "Fecha Vencimiento CAE:", WSBFE.Vencimiento
        
    If cae = "" Or WSBFE.Resultado <> "A" Then
        MsgBox "No se asign� CAE (Rechazado). Observaci�n (motivos): " & WSBFE.Obs, vbInformation + vbOKOnly
    ElseIf Trim(WSBFE.Obs) <> "" And WSBFE.Obs <> "00" Then
        MsgBox "Se asign� CAE pero con advertencias. Observaci�n (motivos): " & WSBFE.Obs & " ErrMsg: " & WSBFE.ErrMsg, vbInformation + vbOKOnly
    End If
    
    ' Imprimo pedido y respuesta XML para depuraci�n (errores de formato)
    Debug.Print WSBFE.XmlRequest
    Debug.Print WSBFE.XmlResponse
    
    MsgBox "Resultado:" & WSBFE.Resultado & " CAE: " & cae & " Reproceso: " & WSBFE.Reproceso & " Obs: " & WSBFE.Obs & " ErrMsg: " & WSBFE.ErrMsg, vbInformation + vbOKOnly
    
    ' Muestro los eventos (mantenimiento programados y otros mensajes de la AFIP)
    For Each evento In WSBFE.Eventos
        If evento <> "0: " Then
            MsgBox "Evento: " & evento, vbInformation
        End If
    Next
    
    ' Buscar la factura
    cae2 = WSBFE.GetCMP(tipo_cbte, punto_vta, cbte_nro)
    
    Debug.Print "Fecha Comprobante:", WSBFE.FechaCbte
    Debug.Print "Importe Neto:", WSBFE.ImpNeto
    Debug.Print "Impuesto Liquidado:", WSBFE.ImptoLiq
    Debug.Print "Importe Total:", WSBFE.ImpTotal
    
    If cae <> cae2 Then
        MsgBox "El CAE de la factura no concuerdan con el recuperado en la AFIP!"
    Else
        MsgBox "El CAE de la factura concuerdan con el recuperado de la AFIP"
    End If
    
    Debug.Print WSBFE.XmlRequest
    Debug.Print WSBFE.XmlResponse
    
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
    Debug.Print WSBFE.XmlRequest
    Debug.Print WSBFE.XmlResponse
    Debug.Assert False

End Sub
