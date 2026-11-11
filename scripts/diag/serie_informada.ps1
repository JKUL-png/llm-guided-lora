# Corre en serie sesiones informadas aisladas. Uso: serie_informada.ps1 -Pares "3:3,4:0"  (sesion:semilla)
param([string]$Pares)
$env:PYTHONIOENCODING = "utf-8"
$diag = "<proyecto>/paper2\scripts\diag"
$res = "<proyecto>/paper2\resultados\jaula_informada"
$log = "$res\serie.log"
foreach ($p in $Pares.Split(",")) {
  $s, $sem = $p.Split(":")
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') instalar sesion $s semilla $sem"
  python "$diag\instalar_informado.py" $s $sem *>> $log
  if ($LASTEXITCODE -ne 0) { Add-Content $log "fallo la instalacion; me detengo"; break }
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') inicio sesion $s"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$diag\lanzar_sesion.ps1" -Modelo claude-opus-5-5 -Prompt <carpeta-aislada>\control\prompt.txt -Salida "<carpeta-aislada>\registro\sesion_informada$s.jsonl"
  New-Item -ItemType Directory -Force "$res\sesion$s" | Out-Null
  Copy-Item <carpeta-aislada>\registro\gancho.jsonl, "<carpeta-aislada>\registro\sesion_informada$s.jsonl" "$res\sesion$s\" -ErrorAction SilentlyContinue
  Copy-Item "<carpeta-aislada>\salida\capas_informado_$s.json" "$res\sesion$s\" -ErrorAction SilentlyContinue
  Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') fin sesion $s"
}
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') serie terminada"
