@echo off
powershell -WindowStyle Hidden -Command "Get-PhysicalDisk | Select-Object -ExpandProperty SerialNumber | ForEach-Object { $_.TrimEnd('.') } | Set-Clipboard"