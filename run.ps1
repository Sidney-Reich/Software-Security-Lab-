# Runs the whole experiment with Docker Desktop on Windows: preprocessing, then training, then testing.
# Usage: powershell -ExecutionPolicy Bypass -File .\run.ps1 [-Phase all|preprocess|train|test] [-Cases all|N] [-Epochs 20]
# Results end up in results\preprocessing\, results\training\ and results\testing\.
param([string]$Phase = "all", [string]$Cases = "all", [int]$Epochs = 20)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker is not running. Start Docker Desktop and try again." -ForegroundColor Red; exit 1 }
function Check($what) { if ($LASTEXITCODE -ne 0) { Write-Host "$what failed (see the lines above)." -ForegroundColor Red; exit 1 } }
$R = Join-Path $PSScriptRoot "results"; $Vec = Join-Path $R "preprocessing\vectors"

if ($Phase -in "all", "preprocess") {
    Write-Host "== 1. PREPROCESSING  (Juliet CWE-416 -> slices -> labels -> vectors)"
    docker build --load -t sysevr-preprocessing preprocessing; Check "Image build"
    $out = Join-Path $R "preprocessing"
    if (Test-Path $out) { Remove-Item -Recurse -Force $out }
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    docker run --rm -v "${out}:/results" sysevr-preprocessing $Cases; Check "Preprocessing"
}
if ($Phase -in "all", "train", "test") {
    if (-not (Test-Path (Join-Path $Vec "dl_input_shuffle"))) {
        Write-Host "No preprocessing output in ${Vec}: run with -Phase preprocess first." -ForegroundColor Red; exit 1
    }
    docker build --load -t sysevr-model model; Check "Image build" }
if ($Phase -in "all", "train") {
    Write-Host "== 2. TRAINING  (BGRU, $Epochs epochs, train split)"
    $out = Join-Path $R "training"; New-Item -ItemType Directory -Force -Path $out | Out-Null
    docker run --rm -v "${Vec}:/vectors:ro" -v "${out}:/out" sysevr-model train.py /vectors /out --epochs $Epochs; Check "Training"
}
if ($Phase -in "all", "test") {
    $model = Join-Path $R "training\bgru.pt"
    if (-not (Test-Path $model)) { $model = Join-Path $PSScriptRoot "reference\training\bgru.pt" }
    Write-Host "== 3. TESTING  ($model on the test split)"
    $out = Join-Path $R "testing"; New-Item -ItemType Directory -Force -Path $out | Out-Null
    docker run --rm -v "${Vec}:/vectors:ro" -v "${model}:/bgru.pt:ro" -v "${out}:/out" sysevr-model test.py /bgru.pt /vectors /out; Check "Testing"
}
