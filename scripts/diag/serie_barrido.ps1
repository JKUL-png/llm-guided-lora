# Corre en serie sesiones aisladas de "Opus + barrido" (sin GPU). Uso: serie_barrido.ps1 -Pares "1:1,2:2"  (sesion:semilla; la semilla solo se anota)
param([string]$Pares)
$env:PYTHONIOENCODING = "utf-8"
$diag = "<proyecto>/paper2\scripts\diag"
$res = "<proyecto>/paper2\resultados\jaula_barrido"
$log = "$res\serie.log"
foreach ($p in $Pares.Split(",")) {
  $s, $sem = $p.Split(":")
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') instalar sesion $s semilla $sem"
  python "$diag\instalar_barrido.py" $s *>> $log
  if ($LASTEXITCODE -ne 0) { Add-Content $log "fallo la instalacion; me detengo"; break }
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') nvidia-smi antes: $(wsl.exe -d Ubuntu-24.04 -- nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') inicio sesion $s"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$diag\lanzar_sesion.ps1" -Modelo claude-opus-5-5 -Prompt <carpeta-aislada>\control\prompt.txt -Salida "<carpeta-aislada>\registro\sesion_barrido$s.jsonl"
  New-Item -ItemType Directory -Force "$res\sesion$s" | Out-Null
  Copy-Item <carpeta-aislada>\registro\gancho.jsonl, "<carpeta-aislada>\registro\sesion_barrido$s.jsonl" "$res\sesion$s\" -ErrorAction SilentlyContinue
  Copy-Item "<carpeta-aislada>\salida\capas_barrido_$s.json" "$res\sesion$s\" -ErrorAction SilentlyContinue
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') fin sesion $s"
}
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') serie terminada"
