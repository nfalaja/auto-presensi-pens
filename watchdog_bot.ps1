# Watchdog runner lokal untuk main.py
$pythonPath = "C:\Users\Aghna\.gemini\antigravity\scratch\pens-presensi\venv\bin\python.exe"
$scriptPath = "C:\Users\Aghna\.gemini\antigravity\scratch\pens-presensi\main.py"

while ($true) {
    try {
        & $pythonPath $scriptPath
    } catch {
        Start-Sleep -Seconds 5
    }
    Start-Sleep -Seconds 3
}
