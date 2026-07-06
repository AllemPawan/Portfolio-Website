$port = 8000
if ($args[0]) { $port = $args[0] }

Write-Host "Starting server at http://localhost:$port" -ForegroundColor Cyan
Write-Host "Open chatbot: http://localhost:$port/projects/ai-chatbot/" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

python -m http.server $port -d "$PSScriptRoot"
