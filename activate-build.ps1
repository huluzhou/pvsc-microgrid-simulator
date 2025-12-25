# 激活打包环境 (Windows PowerShell)
& "venv-build\Scripts\Activate.ps1"
Write-Host "已激活打包环境 (venv-build)" -ForegroundColor Green
Write-Host "打包项目: python pack_nuitka.py 或 python build.py" -ForegroundColor Yellow
Write-Host "退出环境: deactivate" -ForegroundColor Yellow

