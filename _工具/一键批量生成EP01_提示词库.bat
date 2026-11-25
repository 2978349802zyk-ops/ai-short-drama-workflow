@echo off
chcp 65001 >nul
REM ============================================================
REM  一键批量生成 EP01（从「提示词库_EP01_带参考图.json」读取）
REM  每镜自带参考图锁角色外观，无需手动敲提示词、无需导入 Muse
REM  Muse 无提示词库功能，这个本地 json 就是我们的提示词库
REM ============================================================
setlocal

set PY=D:\muse\muse-protocol\.venv\Scripts\python.exe
set SCRIPTS=C:\Users\admin\AppData\Local\hermes\skills\creative\ai-comic-drama-pipeline\scripts
set LIB=D:\Hermes环境准备\AI漫剧制作\00_项目管理\提示词库_EP01_带参考图.json
set OUT=D:\Hermes环境准备\AI漫剧制作\04_视频素材\待生成\ep01_lib
set MANIFEST=%OUT%\manifest.jsonl

if not exist "%OUT%" mkdir "%OUT%"

echo.
echo [准备] 生成前请确认：1) Muse 浏览器已登录(CDP 9371)  2) 视觉网关 3425 正常
echo [提示词库] %LIB%
echo [输出目录] %OUT%
echo.

cd /d "%SCRIPTS%"
"%PY%" muse_shoot.py ^
  --briefs "%LIB%" ^
  --outdir "%OUT%" ^
  --kind video ^
  --retries 1 ^
  --llm ^
  --manifest "%MANIFEST%"

echo.
echo [完成] 成片在 %OUT%
echo [下一步] 用 MoviePy 剪辑：06_剪辑工程\moviepy_assemble.py
pause
