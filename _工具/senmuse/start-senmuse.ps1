# SenMuse 4 实例保活启动脚本（Windows PowerShell）
# 作用：逐个检查 4 个实例，没在跑的拉起来（最小化窗口），在跑的跳过。
# 用法：
#   1. 手动：右键 → 使用 PowerShell 运行
#   2. 开机自启：Win+R 输入 shell:startup，把本文件的快捷方式放进去
#   3. 定时保活：任务计划程序里建一个每 10 分钟运行本脚本的任务（可选）
#
# 前提：本机代理（127.0.0.1:7897）开着；4 个实例各自已 login（acc1 已登录，2/3/4 需本人登录）。

$SenMuseDir = "D:\senmuse"
$Instances = @(
    @{ Port = 47831; Data = ".senmuse-api"   },
    @{ Port = 47832; Data = ".senmuse-api-2" },
    @{ Port = 47833; Data = ".senmuse-api-3" },
    @{ Port = 47834; Data = ".senmuse-api-4" }
)

foreach ($inst in $Instances) {
    $url = "http://127.0.0.1:$($inst.Port)/healthz"
    $alive = $false
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 3
        if ($r.alive) { $alive = $true }
    } catch { }
    if ($alive) {
        Write-Host "端口 $($inst.Port) 已在运行，跳过。"
        continue
    }
    Write-Host "端口 $($inst.Port) 未运行，正在启动（data: $($inst.Data)）……"
    Start-Process -FilePath "node" `
        -ArgumentList "scripts/senmuse-api.mjs", "serve", "--data", $inst.Data `
        -WorkingDirectory $SenMuseDir `
        -WindowStyle Minimized
}

Start-Sleep -Seconds 3
foreach ($inst in $Instances) {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$($inst.Port)/healthz" -TimeoutSec 5
        if ($r.alive) { Write-Host "端口 $($inst.Port) OK" }
    } catch {
        Write-Host "端口 $($inst.Port) 仍连不上，请手动在 $SenMuseDir 里运行 serve --data $($inst.Data) 看报错。"
    }
}
