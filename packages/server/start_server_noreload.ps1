$env:PYTHONPATH = "$PSScriptRoot\src"
Set-Location $PSScriptRoot
uvicorn reins.api.server:create_app --factory --host 0.0.0.0 --port 8094 --no-access-log
