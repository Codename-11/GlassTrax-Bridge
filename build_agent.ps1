#Requires -Version 5.1
<#
.SYNOPSIS
    Builds GlassTrax Agent Windows installer

.DESCRIPTION
    This script builds a standalone Windows installer for the GlassTrax Agent.
    It downloads Python 3.11 32-bit embeddable, installs dependencies, and
    creates an Inno Setup installer.

    Steps:
    1. Clean build directories (optional)
    2. Download Python 3.11 32-bit embeddable
    3. Extract Python to build directory
    4. Enable pip in embedded Python
    5. Install pip
    6. Install agent dependencies
    7. Copy agent source files
    8. Generate Inno Setup script
    9. Compile installer

.PARAMETER Clean
    Clean build directories before starting

.PARAMETER SkipInstaller
    Skip Inno Setup compilation (for testing build process)

.PARAMETER SkipDownload
    Skip downloading Python (use cached version)

.PARAMETER Verbose
    Show detailed output

.EXAMPLE
    .\build_agent.ps1
    Build the installer

.EXAMPLE
    .\build_agent.ps1 -Clean
    Clean build and rebuild from scratch

.EXAMPLE
    .\build_agent.ps1 -SkipInstaller
    Build without compiling installer (for testing)
#>

param(
    [switch]$Clean,
    [switch]$SkipInstaller,
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"

# Configuration
$PYTHON_VERSION = "3.11.9"
$PYTHON_URL = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-embed-win32.zip"
$GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# Paths
$ProjectRoot = $PSScriptRoot
$BuildCache = Join-Path $ProjectRoot ".build_cache"
$BuildDir = Join-Path $ProjectRoot "build" "agent"
$DistDir = Join-Path $ProjectRoot "dist"
$AgentDir = Join-Path $ProjectRoot "agent"

# Read version from VERSION file
$VersionFile = Join-Path $ProjectRoot "VERSION"
if (Test-Path $VersionFile) {
    $Version = (Get-Content $VersionFile -Raw).Trim()
} else {
    Write-Host "ERROR: VERSION file not found!" -ForegroundColor Red
    exit 1
}

# Banner
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GlassTrax Agent Build Script" -ForegroundColor Cyan
Write-Host "  Version: $Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Clean (optional)
Write-Host "[1/9] Preparing directories..." -ForegroundColor Yellow
if ($Clean) {
    Write-Host "  Cleaning build directories..." -ForegroundColor Gray
    if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
    if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
}

# Create directories
New-Item -ItemType Directory -Path $BuildCache -Force | Out-Null
New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
Write-Host "  Done" -ForegroundColor Green

# Step 2: Download Python embeddable
Write-Host "[2/9] Checking Python embeddable..." -ForegroundColor Yellow
$PythonZip = Join-Path $BuildCache "python-$PYTHON_VERSION-embed-win32.zip"
$PythonDir = Join-Path $BuildDir "python"

if (-not (Test-Path $PythonZip) -and -not $SkipDownload) {
    Write-Host "  Downloading Python $PYTHON_VERSION (32-bit)..." -ForegroundColor Gray
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $PYTHON_URL -OutFile $PythonZip -UseBasicParsing
        Write-Host "  Downloaded successfully" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to download Python: $_" -ForegroundColor Red
        exit 1
    }
} elseif (Test-Path $PythonZip) {
    Write-Host "  Using cached Python" -ForegroundColor Gray
} else {
    Write-Host "  ERROR: Python zip not found and -SkipDownload specified" -ForegroundColor Red
    exit 1
}

# Step 3: Extract Python
Write-Host "[3/9] Extracting Python..." -ForegroundColor Yellow
if (Test-Path $PythonDir) { Remove-Item $PythonDir -Recurse -Force }
try {
    Expand-Archive -Path $PythonZip -DestinationPath $PythonDir -Force
    Write-Host "  Done" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to extract Python: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Enable pip in embedded Python
Write-Host "[4/9] Enabling pip..." -ForegroundColor Yellow
$PthFile = Get-ChildItem $PythonDir -Filter "python*._pth" | Select-Object -First 1
if ($PthFile) {
    $PthContent = Get-Content $PthFile.FullName -Raw
    # Uncomment 'import site' to enable pip
    $PthContent = $PthContent -replace "^#import site", "import site"
    # Also add Lib\site-packages if not present
    if ($PthContent -notmatch "Lib\\site-packages") {
        $PthContent = $PthContent + "`nLib\site-packages"
    }
    Set-Content -Path $PthFile.FullName -Value $PthContent -NoNewline
    Write-Host "  Modified $($PthFile.Name)" -ForegroundColor Green
} else {
    Write-Host "  WARNING: ._pth file not found" -ForegroundColor Yellow
}

# Step 5: Install pip
Write-Host "[5/9] Installing pip..." -ForegroundColor Yellow
$GetPipPath = Join-Path $BuildCache "get-pip.py"
$PythonExe = Join-Path $PythonDir "python.exe"

if (-not (Test-Path $GetPipPath)) {
    Write-Host "  Downloading get-pip.py..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $GET_PIP_URL -OutFile $GetPipPath -UseBasicParsing
    } catch {
        Write-Host "  ERROR: Failed to download get-pip.py: $_" -ForegroundColor Red
        exit 1
    }
}

try {
    $pipOutput = & $PythonExe $GetPipPath --no-warn-script-location 2>&1
    Write-Host "  Done" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to install pip: $_" -ForegroundColor Red
    exit 1
}

# Step 6: Install dependencies
Write-Host "[6/9] Installing dependencies..." -ForegroundColor Yellow
$RequirementsFile = Join-Path $AgentDir "requirements_agent.txt"

if (-not (Test-Path $RequirementsFile)) {
    Write-Host "  ERROR: requirements_agent.txt not found!" -ForegroundColor Red
    exit 1
}

try {
    $pipInstall = & $PythonExe -m pip install -r $RequirementsFile --no-warn-script-location 2>&1
    Write-Host "  Done" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to install dependencies: $_" -ForegroundColor Red
    exit 1
}

# Step 7: Copy source files
Write-Host "[7/9] Copying source files..." -ForegroundColor Yellow
$AppDir = Join-Path $BuildDir "app"
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null

# Copy agent package
$AgentDest = Join-Path $AppDir "agent"
if (Test-Path $AgentDest) { Remove-Item $AgentDest -Recurse -Force }
Copy-Item -Path $AgentDir -Destination $AgentDest -Recurse

# Clean __pycache__ and .pyc files
Get-ChildItem -Path $AgentDest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $AgentDest -Recurse -File -Filter "*.pyc" | Remove-Item -Force

# Copy VERSION file
Copy-Item -Path $VersionFile -Destination $AppDir

# Copy config example
$ConfigExample = Join-Path $ProjectRoot "agent_config.example.yaml"
if (Test-Path $ConfigExample) {
    Copy-Item -Path $ConfigExample -Destination $AppDir
}

Write-Host "  Done" -ForegroundColor Green

# Step 8: Generate Inno Setup script
Write-Host "[8/9] Generating installer script..." -ForegroundColor Yellow
$InstallerScript = Join-Path $BuildDir "installer.iss"

# Generate unique GUID for this app (consistent across builds)
$AppGuid = "B8E4F2A1-3C7D-4E9F-A5B6-8D2C1E3F4A5B"

$InstallerContent = @"
; GlassTrax Agent Installer
; Generated by build_agent.ps1
; Version: $Version

#define MyAppName "GlassTrax Agent"
#define MyAppVersion "$Version"
#define MyAppPublisher "GlassTrax Bridge"
#define MyAppURL "https://github.com/Codename-11/GlassTrax-Bridge"

[Setup]
AppId={{$AppGuid}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=$DistDir
OutputBaseFilename=GlassTraxAgent-$Version-Setup
SetupIconFile=$AgentDest\icons\icon_running.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x86 x64
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\agent\icons\icon_running.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically with Windows"; GroupDescription: "Startup Options:"; Flags: unchecked

[Files]
Source: "$PythonDir\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "$AppDir\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu - Tray Mode (default)
Name: "{group}\{#MyAppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m agent.cli --tray"; WorkingDir: "{app}"; IconFilename: "{app}\agent\icons\icon_running.ico"; Comment: "Start GlassTrax Agent in system tray"
; Start Menu - Console Mode
Name: "{group}\{#MyAppName} (Console)"; Filename: "{app}\python\python.exe"; Parameters: "-m agent.cli --console"; WorkingDir: "{app}"; IconFilename: "{app}\agent\icons\icon_running.ico"; Comment: "Start GlassTrax Agent in console mode"
; Start Menu - Uninstall
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop Icon (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m agent.cli --tray"; WorkingDir: "{app}"; IconFilename: "{app}\agent\icons\icon_running.ico"; Tasks: desktopicon; Comment: "Start GlassTrax Agent"

[Registry]
; Auto-start on Windows boot (optional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "GlassTraxAgent"; ValueData: """{app}\python\pythonw.exe"" -m agent.cli --tray"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Launch after install
Filename: "{app}\python\pythonw.exe"; Parameters: "-m agent.cli --tray"; WorkingDir: "{app}"; Description: "Launch GlassTrax Agent"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop any running instance before uninstall
Filename: "taskkill"; Parameters: "/F /IM pythonw.exe"; Flags: runhidden; RunOnceId: "StopAgent"

[Code]
// Check if agent is running and warn user
function InitializeUninstall(): Boolean;
begin
  Result := True;
  // Could add check for running process here
end;
"@

Set-Content -Path $InstallerScript -Value $InstallerContent -Encoding UTF8
Write-Host "  Generated installer.iss" -ForegroundColor Green

# Step 9: Compile installer
if (-not $SkipInstaller) {
    Write-Host "[9/9] Compiling installer..." -ForegroundColor Yellow

    # Find Inno Setup
    $InnoSetupPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    $InnoSetup = $InnoSetupPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $InnoSetup) {
        Write-Host ""
        Write-Host "  ERROR: Inno Setup 6 not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Please install Inno Setup 6 from:" -ForegroundColor Yellow
        Write-Host "  https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Or run with -SkipInstaller to skip compilation" -ForegroundColor Gray
        exit 1
    }

    Write-Host "  Using: $InnoSetup" -ForegroundColor Gray

    try {
        & $InnoSetup /Q $InstallerScript
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup returned exit code $LASTEXITCODE"
        }
        Write-Host "  Done" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to compile installer: $_" -ForegroundColor Red
        exit 1
    }

    # Success banner
    $InstallerPath = Join-Path $DistDir "GlassTraxAgent-$Version-Setup.exe"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Build Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Installer: $InstallerPath" -ForegroundColor Cyan
    Write-Host ""

    # Check file size
    if (Test-Path $InstallerPath) {
        $FileSize = (Get-Item $InstallerPath).Length / 1MB
        Write-Host "  Size: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Gray
    }
} else {
    Write-Host "[9/9] Skipping installer compilation (-SkipInstaller)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  Build Complete (no installer)" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Build output: $BuildDir" -ForegroundColor Cyan
}

Write-Host ""
