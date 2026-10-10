<#
.SYNOPSIS
    Publica el instalador DEMO de Asiento en oscarvogel/vogel-releases.

.DESCRIPTION
    Es el mismo ciclo que release.ps1 (tests, build, instalador, SHA, subida),
    con las diferencias que hacen que un build de demo no pueda hacer dano:

      1. los tests corren con el arbol en estado de desarrollo;
      2. marca la identidad del build con `--app-id asiento-demo`;
      3. compila con `installer\Asiento_Demo.iss`, que tiene su propio AppId;
      4. sube `Asiento_Demo_Setup.exe` al release `latest`, con nombre propio.

    Lo que este script NO hace, a proposito:

    - **No escribe manifiesto.** Nada apunta al demo, asi que ninguna app
      puede "actualizarse" hacia el. Con `app_id = asiento-demo` fuera de la
      tabla de manifiestos, `es_build_productivo()` da False y el actualizador
      del demo queda apagado. Una maquina de demostracion no puede terminar
      bajando el instalador de PRODUCCION.
    - **No toca `Asiento_Produccion_Setup.exe`.** Es el asset que baja el
      actualizador de los clientes. Este script solo sube el suyo.

    El estado del repo se restaura en un `finally`, aunque el build o la
    subida fallen a mitad: si el arbol quedara con la identidad de un build que
    no se publico, la app en desarrollo creeria que esta atrasada.

.PARAMETER BuildVersion
    Timestamp yyyy.MM.dd.HH.mm.ss. Por defecto, la hora UTC actual.

.PARAMETER SinPublicar
    Compila y arma el instalador pero no sube nada. Para probar el build.

.PARAMETER Token
    PAT de vogel-releases. Si no se pasa, usa la sesion de `gh` que haya.

.EXAMPLE
    .\release-demo.ps1 -SinPublicar
    .\release-demo.ps1
#>
[CmdletBinding()]
param(
    [string]$BuildVersion,
    [switch]$SinPublicar,
    [string]$Token
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleasesRepo = "oscarvogel/vogel-releases"
# El app_id del build. NO es "asiento": ese esta en el manifiesto de
# produccion, y usarlo aqui encenderia el actualizador en el demo.
$AppId = "asiento-demo"
$AssetNombre = "Asiento_Demo_Setup.exe"


function Write-Paso([string]$Texto) {
    Write-Host ""
    Write-Host "==> $Texto" -ForegroundColor Cyan
}

function Write-Ok([string]$Texto) {
    Write-Host "    $Texto" -ForegroundColor Green
}

function Die([string]$Texto) {
    Write-Host ""
    Write-Host "ERROR: $Texto" -ForegroundColor Red
    exit 1
}


# ------------------------------------------------------------------ salida

if (-not $BuildVersion) {
    $BuildVersion = (Get-Date).ToUniversalTime().ToString("yyyy.MM.dd.HH.mm.ss")
}
if ($BuildVersion -notmatch '^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$') {
    Die "La version tiene que ser yyyy.MM.dd.HH.mm.ss y se recibio '$BuildVersion'."
}

Write-Host "Asiento DEMO $BuildVersion" -ForegroundColor Green
Write-Host "Destino: $ReleasesRepo (asset $AssetNombre)" -ForegroundColor DarkGray
Write-Host "Sin manifiesto: el demo no se actualiza solo." -ForegroundColor Yellow

Push-Location $RepoRoot
try {
    # ------------------------------------------------- stderr no es un fallo
    #
    # PyInstaller, gh y git escriben por stderr aunque todo vaya bien, y con
    # la salida capturada PowerShell convierte cada linea de stderr de un
    # comando nativo en un error TERMINANTE. Mismomotivo que en release.ps1.
    $ErrorActionPreference = "Continue"

    # ---------------------------------------------------- 1. tests
    #
    # PRIMERO, con el arbol en desarrollo: varios tests comprueban que el
    # build_info versionado dice app_id 'development', que es lo que
    # deshabilita el actualizador.

    Write-Paso "Corriendo los tests"
    & python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { Die "Fallaron los tests. No se publica nada." }

    # ------------------------------------------ 2. identidad del build

    Write-Paso "Marcando la identidad del build ($AppId)"
    & python tools\generar_build_info.py --version $BuildVersion --app-id $AppId
    if ($LASTEXITCODE -ne 0) { Die "No se pudo marcar la identidad del build." }
    & python tools\generar_build_info.py --verificar
    if ($LASTEXITCODE -ne 0) { Die "El build no quedo con la identidad del demo." }

    # ---------------------------------------------------- 3. build

    Write-Paso "Compilando con PyInstaller"
    $PreferenciaPrevia = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & cmd /c compila.bat
        $CodigoCompilacion = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreferenciaPrevia
    }
    if ($CodigoCompilacion -ne 0) { Die "Fallo la compilacion (codigo $CodigoCompilacion)." }
    if (-not (Test-Path "dist\main.exe")) { Die "No quedo dist\main.exe." }

    # ---------------------------------- 4. distribucion y configuracion

    Write-Paso "Verificando la distribucion"
    & python installer\verificar_dist.py
    if ($LASTEXITCODE -ne 0) { Die "La distribucion esta incompleta." }

    # Frontera de configuracion: si sistema.ini llegara a dist, el instalador
    # lo pondria en {app} y la siguiente actualizacion lo pisaria.
    if (Test-Path "dist\sistema.ini") {
        Die "dist\sistema.ini existe. El instalador pisaria la configuracion del usuario."
    }
    foreach ($prohibido in @("dist\.env", "dist\fe.ini", "dist\sistema.ini.teo")) {
        if (Test-Path $prohibido) {
            Die "$prohibido esta en la distribucion. No se publica con configuracion adentro."
        }
    }
    Write-Ok "sin configuracion ni secretos en dist"

    # -------------------------------------------------- 5. instalador

    Write-Paso "Preparando el certificado de homologacion del demo"

    # Antes de compilar nada. La herramienta valida el par entero -- que se
    # pueda leer, que no este vencido, que el CUIT sea el esperado y que la
    # clave sea la de ese certificado -- y recien ahi copia a
    # `installer\demo-certificados\`, que esta en .gitignore.
    #
    # Si algo de eso falla, el demo se publicaria abriendose pero sin poder
    # emitir, y eso no se ve hasta que el cliente autoriza un comprobante.
    & python tools\preparar_certificado_demo.py
    if ($LASTEXITCODE -ne 0) {
        Die "El certificado del demo no esta bien. No se publica nada."
    }

    Write-Paso "Armando el instalador del demo"

    $Iscc = Get-Command "iscc" -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        foreach ($candidato in @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
            if ($candidato -and (Test-Path $candidato)) { $Iscc = $candidato; break }
        }
    }
    if (-not $Iscc) {
        Die "No se encontro ISCC (Inno Setup 6). Instalalo o agrega ISCC al PATH."
    }
    Write-Ok "Inno Setup: $Iscc"

    & $Iscc "/DAppVersion=$BuildVersion" "installer\Asiento_Demo.iss"
    if ($LASTEXITCODE -ne 0) { Die "Fallo la compilacion del instalador." }

    $Temporal = Join-Path $RepoRoot "instaladores\demo\Asiento_Demo-$BuildVersion-setup.exe"
    if (-not (Test-Path $Temporal)) {
        Die "No quedo el instalador en instaladores\demo\."
    }
    $Instalador = Join-Path $RepoRoot "instaladores\$AssetNombre"
    Copy-Item -Force $Temporal $Instalador
    Write-Ok "instalador: $AssetNombre"

    # ---------------------------------------------------- 6. sha

    Write-Paso "Calculando el SHA256"
    $Sha = (Get-FileHash -Algorithm SHA256 -Path $Instalador).Hash.ToLower()
    Write-Ok $Sha

    if ($SinPublicar) {
        Write-Host ""
        Write-Host "SinPublicar: no se sube nada." -ForegroundColor Yellow
        Write-Host "Instalador: $Instalador" -ForegroundColor Green
        Write-Host "SHA256    : $Sha" -ForegroundColor Green
        return
    }

    # ------------------------------------------------------ 7. subida

    Write-Paso "Subiendo el instalador del demo"
    if ($Token) { $env:GH_TOKEN = $Token }

    $PreferenciaPrevia = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & gh auth status 2>&1 | Out-Null
        $CodigoAuth = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreferenciaPrevia
    }
    if ($CodigoAuth -ne 0) { Die "gh no esta autenticado. Pasale -Token o logueate." }

    # El asset del demo tiene nombre propio. `latest` es compartido con los
    # demas productos, y Asiento_Produccion_Setup.exe -- el que baja el
    # actualizador de los clientes -- no se toca.
    & gh release upload "latest" $Instalador --clobber --repo $ReleasesRepo
    if ($LASTEXITCODE -ne 0) { Die "No se pudo subir el instalador del demo." }
    Write-Ok "asset $AssetNombre subido al release latest"

    # ------------------------------------------ 8. verificacion final
    #
    # Se parsea el JSON en PowerShell en vez de usar `--jq` con el nombre del
    # asset adentro. PowerShell 5.1 le pasa a los nativos el argumento `--jq`
    # partido cuando el valor trae comillas dobles adentro, `gh` recibe dos
    # argumentos posicionales y contesta "accepts 1 arg(s), received 2": la
    # verificacion fallaba siempre, con el asset ya subido. Con
    # ConvertFrom-Json no hay comillas que puedan partirse.

    Write-Paso "Verificando lo publicado"
    $Json = (gh release view latest --repo $ReleasesRepo --json assets 2>$null) -join ""
    if (-not $Json) { Die "No se pudo leer el release $ReleasesRepo/latest." }

    $Publicado = ($Json | ConvertFrom-Json).assets |
                 Where-Object { $_.name -eq $AssetNombre } |
                 Select-Object -First 1
    if (-not $Publicado) { Die "No se encontro el asset $AssetNombre recien subido." }

    $Esperado = "sha256:$Sha"
    if ($Publicado.digest -ne $Esperado) {
        Die "El digest publicado dice '$($Publicado.digest)' y el local es '$Esperado'."
    }
    Write-Ok "digest verificado en GitHub: $($Publicado.digest)"
    Write-Ok "$AssetNombre en https://github.com/$ReleasesRepo/releases/download/latest/$AssetNombre"
    Write-Ok "sin manifiesto: nadie se actualiza hacia el demo"
}
finally {
    # ---------------------------------------------------- restaurar

    $ErrorActionPreference = "Stop"

    Write-Paso "Restaurando el estado de desarrollo"
    Push-Location $RepoRoot
    try {
        & python tools\generar_build_info.py --restaurar | Out-Null
        Write-Ok "libs/build_info.py y version.txt vuelven al estado de desarrollo"

        # La clave privada del demo no se queda en el arbol: se copia de ahi
        # para compilar, y se va con el resto.
        & python tools\preparar_certificado_demo.py --limpiar | Out-Null
        Write-Ok "installer\demo-certificados borrado"
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Publicado el instalador DEMO $BuildVersion" -ForegroundColor Green