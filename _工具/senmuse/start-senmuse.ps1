# SenMuse 服务保活启动脚本（Windows PowerShell）
# 作用：服务没在跑就拉起来（最小化窗口），在跑就什么都不做。
# 用法：
#   1. 手动：右键 → 使用 PowerShell 运行
#   2. 开机自启：Win+R 输入 shell:startup，把本文件的快捷方式放进去
#   3. 定时保活：任务计划程序里建一个每 10 分钟运行本脚本的任务（可选）
#
# 注意：改下面两个路径为你自己的 SenMuse 目录。

$SenMuseDir = "D:\senmuse"
$DataDir = ".senmuse-api"
$HealthUrl = "http://127.0.0.1:47831/healthz"

try {
    $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
    if ($r.alive) {
        Write-Host "SenMuse 已在运行，无需启动。"
        exit 0
    }
} catch {
    # 连不上说明没在跑，继续往下启动
}

Write-Host "SenMuse 未运行，正在启动……"
Start-Process -FilePath "node" `
    -ArgumentList "scripts/senmuse-api.mjs", "serve", "--data", $DataDir `
    -WorkingDirectory $SenMuseDir `
    -WindowStyle Minimized

Start-Sleep -Seconds 3
try {
    $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
    if ($r.alive) { Write-Host "SenMuse 已启动：http://127.0.0.1:47831" }
} catch {
    Write-Host "启动后仍连不上，请手动在 $SenMuseDir 里运行 serve 看报错。"
}
