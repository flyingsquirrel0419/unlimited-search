param(
    [ValidateSet("install", "update", "uninstall", "help")]
    [string]$Action = "install"
)

$ErrorActionPreference = "Stop"
$Repo = if ($env:UNLIMITED_SEARCH_REPO) { $env:UNLIMITED_SEARCH_REPO } else { "https://github.com/flyingsquirrel0419/unlimited-search.git" }
$HomeDir = if ($env:UNLIMITED_SEARCH_HOME) { $env:UNLIMITED_SEARCH_HOME } else { Join-Path $HOME ".unlimited-search" }
$BinDir = if ($env:UNLIMITED_SEARCH_BIN) { $env:UNLIMITED_SEARCH_BIN } else { Join-Path $HOME ".local\bin" }
$Bin = Join-Path $BinDir "unlimited-search.ps1"

function Show-Help {
@"
unlimited-search installer

Usage:
  install.ps1 [-Action install|update|uninstall|help]

Env:
  UNLIMITED_SEARCH_REPO  Git repo URL. Default: $Repo
  UNLIMITED_SEARCH_HOME  Install dir. Default: $HomeDir
  UNLIMITED_SEARCH_BIN   Bin dir. Default: $BinDir

Commands after install:
  unlimited-search serve
  unlimited-search read https://example.com
  unlimited-search update
  unlimited-search uninstall
  unlimited-search help
"@
}

function Show-UvHelp {
@"
uv is required.

Install uv:
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
"@
}

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "missing required command: $Name"
    }
}

function Write-Wrapper {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    $homeEscaped = $HomeDir.Replace("'", "''")
    @"
`$ErrorActionPreference = "Stop"
`$AppHome = '$homeEscaped'
`$cmd = if (`$args.Count -gt 0) { `$args[0] } else { "help" }
`$rest = if (`$args.Count -gt 1) { `$args[1..(`$args.Count - 1)] } else { @() }
switch (`$cmd) {
  "serve" { & uv --directory `$AppHome run unlimited-search serve @rest; exit `$LASTEXITCODE }
  "read" { & uv --directory `$AppHome run unlimited-search read @rest; exit `$LASTEXITCODE }
  "diagnose" { & uv --directory `$AppHome run unlimited-search diagnose @rest; exit `$LASTEXITCODE }
  "media" { & uv --directory `$AppHome run unlimited-search media @rest; exit `$LASTEXITCODE }
  "update" { & powershell -ExecutionPolicy ByPass -File "`$AppHome\scripts\install.ps1" -Action update; exit `$LASTEXITCODE }
  "uninstall" { & powershell -ExecutionPolicy ByPass -File "`$AppHome\scripts\install.ps1" -Action uninstall; exit `$LASTEXITCODE }
  default {
    Write-Output "unlimited-search"
    Write-Output ""
    Write-Output "Usage:"
    Write-Output "  unlimited-search serve"
    Write-Output "  unlimited-search read URL"
    Write-Output "  unlimited-search diagnose URL"
    Write-Output "  unlimited-search media URL"
    Write-Output "  unlimited-search update"
    Write-Output "  unlimited-search uninstall"
    Write-Output "  unlimited-search help"
    Write-Output ""
    `$jsonPath = `$PSCommandPath.Replace("\", "\\")
    Write-Output ('MCP config: {"mcpServers":{"unlimited-search":{"command":"powershell","args":["-ExecutionPolicy","ByPass","-File","' + `$jsonPath + '","serve"]}}}')
  }
}
"@ | Set-Content -Encoding UTF8 -Path $Bin
}

function Show-Installed {
    $jsonPath = $Bin.Replace("\", "\\")
@"
installed unlimited-search

Try:
  powershell -ExecutionPolicy ByPass -File "$Bin" read https://example.com

MCP config:
  {"mcpServers":{"unlimited-search":{"command":"powershell","args":["-ExecutionPolicy","ByPass","-File","$jsonPath","serve"]}}}
"@
}

function Install-App {
    Assert-Command git
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Show-UvHelp | Write-Error
        exit 1
    }
    if (Test-Path (Join-Path $HomeDir ".git")) {
        Update-App
        return
    }
    if (Test-Path $HomeDir) {
        throw "$HomeDir exists but is not a git checkout"
    }
    git clone $Repo $HomeDir
    uv --directory $HomeDir sync --no-dev
    Write-Wrapper
    Show-Installed
}

function Update-App {
    Assert-Command git
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Show-UvHelp | Write-Error
        exit 1
    }
    if (-not (Test-Path (Join-Path $HomeDir ".git"))) {
        throw "$HomeDir is not installed"
    }
    git -C $HomeDir pull --ff-only
    uv --directory $HomeDir sync --no-dev
    Write-Wrapper
    Show-Installed
}

function Uninstall-App {
    Remove-Item -Recurse -Force $HomeDir, $Bin -ErrorAction SilentlyContinue
    Write-Output "removed unlimited-search"
    Write-Output "remove it from your MCP client config if needed"
}

switch ($Action) {
    "install" { Install-App }
    "update" { Update-App }
    "uninstall" { Uninstall-App }
    "help" { Show-Help }
}
