# bootstrap_runtime_win7.ps1  (兼容 Windows 7 / Python 3.8)
$ErrorActionPreference = 'Stop'

# 清除代理环境变量：pip 会读取系统/环境代理设置，
# 若用户开着代理但代理软件未运行，会导致下载与安装失败。
$env:HTTP_PROXY = ''
$env:HTTPS_PROXY = ''
$env:http_proxy = ''
$env:https_proxy = ''
$env:NO_PROXY = '*'
$env:no_proxy = '*'

$WORK_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$RUNTIME = Join-Path $WORK_DIR 'runtime'
$PY_ZIP = Join-Path $RUNTIME 'python_embed.zip'
$PACKAGES = @('numpy<2','pillow<10','piexif','exifread','PyWavelets<2')
$MIRRORS = @('https://mirrors.aliyun.com/pypi/simple','https://pypi.tuna.tsinghua.edu.cn/simple','https://mirrors.ustc.edu.cn/pypi/web/simple')

# 自动测速选最快镜像源
function Select-FastestMirror {
    param([string[]]$Mirrors)
    $results = @()
    foreach ($m in $Mirrors) {
        try {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            $testUrl = $m.TrimEnd('/') + '/pip/'
            $resp = Invoke-WebRequest -Uri $testUrl -UseBasicParsing -TimeoutSec 10
            $sw.Stop()
            $speed = if ($resp.RawContentLength -gt 0) { $resp.RawContentLength / $sw.Elapsed.TotalSeconds } else { 0 }
            Write-Host ("测速 {0}  ->  {1:N0} KB/s" -f $m, ($speed/1KB))
            $results += [PSCustomObject]@{ Url = $m; Speed = $speed }
        } catch {
            Write-Host ("测速 {0}  ->  不可用" -f $m)
        }
    }
    if ($results.Count -eq 0) { return $Mirrors }
    return ($results | Sort-Object Speed -Descending | ForEach-Object { $_.Url })
}
Write-Host '正在测速选择最快镜像源...'
$MIRRORS = @(Select-FastestMirror $MIRRORS)
Write-Host ("最快镜像源: {0}" -f $MIRRORS[0])
$pyExe = Join-Path $RUNTIME 'python.exe'
if (-not (Test-Path $pyExe)) {
    Write-Host 'Step 1: 下载 Python 3.8.10 嵌入式运行时 (兼容 Win7)'
    New-Item -ItemType Directory -Force -Path $RUNTIME | Out-Null
    $pyUrls = @('https://mirrors.huaweicloud.com/python/3.8.10/python-3.8.10-embed-amd64.zip','https://registry.npmmirror.com/-/binary/python/3.8.10/python-3.8.10-embed-amd64.zip','https://www.python.org/ftp/python/3.8.10/python-3.8.10-embed-amd64.zip')
    $downloaded = $false
    foreach ($url in $pyUrls) {
        try { Write-Host "尝试下载: $url"; Invoke-WebRequest -Uri $url -OutFile $PY_ZIP -UseBasicParsing -TimeoutSec 300; $downloaded = $true; break } catch { Write-Host '下载失败，尝试下一个源...' }
    }
    if (-not $downloaded) { Write-Host 'ERROR: Python 下载失败'; Read-Host '按回车退出'; exit 1 }
    Write-Host 'Step 2: 解压 Python'
    Expand-Archive -Path $PY_ZIP -DestinationPath $RUNTIME -Force
    Remove-Item $PY_ZIP -Force
    Write-Host 'Step 3: 启用 site 模块'
    $pth = Join-Path $RUNTIME 'python38._pth'
    if (Test-Path $pth) { (Get-Content $pth) -replace '#import site','import site' | Set-Content $pth }
    Write-Host 'Step 4: 安装 pip 并升级'
    $gp = Join-Path $RUNTIME 'get-pip.py'
    foreach ($url in @('https://mirrors.aliyun.com/pypi/get-pip.py','https://bootstrap.pypa.io/get-pip.py')) { try { Invoke-WebRequest -Uri $url -OutFile $gp -UseBasicParsing; break } catch { } }
    if (Test-Path $gp) { & $pyExe $gp --no-setuptools --no-wheel -i $MIRRORS[0] --proxy ""; Remove-Item $gp -Force }
    & $pyExe -m pip install --upgrade "pip<24" -i $MIRRORS[0] --proxy ""
}
Write-Host '检查并安装依赖包:'
Write-Host $PACKAGES
$installed = $false
try { & $pyExe -c "import numpy, PIL, piexif, exifread, pywt" 2>$null; if ($LASTEXITCODE -eq 0) { $installed = $true } } catch { }
if (-not $installed) {
    Write-Host '部分包缺失，开始安装...'
    $ok = $false
    foreach ($mirror in $MIRRORS) { Write-Host "尝试镜像: $mirror"; & $pyExe -m pip install $PACKAGES -i $mirror --proxy "" --progress-bar on; if ($LASTEXITCODE -eq 0) { $ok = $true; break } }
    if (-not $ok) { Write-Host 'WARNING: 依赖安装失败，请手动执行:'; Write-Host "$pyExe -m pip install $PACKAGES"; Read-Host '按回车退出'; exit 1 }
} else { Write-Host '所有依赖包已安装。' }
Write-Host '配置 tkinter...'
# 说明: 嵌入式 zip 不含 tkinter/tcl。若 runtime 目录中已预置 tkinter 组件
# (tkinter/、tcl/、_tkinter.pyd、tcl86t.dll、tk86t.dll)，则直接复用，实现与下载的 Python 自动合并。
$env:TCL_LIBRARY = Join-Path $RUNTIME 'tcl\tcl8.6'
$env:TK_LIBRARY = Join-Path $RUNTIME 'tcl\tk8.6'
$dlls = Join-Path $RUNTIME 'DLLs'
if (-not (Test-Path $dlls)) { New-Item -ItemType Directory -Force -Path $dlls | Out-Null }

# 1) 确保 _tkinter.pyd 位于 runtime 根目录 (嵌入式解释器从根目录加载扩展)
$tkPydRoot = Join-Path $RUNTIME '_tkinter.pyd'
$tkPydDlls = Join-Path $dlls '_tkinter.pyd'
if (-not (Test-Path $tkPydRoot) -and (Test-Path $tkPydDlls)) {
    Copy-Item $tkPydDlls $tkPydRoot -Force
}
# 兼容旧命名 tkinter.pyd -> _tkinter.pyd
$tkOld = Join-Path $RUNTIME 'tkinter.pyd'
if ((Test-Path $tkOld) -and -not (Test-Path $tkPydRoot)) {
    Rename-Item $tkOld '_tkinter.pyd' -Force
}

# 2) 确保 tcl/tk 运行库 DLL 同时存在于根目录与 DLLs 目录
foreach ($dll in @('tcl86t.dll','tk86t.dll')) {
    $src = Join-Path $RUNTIME $dll
    if (Test-Path $src) { Copy-Item $src $dlls -Force }
}

# 3) 确保 python38._pth 启用 site 并包含当前目录 (让 tkinter 与 site-packages 可被导入)
$pth = Join-Path $RUNTIME 'python38._pth'
if (Test-Path $pth) {
    $lines = @(Get-Content $pth)
    if ($lines -notcontains '.') { $lines = @('.') + $lines }
    $lines = $lines -replace '^#\s*import site', 'import site'
    if ($lines -notcontains 'import site') { $lines += 'import site' }
    $lines | Set-Content $pth
}

# 4) 验证 tkinter 可导入
try { & $pyExe -c "import tkinter" 2>$null; if ($LASTEXITCODE -ne 0) { throw 'tkinter import failed' } } catch { Write-Host 'tkinter 配置失败'; Read-Host '按回车退出'; exit 1 }
Write-Host '所有依赖安装并配置成功。'
Write-Host '正在启动程序: main.py'
# 设置 tkinter 所需环境变量后启动 GUI (用相对文件名避免中文路径编码问题)
$env:TCL_LIBRARY = Join-Path $RUNTIME 'tcl\tcl8.6'
$env:TK_LIBRARY = Join-Path $RUNTIME 'tcl\tk8.6'
Start-Process -FilePath $pyExe -ArgumentList 'main.py' -WorkingDirectory $WORK_DIR
Write-Host '程序已启动，本窗口可关闭。'
Start-Sleep -Seconds 3



