$ErrorActionPreference = "Stop"

$serviceName = "AlarmClock"
$displayName = "Alarm Clock Service"
$description = "Background alarm clock daemon with persistent alarms"
$exePath = "$PSScriptRoot\alarm-clock.exe"
$args = "daemon"

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Write-Host "Service already exists. Removing..."
    sc.exe stop $serviceName
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

New-Service -Name $serviceName -BinaryPathName "`"$exePath`" $args" `
    -DisplayName $displayName -Description $description `
    -StartupType Automatic

Write-Host "Service created. Starting..."
Start-Service -Name $serviceName
Write-Host "Service started successfully."
