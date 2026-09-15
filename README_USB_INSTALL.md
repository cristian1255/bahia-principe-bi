# Instalación USB de Bahía Príncipe BI en Android

Este manual explica cómo instalar la aplicación Android que envuelve el dashboard web de Bahía Príncipe BI y cómo ejecutarla por USB desde una laptop con Windows.

## 1. Requisitos

- Laptop con Windows 10 o 11
- Python 3.10 o superior
- Android SDK Platform Tools (`adb.exe`)
- Teléfono Android con depuración USB habilitada
- Cable USB original o de buena calidad

## 2. Activar Depuración USB en el teléfono

1. Abre `Ajustes`.
2. Entra en `Acerca del teléfono`.
3. Toca varias veces `Número de compilación` para activar `Opciones de desarrollador`.
4. Vuelve a `Ajustes` y entra en `Sistema` > `Opciones de desarrollador`.
5. Activa `Depuración USB`.
6. Cuando aparezca el diálogo en el teléfono, acepta la autorización.
7. Conecta el móvil a la laptop con USB.

## 3. Verificar ADB

Abre una terminal PowerShell y ejecuta:

```powershell
adb devices
```

Si aparece el identificador del dispositivo, el teléfono ya está autorizado y listo para instalación.

## 4. Abrir el script de instalación

Desde la carpeta del proyecto, ejecuta:

```powershell
scripts\instalar_en_android.bat
```

El script hará lo siguiente:

- Comprobar Python
- Comprobar `adb`
- Detectar el dispositivo USB
- Iniciar el backend en `0.0.0.0:8501`
- Buscar el APK generado
- Instalarlo con `adb install -r`
- Lanzar la app con `adb shell am start -n com.bahiaprincipe.bi/.MainActivity`

## 5. Configuración del servidor web

La app web del dashboard debe arrancarse con el host accesible desde el dispositivo Android:

```powershell
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

La aplicación Android está configurada para apuntar a la IP local de la laptop; el script automatiza esta detección.

## 6. Icono y nombre de la app

El nombre visible de la app es:

- Bahía Príncipe BI

Y se configura mediante:

- `android:label="Bahía Príncipe BI"`
- `@mipmap/ic_launcher`

Coloca el icono `ic_launcher.png` en la carpeta `android_project/res/mipmap*` de tu proyecto Android Studio.

## 7. Solución de problemas

### El móvil no aparece en `adb devices`
- Comprueba que `Depuración USB` está activada.
- Acepta la autorización del PC en el teléfono.
- Cambia el cable USB.
- Reinicia `adb`:

```powershell
adb kill-server
adb start-server
adb devices
```

### El APK no se instala
- Comprueba que el archivo exista en la ruta esperada.
- Compila primero el proyecto Android en Android Studio:
  - Build > Build Bundle(s)/APK(s) > Build APK(s)

### La app no abre
- Verifica que la IP local es correcta y que el backend responde:

```powershell
http://<IP_LOCAL>:8501
```

## 8. Resultado esperado

Una vez completado, la pantalla del teléfono mostrará la aplicación `Bahía Príncipe BI` y la dashboard web estará visible en modo WebView completo.
