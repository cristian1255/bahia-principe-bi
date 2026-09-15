# Plan de Implementación: Aplicación Nativa Bahía Príncipe BI para Ejecutivos

Este plan detalla la transformación de la aplicación actual basada en WebView a una aplicación nativa completa utilizando Jetpack Compose. El objetivo es proporcionar una herramienta profesional para ejecutivos con múltiples funciones y visualización de datos en tiempo real.

## User Review Required

> [!IMPORTANT]
> **Cambio de Arquitectura**: La aplicación dejará de cargar la página de Streamlit. En su lugar, consumirá datos directamente desde una API (o un mock de datos en línea) y los mostrará en una interfaz nativa.
> **Diseño Formal**: Se utilizará Material Design 3 con una paleta de colores sobria y profesional.

## Proposed Changes

### [Infraestructura y Dependencias]

Se actualizará el entorno para soportar Jetpack Compose y las librerías necesarias para una app moderna.

#### [MODIFY] [build.gradle (app)](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/build.gradle)
- Habilitar `buildFeatures { compose true }`.
- Agregar dependencias de Jetpack Compose, Navigation y ViewModel.

### [Interfaz de Usuario (UI)]

Se creará una estructura de navegación con múltiples pantallas.

#### [NEW] [LoginScreen.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/ui/screens/LoginScreen.kt)
- Pantalla de inicio formal con autenticación.

#### [NEW] [DashboardScreen.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/ui/screens/DashboardScreen.kt)
- Pantalla principal con tarjetas de KPIs (Ingresos, Ocupación, ADR).
- Gráficos de tendencias nativos.

#### [NEW] [ReportsScreen.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/ui/screens/ReportsScreen.kt)
- Listado de reportes detallados con filtros por fecha y región.

#### [NEW] [ExecutiveNavigation.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/ui/navigation/ExecutiveNavigation.kt)
- Definición de la estructura de navegación y Bottom Bar.

### [Lógica y Datos]

Implementación del patrón MVVM para separar la lógica de negocio de la interfaz.

#### [NEW] [ExecutiveViewModel.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/ui/viewmodel/ExecutiveViewModel.kt)
- Manejo del estado de la UI y llamada a servicios de datos.

#### [NEW] [DataModels.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/data/model/DataModels.kt)
- Definición de entidades (KPI, Reporte, Usuario).

#### [MODIFY] [MainActivity.kt](file:///C:/Users/Informatica/Desktop/bahia-principe-bi/android_project/app/src/main/java/com/bahiaprincipe/bi/MainActivity.kt)
- Reemplazar el WebView por el host de navegación de Compose.

## Verification Plan

### Manual Verification
- Verificar que el flujo de navegación entre Dashboard y Reportes sea fluido.
- Confirmar que los datos se visualicen correctamente en las tarjetas de KPI.
- Validar el diseño en modo horizontal (Landscape) dado el perfil ejecutivo.

### Automated Tests
- Implementar pruebas unitarias básicas para el `ExecutiveViewModel` para asegurar que los KPIs se procesan correctamente.
