<#
.SYNOPSIS
    Publica una version de Asiento en oscarvogel/vogel-releases.

.DESCRIPTION
    Hace el ciclo entero de release en local, en el mismo orden que el
    release.ps1 de femag:

      1. marca la identidad del build (app_id + timestamp UTC);
      2. corre los tests;
      3. compila con compila.bat (PyInstaller);
      4. verifica la distribucion y que no haya configuracion adentro;
      5. arma el instalador de Inno Setup;
      6. calcula el SHA256;
      7. sube el asset con nombre estable al release `latest`;
      8. escribe apps/asiento/latest.json;
      9. AGREGA la entrada a apps/asiento/changelog.json, sin truncarlo;
     10. deja libs/build_info.py y version.txt como estaban.

    El paso 10 va en un try/finally: si el build o la subida fallan a mitad,
    el repo no puede quedar con la identidad de un build que no se publico.
    Si eso pasara, el arbol en desarrollo creeria que la app esta atrasada y
    avisaria de actualizaciones fantasma.

    OJO con el orden de 7 y 8: el manifiesto se sube ANTES que el asset. Al
    reves, si la subida del .exe fallara, el manifiesto quedaria
    describiendo una version cuyo instalador todavia no se puede bajar.

.PARAMETER BuildVersion
    Timestamp yyyy.MM.dd.HH.mm.ss. Por defecto, la hora UTC actual.

.PARAMETER Notas
    Novedades de la version, separadas por ';'. Si no se pasan, se arma con
    los commits desde la ultima version publicada.

.PARAMETER SinPublicar
    Compila y arma el instalador pero no sube nada. Para probar el build.

.PARAMETER Token
    PAT de vogel-releases. Si no se pasa, usa la sesion de `gh` que haya.

.EXAMPLE
    .\release.ps1 -SinPublicar
    .\release.ps1 -Notas "Manejo de stock; Pantalla de emision"
#>
[CmdletBinding()]
param(
    [string]$BuildVersion,
    [string]$Notas,
    [switch]$SinPublicar,
    [string]$Token
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleasesRepo = "oscarvogel/vogel-releases"
$AppId = "asiento"
$AssetNombre = "Asiento_Produccion_Setup.exe"
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

# Campos que el schema de vogel-releases exige. El schema declara
# additionalProperties:false, asi que un campo de mas hace fallar TODOS los
# manifiestos del repo en el proximo que valide alguien. De ahi que
# 'channel' (que femag y fgpy usan) NO se escriba aca: el schema de este repo
# no lo admite.
$CamposManifiesto = @("schema_version", "app_id", "version", "published_at",
                       "mandatory", "download_url", "sha256", "notes")


# ------------------------------------------------------------------ salida

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


# ------------------------------------------------------------------ notas

function Get-ListaNotas([string]$NotasPedidas, [string]$Version) {
    <#
        Devuelve las novedades como lista de frases.

        Sin -Notas se arma con los commits desde la ultima version publicada.
        Prefiere notas escritas a mano: un listado de commits dice "arreglado
        un bug" y eso no le sirve a nadie. El que escribe la nota sabe que
        cambio le importa al usuario.
    #>
    if ($NotasPedidas) {
        $limpias = @($NotasPedidas -split ";" |
                     ForEach-Object { $_.Trim() } | Where-Object { $_ })
        if ($limpias.Count -gt 0) { return $limpias }
    }

    Push-Location $RepoRoot
    try {
        $Tags = @(git tag --list "v20*" 2>$null | Sort-Object)
        $Ultima = $Tags | Select-Object -Last 1
        $Rango = if ($Ultima) { "$Ultima..HEAD" } else { "HEAD" }
        $Commits = @(git log --no-merges --pretty=format:"%s" $Rango 2>$null |
                     Where-Object { $_ -and $_ -notmatch '^ci\(' } |
                     Select-Object -First 20)
    }
    finally {
        Pop-Location
    }

    if ($Commits.Count -gt 0) { return @($Commits) }
    return @("Correcciones y mejoras de la version $Version.")
}


# -------------------------------------------------------------- changelog

function Add-ChangelogEntry([string]$Ruta, [string]$AppIdChangelog,
                            [string]$Version, [string]$Publicado,
                            [string[]]$Lista) {
    <#
        Agrega una entrada al historial, NUNCA reemplaza el archivo.

        El historial es acumulable a proposito: si el usuario salta de la
        10:00 a la 13:00, tiene que ver las novedades de las 11:00, 12:00 y
        13:00 juntas. Un changelog que se sobrescribe en cada publicacion
        deja viendo siempre solo la ultima.
    #>
    $Changelog = [ordered]@{
        schema_version = 1
        app_id         = $AppIdChangelog
        versions       = @()
    }

    if (Test-Path $Ruta) {
        $Existente = Get-Content -Raw -Encoding UTF8 $Ruta | ConvertFrom-Json
        if ($Existente.app_id -ne $AppIdChangelog) {
            Die "El changelog de $Ruta es de otro producto ($($Existente.app_id))."
        }
        $Changelog.versions = @($Existente.versions)
    }

    if ($Changelog.versions | Where-Object { $_.version -eq $Version }) {
        Die "El changelog ya tiene la version $Version. Cada version se publica una vez."
    }

    $Changelog.versions = @($Changelog.versions) + @([ordered]@{
        version      = $Version
        published_at = $Publicado
        notes        = @($Lista)
    })

    # De mas viejo a mas nuevo. El formato del timestamp ordena bien como
    # texto: todos los componentes tienen ancho fijo.
    $Changelog.versions = @($Changelog.versions | Sort-Object { $_.version })

    [System.IO.File]::WriteAllText(
        $Ruta, (ConvertTo-Json $Changelog -Depth 6) + "`n", $Utf8NoBom)
}


# -------------------------------------------------------------- manifiesto

function Test-ManifestValido([string]$Ruta, [string]$AppIdEsperado,
                             [string]$VersionEsperada, [string]$ShaEsperado) {
    <#
        Valida el manifiesto LOCAL contra el schema del repo.

        Ojo: `tools/validar_manifiesto_vogel.py` NO sirve para aca. Lee los
        manifiestos con `gh api` desde GitHub, o sea que valida lo que ya
        esta publicado y no el archivo que este script acaba de escribir.
        Daria verde con un manifiesto roto.
    #>
    $Crudo = [System.IO.File]::ReadAllBytes($Ruta)
    if ($Crudo.Length -ge 3 -and $Crudo[0] -eq 0xEF -and $Crudo[1] -eq 0xBB) {
        Die "El manifiesto tiene BOM. El schema pide UTF-8 sin BOM."
    }

    $Texto = [System.Text.Encoding]::UTF8.GetString($Crudo)
    $Datos = $Texto | ConvertFrom-Json

    $Claves = @($Datos.PSObject.Properties.Name)
    foreach ($campo in $CamposManifiesto) {
        if ($Claves -notcontains $campo) { Die "Al manifiesto le falta '$campo'." }
    }
    foreach ($clave in $Claves) {
        if ($CamposManifiesto -notcontains $clave) {
            Die "El manifiesto tiene '$clave', que el schema prohibe (additionalProperties:false)."
        }
    }

    if ($Datos.schema_version -ne 1) { Die "schema_version tiene que ser 1." }
    if ($Datos.app_id -ne $AppIdEsperado) { Die "app_id tiene que ser '$AppIdEsperado'." }
    if ($Datos.version -ne $VersionEsperada) { Die "version no coincide con la del build." }
    if ($Datos.download_url -notmatch '^https://github\.com/oscarvogel/vogel-releases/releases/download/') {
        Die "download_url tiene que apuntar al release de vogel-releases por HTTPS."
    }
    if ($Datos.sha256 -notmatch '^[0-9a-fA-F]{64}$') { Die "sha256 no es un hash de 64 hex." }
    if ($Datos.sha256.ToLower() -ne $ShaEsperado) { Die "sha256 no coincide con el del instalador." }
    if ($null -eq $Datos.published_at) { Die "published_at falta." }

    Write-Ok "manifiesto valido contra el schema"
}


# ================================================================== CICLO

if (-not $BuildVersion) {
    $BuildVersion = (Get-Date).ToUniversalTime().ToString("yyyy.MM.dd.HH.mm.ss")
}
if ($BuildVersion -notmatch '^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$') {
    Die "La version tiene que ser yyyy.MM.dd.HH.mm.ss y se recibio '$BuildVersion'."
}
$PublicadoEn = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host "Asiento $BuildVersion" -ForegroundColor Green
Write-Host "Destino: $ReleasesRepo" -ForegroundColor DarkGray
$Sha = $null

Push-Location $RepoRoot
try {
    # ---------------------------------------------------- 2. tests

    # Los tests van PRIMERO, con el arbol en estado de desarrollo.

    # No es un detalle de orden: varios tests comprueban que el archivo
    # versionado de build_info dice app_id 'development' (que es lo que
    # deshabilita el actualizador). Si la identidad se marcara antes, esos
    # tests correrian con un build de produccion y fallarian, y el release
    # no publicaria nunca. Ademas, si un test falla, todavia no se toco
    # ningun archivo del repo.

    Write-Paso "Corriendo los tests"
    & python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { Die "Fallaron los tests. No se publica nada." }

    # ------------------------------------------ 1. identidad del build

    Write-Paso "Marcando la identidad del build"
    & python tools\generar_build_info.py --version $BuildVersion --app-id $AppId
    if ($LASTEXITCODE -ne 0) { Die "No se pudo marcar la identidad del build." }

    # ---------------------------------------------------- 3. build

    Write-Paso "Compilando con PyInstaller"
    & cmd /c compila.bat
    if ($LASTEXITCODE -ne 0) { Die "Fallo la compilacion." }
    if (-not (Test-Path "dist\main.exe")) { Die "No quedo dist\main.exe." }

    # ---------------------------------- 4. distribucion y configuracion

    Write-Paso "Verificando la distribucion"
    & python installer\verificar_dist.py
    if ($LASTEXITCODE -ne 0) { Die "La distribucion esta incompleta." }

    # Frontera de configuracion. sistema.ini lo crea la app con los datos del
    # asistente de primer arranque y le pertenece al usuario. Si llegara a
    # dist, el instalador lo pondria en {app} y en la siguiente actualizacion
    # InnoSetup lo trataria como un archivo suyo y lo pisaria. compila.bat
    # hoy no lo copia; este chequeo esta para que siga sin copiarlo sin que
    # nadie se avise.
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

    Write-Paso "Armando el instalador"

    $Iscc = Get-Command "iscc" -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        # La instalacion por usuario de Inno Setup 6 va a LOCALAPPDATA y no
        # a Program Files, y es la que queda cuando se instala "para este
        # usuario". Sin esta ruta, el release falla aca con "no se encontro
        # ISCC" aunque el compilador este instalado.
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

    & $Iscc "/DAppVersion=$BuildVersion" "installer\PyFE.iss"
    if ($LASTEXITCODE -ne 0) { Die "Fallo la compilacion del instalador." }

    $InstaladorTemporal = Join-Path $RepoRoot "instaladores\Asiento-$BuildVersion-setup.exe"
    if (-not (Test-Path $InstaladorTemporal)) {
        Die "No quedo el instalador en instaladores\."
    }
    $Instalador = Join-Path $RepoRoot "instaladores\$AssetNombre"
    Copy-Item -Force $InstaladorTemporal $Instalador
    Write-Ok "instalador: $AssetNombre"

    # ------------------------------------------------------ 6. sha

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

    # ------------------------------------------- 7. manifiesto y changelog

    Write-Paso "Preparando los manifiestos"

    if ($Token) { $env:GH_TOKEN = $Token }
    & gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "gh no esta autenticado. Pasale -Token o logueate." }

    $ListaNotas = Get-ListaNotas -NotasPedidas $Notas -Version $BuildVersion
    Write-Ok ("notas: " + ($ListaNotas -join " | "))

    $Manifiesto = [ordered]@{
        schema_version = 1
        app_id         = $AppId
        version        = $BuildVersion
        published_at   = $PublicadoEn
        mandatory      = $false
        download_url   = "https://github.com/$ReleasesRepo/releases/download/latest/$AssetNombre"
        sha256         = $Sha
        notes          = ($ListaNotas -join " ")
    }

    $Clon = Join-Path ([System.IO.Path]::GetTempPath()) "vogel-releases-release"
    if (Test-Path $Clon) { Remove-Item -Recurse -Force $Clon }
    & git clone --quiet "https://github.com/$ReleasesRepo.git" $Clon
    if ($LASTEXITCODE -ne 0) { Die "No se pudo clonar $ReleasesRepo." }

    $AppDir = Join-Path $Clon "apps\$AppId"
    if (-not (Test-Path $AppDir)) {
        New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
    }

    $RutaManifiesto = Join-Path $AppDir "latest.json"
    [System.IO.File]::WriteAllText(
        $RutaManifiesto, (ConvertTo-Json $Manifiesto -Depth 5) + "`n", $Utf8NoBom)

    Add-ChangelogEntry -Ruta (Join-Path $AppDir "changelog.json") `
                       -AppIdChangelog $AppId -Version $BuildVersion `
                       -Publicado $PublicadoEn -Lista $ListaNotas

    Test-ManifestValido -Ruta $RutaManifiesto -AppIdEsperado $AppId `
                        -VersionEsperada $BuildVersion -ShaEsperado $Sha

    Push-Location $Clon
    try {
        & git add "apps/$AppId"
        & git commit --quiet -m "release($AppId): $BuildVersion"
        & git push --quiet origin HEAD:main
        if ($LASTEXITCODE -ne 0) { Die "No se pudieron subir los manifiestos." }
    }
    finally {
        Pop-Location
    }
    Write-Ok "manifiesto y changelog publicados"

    # ------------------------------------------------------- 8. asset

    Write-Paso "Subiendo el instalador"
    & gh release upload "latest" $Instalador --clobber --repo $ReleasesRepo
    if ($LASTEXITCODE -ne 0) { Die "No se pudo subir el instalador." }
    Write-Ok "asset $AssetNombre reemplazado"

    # ------------------------------------------------ 9. verificacion final

    Write-Paso "Verificando lo publicado"
    $Publicado = gh api "repos/$ReleasesRepo/contents/apps/$AppId/latest.json" `
                      --jq .content 2>$null
    if (-not $Publicado) { Die "No se pudo leer el manifiesto recien publicado." }

    $Texto = [System.Text.Encoding]::UTF8.GetString(
        [System.Convert]::FromBase64String((($Publicado -join "") -replace '\s', '')))
    $Leido = $Texto | ConvertFrom-Json
    if ($Leido.version -ne $BuildVersion) {
        Die "El manifiesto publicado dice $($Leido.version), no $BuildVersion."
    }
    if ($Leido.sha256.ToLower() -ne $Sha) {
        Die "El SHA256 publicado no coincide con el del instalador."
    }
    Write-Ok "publicado: $($Leido.version) / $($Leido.sha256.Substring(0, 12))..."
}
finally {
    # ------------------------------------------------------ 10. restaurar

    Write-Paso "Restaurando el estado de desarrollo"
    Push-Location $RepoRoot
    try {
        & python tools\generar_build_info.py --restaurar | Out-Null
        Write-Ok "libs/build_info.py y version.txt vuelven al estado de desarrollo"
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Publicada la version $BuildVersion" -ForegroundColor Green
Write-Host "Asset     : $AssetNombre" -ForegroundColor Green
Write-Host "SHA256    : $Sha" -ForegroundColor Green
Write-Host ""
Write-Host "Falta el E2E en una PC real. Ver docs/ACTUALIZACION-AUTOMATICA.md." -ForegroundColor Yellow
