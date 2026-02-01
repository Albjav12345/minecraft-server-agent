@echo off
setlocal enabledelayedexpansion
title MineGenesis AI Console

:: Silent dependency check and installation
echo Preparando entorno MineGenesis...
pip install -q -r requirements.txt >nul 2>&1

:: Clear console for clean startup
cls

:: Launch application
python run.py

:: Error handling
if errorlevel 1 (
    echo.
    echo ========================================
    echo   ERROR AL INICIAR MINEGENESIS
    echo ========================================
    echo.
    echo Posibles causas:
    echo   - Python no instalado o no esta en PATH
    echo   - Dependencias faltantes
    echo.
    echo Intenta ejecutar manualmente:
    echo   pip install -r requirements.txt
    echo   python run.py
    echo.
)

pause
