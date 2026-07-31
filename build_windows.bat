@echo off
REM ============================================================
REM  FZK Windows 桌面应用本地构建脚本
REM  环境要求:Windows 10/11 + Python 3.12 + Node 20 + pnpm
REM  用法:双击或 cmd 中执行 build_windows.bat
REM  产物:dist\FZK.exe
REM ============================================================
setlocal

echo [1/5] 安装前端依赖...
pushd frontend
call pnpm install --frozen-lockfile=false
if errorlevel 1 (echo 前端依赖安装失败 & popd & exit /b 1)

echo [2/5] 构建前端 dist...
call pnpm build
if errorlevel 1 (echo 前端构建失败 & popd & exit /b 1)
popd

if not exist frontend\dist\index.html (echo frontend\dist\index.html 不存在 & exit /b 1)

echo [3/5] 安装 Python 依赖...
python -m pip install --upgrade pip
pip install -r requirements-desktop.txt
if errorlevel 1 (echo Python 依赖安装失败 & exit /b 1)

echo [4/5] PyInstaller 打包...
pyinstaller fzk.spec --noconfirm
if errorlevel 1 (echo 打包失败 & exit /b 1)

if not exist dist\FZK.exe (echo dist\FZK.exe 不存在 & exit /b 1)

echo [5/5] 完成!
echo 产物: dist\FZK.exe
echo 数据目录将在首次运行时创建于 exe 旁的 data\ 文件夹
endlocal
