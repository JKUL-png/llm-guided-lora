# Lanza lanzar_sesion.ps1 en un proceso oculto e independiente de Claude Code. Uso: lanzar_oculto.ps1 -Modelo M -Prompt P -Salida S
param([string]$Modelo, [string]$Prompt, [string]$Salida)
$a = "-NoProfile -ExecutionPolicy Bypass -File <proyecto>/paper2\scripts\diag\lanzar_sesion.ps1 -Modelo $Modelo -Prompt $Prompt -Salida $Salida"
Start-Process powershell.exe -ArgumentList $a -WindowStyle Hidden
