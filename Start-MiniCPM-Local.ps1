$ErrorActionPreference = 'Stop'
$server = 'C:\Users\J1NnY\llama.cpp\llama-server.exe'
$model = 'D:\models\MiniCPM5-1B-heretic-Q4_K_M.gguf'
$port = 8081

if (-not (Test-Path -LiteralPath $server)) { throw "llama-server.exe was not found: $server" }
if (-not (Test-Path -LiteralPath $model)) { throw "MiniCPM model was not found: $model" }

$ready = Test-NetConnection -ComputerName '127.0.0.1' -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $ready) {
    $logDir = Join-Path $env:LOCALAPPDATA 'mikasa\logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $stdout = Join-Path $logDir 'minicpm-llama.out.log'
    $stderr = Join-Path $logDir 'minicpm-llama.err.log'
    Start-Process -FilePath $server -ArgumentList @('-m', $model, '--host', '127.0.0.1', '--port', "$port", '-c', '8192') -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    for ($try = 1; $try -le 30; $try++) {
        Start-Sleep -Seconds 1
        if (Test-NetConnection -ComputerName '127.0.0.1' -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue) { $ready = $true; break }
    }
}
if (-not $ready) { throw 'MiniCPM did not start. Check %LOCALAPPDATA%\mikasa\logs\minicpm-llama.err.log.' }

& (Join-Path $env:USERPROFILE '.local\bin\mikasa.exe') --tui
