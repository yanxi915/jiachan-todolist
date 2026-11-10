# 在桌面创建「探头待办」快捷方式：目标 pythonw.exe，无黑框，图标用项目内 app.ico
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $root
$pyw = "D:\Program Files (x86)\python\pythonw.exe"
if (-not (Test-Path $pyw)) {
    $cand = (Get-Command pythonw.exe -ErrorAction SilentlyContinue)
    if ($cand) { $pyw = $cand.Source }
}
$main = Join-Path $root "app\main.py"
$icon = Join-Path $root "assets\app.ico"
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop "探头待办.lnk"

$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = '"' + $main + '"'
$s.WorkingDirectory = $root
$s.WindowStyle = 7
if (Test-Path $icon) { $s.IconLocation = $icon }
$s.Description = "桌面悬浮待办小部件（探头待办）"
$s.Save()

Write-Output ("shortcut=" + $lnk)
Write-Output ("target=" + $pyw)
Write-Output ("exists=" + (Test-Path $lnk))
