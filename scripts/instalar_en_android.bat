@echo off
setlocal enabledelayedexpansion

rem ============================================
rem Script de despliegue USB para Bahía Príncipe BI
rem ============================================

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo ==========================================
echo Bahía Príncipe BI - Instalador Android USB
echo ==========================================

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en PATH.
    echo Instala Python 3.10+ y reinicia la terminal.
    exit /b 1
)

echo [OK] Python detectado.

set "ADB_PATH="
where adb >nul 2>nul
if not errorlevel 1 (
    set "ADB_PATH=adb"
) else (
    set "CANDIDATE=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
    if exist "%CANDIDATE%" (
        set "ADB_PATH=%CANDIDATE%"
    ) else (
        set "CANDIDATE=C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe"
        if exist "%CANDIDATE%" (
            set "ADB_PATH=%CANDIDATE%"
        )
    )
)

if "%ADB_PATH%"=="" (
    echo ERROR: ADB no encontrado.
    echo Instala Android SDK Platform Tools o agrega la carpeta platform-tools al PATH.
    exit /b 1
)

echo [OK] ADB encontrado: %ADB_PATH%

call :check_device
if errorlevel 1 exit /b 1

call :detect_ip
if errorlevel 1 exit /b 1

call :start_server
if errorlevel 1 exit /b 1

call :build_apk
if errorlevel 1 exit /b 1

call :install_apk
if errorlevel 1 exit /b 1

call :launch_app
if errorlevel 1 exit /b 1

echo.
echo ¡Instalación exitosa! La app 'Bahía Príncipe BI' ya está ejecutándose en tu teléfono Android.
echo.
exit /b 0

:check_device
    echo [INFO] Revisando dispositivos Android conectados...
    "%ADB_PATH%" devices > temp_adb_devices.txt 2>&1
    type temp_adb_devices.txt
    findstr /I /R "device$" temp_adb_devices.txt >nul
    if errorlevel 1 (
        echo ERROR: No hay ningún teléfono conectado o la depuración USB no está autorizada.
        echo "Conecta tu teléfono Android por USB y activa la Depuración USB en Opciones de Desarrollador"
        del temp_adb_devices.txt >nul 2>&1
        exit /b 1
    )
    del temp_adb_devices.txt >nul 2>&1
    echo [OK] Dispositivo detectado.
    exit /b 0

:detect_ip
    echo [INFO] Detectando IP local de la laptop...
    for /f "tokens=2 delims=[] " %%i in ("ipconfig 2^>nul ^| findstr /R /C:"IPv4"" ) do (
        set "LOCAL_IP=%%i"
        goto :ip_found
    )
    :ip_found
    if "%LOCAL_IP%"=="" (
        echo ERROR: No se pudo detectar la IP de la laptop.
        exit /b 1
    )
    echo [OK] IP local: %LOCAL_IP%
    set "SERVER_URL=http://%LOCAL_IP%:8501"
    exit /b 0

:start_server
    echo [INFO] Iniciando backend del dashboard en %SERVER_URL%
    start "BahiaPrincipeBI-Server" /B python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
    echo [OK] Servidor arrancado en segundo plano.
    timeout /t 8 /nobreak >nul
    exit /b 0

:build_apk
    echo [INFO] Preparando APK Android...
    if not exist "android_project" (
        echo ERROR: No existe la carpeta android_project.
        exit /b 1
    )

    rem Inyección automática de la IP del servidor en la WebView del proyecto Android.
    powershell -NoProfile -Command "(Get-Content 'android_project\MainActivity.kt' -Raw) -replace 'http://SERVER_IP_PLACEHOLDER:8501', 'http://%LOCAL_IP%:8501' | Set-Content 'android_project\MainActivity.kt'"
    powershell -NoProfile -Command "(Get-Content 'android_project\app\src\main\java\com\bahiaprincipe\bi\MainActivity.kt' -Raw) -replace 'http://SERVER_IP_PLACEHOLDER:8501', 'http://%LOCAL_IP%:8501' | Set-Content 'android_project\app\src\main\java\com\bahiaprincipe\bi\MainActivity.kt'"

    if exist "bahia-principe-bi.apk" del /f /q "bahia-principe-bi.apk"

    rem Se espera que el APK se genere con Gradle o con Android Studio.
    rem Si no existe, se muestra una advertencia clara y se permite continuar con un archivo manual.
    if exist "android_project\app\build\outputs\apk\debug\app-debug.apk" (
        copy /Y "android_project\app\build\outputs\apk\debug\app-debug.apk" "bahia-principe-bi.apk" >nul
    ) else if exist "android_project\app\build\outputs\apk\release\app-release.apk" (
        copy /Y "android_project\app\build\outputs\apk\release\app-release.apk" "bahia-principe-bi.apk" >nul
    ) else (
        echo WARNING: No se encontró APK compilado en la ruta esperada.
        echo Asegúrate de compilar el proyecto Android antes de ejecutar este script.
        echo Ejemplo: abrir el proyecto con Android Studio y generar una APK de depuración.
        exit /b 1
    )

    echo [OK] APK generado y listo para instalar.
    exit /b 0

:install_apk
    echo [INFO] Instalando APK en el teléfono vía ADB...
    "%ADB_PATH%" install -r "bahia-principe-bi.apk"
    if errorlevel 1 (
        echo ERROR: La instalación del APK falló.
        exit /b 1
    )
    echo [OK] APK instalado correctamente.
    exit /b 0

:launch_app
    echo [INFO] Abriendo la aplicación en el dispositivo Android...
    "%ADB_PATH%" shell am start -n com.bahiaprincipe.bi/.MainActivity
    if errorlevel 1 (
        echo ERROR: No se pudo abrir la app en el teléfono.
        exit /b 1
    )
    echo [OK] App lanzada correctamente.
    exit /b 0
