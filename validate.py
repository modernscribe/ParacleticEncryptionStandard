param(
    [string]$StsDir = (Get-Location).Path,
    [int]$BitsPerStream = 1000000,
    [int]$NumStreams = 100
)

$StsDir = (Resolve-Path $StsDir).Path

$pythonCmd = $null
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} else {
    Write-Host "Python not found in PATH" -ForegroundColor Red
    exit 1
}

$gccCmd = $null
if (Get-Command gcc -ErrorAction SilentlyContinue) {
    $gccCmd = "gcc"
} elseif (Get-Command clang -ErrorAction SilentlyContinue) {
    $gccCmd = "clang"
}

Write-Host ""
Write-Host "=== NIST STS: Build + Chaos RNG Stream Generation + Assess ==="
Write-Host ""

if (-not $gccCmd) {
    Write-Host "[!] No C compiler found (gcc/clang)." -ForegroundColor Red
    Write-Host "    Install one, for example:" -ForegroundColor Yellow
    Write-Host "      choco install mingw -y" -ForegroundColor Yellow
    exit 1
}

$genScript = Join-Path $StsDir "generate_nist_streams.py"
if (-not (Test-Path $genScript)) {
$py = @'
#!/usr/bin/env python3
import argparse
import importlib
import os

def load_rng(module_name, class_name, seed_bytes):
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)
    return cls(seed_bytes)

def bytes_to_bitstring(data, n_bits):
    bits = []
    needed = n_bits
    for b in data:
        for i in range(8):
            if needed == 0:
                return "".join(bits)
            bit = (b >> (7 - i)) & 1
            bits.append("1" if bit else "0")
            needed -= 1
    return "".join(bits)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="chaos")
    parser.add_argument("--cls", default="ParacleticChaosRNG")
    parser.add_argument("--streams", type=int, default=100)
    parser.add_argument("--bits", type=int, default=1_000_000)
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for i in range(1, args.streams + 1):
        rng = load_rng(args.module, args.cls, None)
        n_bytes = (args.bits + 7) // 8
        raw = rng.random_bytes(n_bytes)
        bitstr = bytes_to_bitstring(raw, args.bits)
        fname = os.path.join(args.out_dir, f"chaos_{i:03d}.bin")
        with open(fname, "w", encoding="ascii") as f:
            f.write(bitstr)

if __name__ == "__main__":
    main()
'@
    Set-Content -LiteralPath $genScript -Value $py -Encoding UTF8
}

Set-Location $StsDir

$srcDir = Join-Path $StsDir "src"
if (-not (Test-Path $srcDir)) {
    Write-Host "[!] NIST STS src directory not found: $srcDir" -ForegroundColor Red
    exit 1
}

$srcFiles = Get-ChildItem -Path $srcDir -Filter '*.c' | ForEach-Object { $_.FullName }
if (-not $srcFiles -or $srcFiles.Count -eq 0) {
    Write-Host "[!] No .c files found in $srcDir" -ForegroundColor Red
    exit 1
}

$assessExe = Join-Path $StsDir "assess.exe"
Write-Host "[+] Compiling NIST STS assess binary..."
& $gccCmd -O2 -o $assessExe $srcFiles
if (-not $?) {
    Write-Host "[!] Compilation failed" -ForegroundColor Red
    exit 1
}

$dataDir = Join-Path $StsDir "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

Write-Host ""
Write-Host "[+] Generating chaos RNG streams..."
& $pythonCmd $genScript `
    --module chaos `
    --cls ParacleticChaosRNG `
    --streams $NumStreams `
    --bits $BitsPerStream `
    --out-dir $dataDir

if (-not $?) {
    Write-Host "[!] Python generation failed" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $assessExe)) {
    Write-Host "[!] assess executable not found after compile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[+] Running NIST STS assessment..."
Write-Host ""
& $assessExe $BitsPerStream

Write-Host ""
Write-Host "=== COMPLETE ==="
