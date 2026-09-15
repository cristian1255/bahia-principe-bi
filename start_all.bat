@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
title Bahia Principe BI - Sistema Unificado

rem Ejecutar siempre desde la raiz del proyecto, aunque el .bat se abra desde otro directorio.
cd /d "%~dp0"

if /i "%~1"=="/check" (
    echo [+] Lanzador encontrado: %~f0
    if exist ".venv\Scripts\python.exe" (echo [+] Entorno virtual encontrado.) else (echo [!] Falta .venv\Scripts\python.exe)
    if exist "app.py" (echo [+] Dashboard encontrado.) else (echo [!] Falta app.py)
    if exist "main.py" (echo [+] Backend encontrado.) else (echo [!] Falta main.py)
    if exist "etl_pipeline.py" (echo [+] ETL principal encontrado.) else (echo [!] Falta etl_pipeline.py)
    exit /b 0
)

set "PORT_BACKEND=8000"
set "PORT_STREAMLIT=8501"

echo ================================================================
echo         BAHIA PRINCIPE HOTELS Y RESORTS - SISTEMA BI
echo ================================================================
echo.

set "PYTHON_EXEC=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXEC=%~dp0.venv\Scripts\python.exe"
)

echo [*] Liberando puertos activos 8000 y 8501...
powershell -NoProfile -Command "$ports = @(8000, 8501); foreach ($p in $ports) { Get-NetTCPConnection -ErrorAction SilentlyContinue -LocalPort $p | ForEach-Object { $_.OwningProcess } | Select-Object -Unique | ForEach-Object { Write-Host \"[!] Cerrando proceso previo en puerto $p (PID $_)...\"; Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"

echo [*] Entorno de ejecucion: %PYTHON_EXEC%
echo.

if /i not "%~1"=="/no-etl" (
    echo [1/3] Ejecutando Pipeline ETL principal...
    "%PYTHON_EXEC%" "%~dp0etl_pipeline.py"
    if errorlevel 1 (
        echo [!] Error durante la ejecucion del ETL.
        if /i not "%~2"=="/no-pause" pause
        exit /b 1
    )
    echo [+] ETL finalizado con exito.
    echo.
) else (
    echo [1/3] ETL omitido por parametro /no-etl.
    echo.
)

echo [2/3] Iniciando Servidor FastAPI (0.0.0.0:%PORT_BACKEND%)...
start "FastAPI Bahia Principe BI" /D "%~dp0" cmd /k ""%PYTHON_EXEC%" -m uvicorn main:app --host 0.0.0.0 --port %PORT_BACKEND% --reload"
timeout /t 2 /nobreak >nul
echo [+] Servidor FastAPI ejecutandose en http://localhost:%PORT_BACKEND%
echo.

echo [3/3] Iniciando Dashboard Interactivo Streamlit (Puerto %PORT_STREAMLIT%)...
start "Streamlit Bahia Principe BI" /D "%~dp0" cmd /k ""%PYTHON_EXEC% -m streamlit run "%~dp0app.py" --server.address 0.0.0.0 --server.port %PORT_STREAMLIT% --server.headless true"

echo.
echo ================================================================
echo  Sistema iniciado correctamente:
echo   - Backend FastAPI: http://localhost:%PORT_BACKEND%
echo   - Swagger: http://localhost:%PORT_BACKEND%/docs
echo   - Dashboard Streamlit: http://localhost:%PORT_STREAMLIT%
echo ================================================================
echo.
if /i not "%~1"=="/no-pause" if /i not "%~2"=="/no-pause" pause
exit /b 0
