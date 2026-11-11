# Abre una sesión aislada. Uso: lanzar_sesion.ps1 -Modelo claude-opus-5-5 -Prompt <carpeta-aislada>\control\prompt.txt -Salida <carpeta-aislada>\registro\sesion.jsonl
param([string]$Modelo, [string]$Prompt, [string]$Salida)
Set-Location <carpeta-aislada>
# Quita variables heredadas que pudieran apuntar al proyecto o a otra sesión
Get-ChildItem Env: | Where-Object { $_.Name -match '^(CLAUDE|ANTHROPIC_BASE|PROYECTO|OLDPWD|PWD)' } | ForEach-Object { Remove-Item "Env:$($_.Name)" }
$env:CLAUDE_CODE_DISABLE_AUTO_MEMORY = '1'
$env:DISABLE_TELEMETRY = '1'
$texto = Get-Content -Raw -Encoding UTF8 $Prompt
$texto | & <carpeta-aislada>\control\claude.exe -p `
  --model $Modelo `
  --tools Bash `
  --restricted `
  --settings <carpeta-aislada>\control\ajustes.json `
  --strict-mcp-config `
  --disable-slash-commands `
  --no-session-persistence `
  --output-format stream-json --verbose | Out-File -Encoding utf8 $Salida
