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
    ta = WSAA.CallWSAA(cms, "https://wsaahomo.afip.gov.ar/ws/services/LoginCms") ' Homologaci�n (cambiar para producci�n)

    ' Imprimir el ticket de acceso, ToKen y Sign de autorizaci�n
    Debug.Print ta
    Debug.Print "Token:", WSAA.Token
    Debug.Print "Sign:", WSAA.Sign
    
    ' Una vez obtenido, se puede usar el mismo token y sign por 24 horas
    ' (este per�odo se puede cambiar)
    
    ' Crear objeto interface Web Service de Factura Electr�nica de Mercado Interno
    Set WSMTXCA = CreateObject("WSMTXCA")
    Debug.Print WSMTXCA.Version
    Debug.Print WSMTXCA.InstallDir
    
    ' Setear tocken y sing de autorizaci�n (pasos previos)
    WSMTXCA.Token = WSAA.Token
    WSMTXCA.Sign = WSAA.Sign
    
    ' CUIT del emisor (debe estar registrado en la AFIP)
    WSMTXCA.Cuit = "20267565393"
    
    ' Conectar al Servicio Web de Facturaci�n
    WSDL = "" ' "https://serviciosjava.afip.gov.ar/wsmtxca/services/MTXCAService?wsdl"
    proxy = "" ''"localhost:8000"
    ok = WSMTXCA.Conectar("", WSDL, proxy, "")   ' producci�n
    Debug.Print WSMTXCA.Version
    
    ' Llamo a un servicio nulo, para obtener el estado del servidor (opcional)
    WSMTXCA.Dummy
    Debug.Print "appserver status", WSMTXCA.AppServerStatus
    Debug.Print "dbserver status", WSMTXCA.DbServerStatus
    Debug.Print "authserver status", WSMTXCA.AuthServerStatus
       
    ' PASO 1: Solicito CAE Anticipado para el per�odo
    ' NOTA: solicitar por �nica vez para un determinado per�odo
    ' consultar si se ha solicitado previamente
    
    Periodo = "201104"  ' A�o y mes
    Orden = "2"         ' Segunda Quincena
    
    ' consulto CAEA ya solicitado
    CAEA = WSMTXCA.ConsultarCAEA(Periodo, Orden)
    If CAEA = "" Then
        ' solicito nuevo CAEA
        CAEA = WSMTXCA.SolicitarCAEA(Periodo, Orden)
    End If
    
    Debug.Print "Periodo:", WSMTXCA.Periodo
    Debug.Print "Orden:", WSMTXCA.Orden
    Debug.Print "Fecha Vigencia Desde:", WSMTXCA.FchVigDesde
    Debug.Print "Fecha Vigencia Hasta:", WSMTXCA.FchVigHasta
    Debug.Print "Fecha Tope Informe:", WSMTXCA.FchTopeInf
    Debug.Print "Fecha Proceso:", WSMTXCA.FchProceso

    MsgBox "Periodo: " & Periodo & " Orden " & Orden & vbCrLf & "CAEA: " & CAEA & vbCrLf & _
            "Obs:" & WSMTXCA.Obs & vbCrLf & _
            "Errores:" & WSMTXCA.ErrMsg
    
    ' Si no tengo CAEA, termino
    If CAEA = "" Then End
    
    ' Establezco los valores de la factura a autorizar:
    tipo_cbte = 1
    punto_vta = 4000
    cbte_nro = WSMTXCA.CompUltimoAutorizado(tipo_cbte, punto_vta)
    fecha = Format(Date, "yyyy-mm-dd")
    vencimiento = Format(Date + 5, "yyyy-mm-dd")
    concepto = 3
    tipo_doc = 80: nro_doc = "30000000007"
    cbte_nro = CLng(cbte_nro) + 1
    cbt_desde = cbte_nro: cbt_hasta = cbte_nro
    imp_total = "122.00": imp_tot_conc = "0.00": imp_neto = "100.00"
    imp_trib = "1.00": imp_op_ex = "0.00": imp_subtotal = "100.00"
    fecha_cbte = fecha: fecha_venc_pago = fecha
    ' Fechas del per�odo del servicio facturado (solo si concepto = 1?)
    fecha_serv_desde = fecha: fecha_serv_hasta = fecha
    moneda_id = "PES": moneda_ctz = "1.000"
    Obs = "Observaciones Comerciales, libre"


    ok = WSMTXCA.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta, _
        cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto, _
        imp_subtotal, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago, _
        fecha_serv_desde, fecha_serv_hasta, _
        moneda_id, moneda_ctz, Obs, CAEA, vencimiento)
    
    ' Agrego los comprobantes asociados:
    If False Then ' solo si es nc o nd
        tipo = 19
        pto_vta = 2
        nro = 1234
        ok = WSMTXCA.AgregarCmpAsoc(tipo, pto_vta, nro)
    End If
    
    ' Agrego impuestos varios
    id = 99
    Desc = "Impuesto Municipal Matanza'"
    base_imp = "100.00"
    alic = "1.00"
    importe = "1.00"
    ok = WSMTXCA.AgregarTributo(id, Desc, base_imp, alic, importe)

    ' Agrego subtotales de IVA
    id = 5 ' 21%
    base_im = "100.00"
    importe = "21.00"
    ok = WSMTXCA.AgregarIva(id, base_imp, importe)
    
    u_mtx = 123456
    cod_mtx = "1234567890"
    codigo = "P0001"
    ds = "Descripcion del producto P0001"
    qty = "1.0000"
    umed = 7
    precio = "100.00"
    bonif = "0.00"
    cod_iva = 5
    imp_iva = "21.00"
    imp_subtotal = "121.00"
    ok = WSMTXCA.AgregarItem(u_mtx, cod_mtx, codigo, ds, qty, _
                umed, precio, bonif, cod_iva, imp_iva, imp_subtotal)
    ok = WSMTXCA.AgregarItem(u_mtx, cod_mtx, codigo, ds, qty, _
                umed, precio, bonif, cod_iva, imp_iva, imp_subtotal)
    ok = WSMTXCA.AgregarItem(u_mtx, cod_mtx, "DESC", "Descuento", 0, _
                "99", 0#, 0, cod_iva, "-21.00", "-121.00")

    ' Solicito CAE:
    cae = WSMTXCA.InformarComprobanteCAEA()
    
    Debug.Print "Resultado", WSMTXCA.Resultado
    Debug.Print "CAEA", WSMTXCA.CAEA
    Debug.Print "Vencimiento CAEA", WSMTXCA.vencimiento
    Debug.Print WSMTXCA.ErrMsg
    
    ' verifico que no haya errores
    For Each er In WSMTXCA.Errores
        MsgBox er, vbInformation, "Error:"
    Next
    
    ' Verifico que no haya rechazo o advertencia al generar el CAE
    If cae = "" Or WSMTXCA.Resultado <> "A" Then
        MsgBox "No se asign� CAE (Rechazado). Observaci�n (motivos): " & WSMTXCA.Obs, vbInformation + vbOKOnly
    ElseIf WSMTXCA.Obs <> "" And WSMTXCA.Obs <> "00" Then
        MsgBox "Se asign� CAE pero con advertencias. Observaci�n (motivos): " & WSMTXCA.Obs, vbInformation + vbOKOnly
    End If
    
    Debug.Print "Numero de comprobante:", WSMTXCA.CbteNro
    
    ' Imprimo pedido y respuesta XML para depuraci�n (errores de formato)
    Debug.Print WSMTXCA.XmlRequest
    Debug.Print WSMTXCA.XmlResponse
    
    MsgBox "Resultado:" & WSMTXCA.Resultado & " CAE: " & cae & " Venc: " & WSMTXCA.vencimiento & " Obs: " & WSMTXCA.Obs, vbInformation + vbOKOnly
    
    ' Muestro los eventos (mantenimiento programados y otros mensajes de la AFIP)
    If WSMTXCA.evento <> "" Then
        MsgBox "Evento: " & WSMTXCA.evento, vbInformation
    End If
    
    ' Buscar la factura
    cae2 = WSMTXCA.ConsultarComprobante(tipo_cbte, punto_vta, cbte_nro)
    
    Debug.Print "Fecha Comprobante:", WSMTXCA.FechaCbte
    Debug.Print "Fecha Vencimiento CAE", WSMTXCA.vencimiento
    Debug.Print "Importe Total:", WSMTXCA.ImpTotal
    
    If cae <> cae2 Then
        MsgBox "El CAE de la factura no concuerdan con el recuperado en la AFIP!: " & cae & " vs " & cae2
    Else
        MsgBox "El CAE de la factura concuerdan con el recuperado de la AFIP"
    End If
        
    Exit Sub
ManejoError:
    ' Si hubo error:
    Debug.Print WSMTXCA.Excepcion
    Debug.Print Err.Description            ' descripci�n error afip
    Debug.Print Err.Number - vbObjectError ' codigo error afip
    Select Case MsgBox(Err.Description, vbCritical + vbRetryCancel, "Error:" & Err.Number - vbObjectError & " en " & Err.Source)
        Case vbRetry
            Debug.Print WSMTXCA.ErrCode
            Debug.Print WSMTXCA.ErrMsg
            Debug.Print WSMTXCA.Traceback
            Debug.Print WSMTXCA.XmlRequest
            Debug.Print WSMTXCA.XmlResponse
            Debug.Assert False
            Resume
        Case vbCancel
            Debug.Print Err.Description
    End Select
    Debug.Print WSMTXCA.XmlRequest
    Debug.Print WSMTXCA.XmlResponse
    Debug.Assert False

End Sub
