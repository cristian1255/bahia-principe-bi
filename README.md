# 🏖️🍽️ Bahía Príncipe Hotels & Resorts - Sistema Analítico Operativo y Predictivo de Reservas A&B

> **Plataforma Integral de Business Intelligence y Analítica Predictiva para Restaurantes de Especialidad en Complejos Hoteleros All-Inclusive.**

![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?logo=streamlit)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4+-F7931E?logo=scikit-learn)
![Plotly](https://img.shields.io/badge/Plotly-5.20+-3F4F75?logo=plotly)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 1. 🏨 Contexto del Negocio y Objetivo Estratégico

En la operación de alimentos y bebidas (A&B) de complejos hoteleros de lujo como **Bahía Príncipe Hotels & Resorts** (con 5 hoteles y 20 restaurantes de especialidad temáticos), la gestión de reservas es un factor crítico de satisfacción del huésped, rentabilidad y eficiencia operativa.

### Retos Operativos Principales:
1. **Sobresaturación de Horarios Pico**: Concentración excesiva de comensales en turnos intermedios (19:30 - 21:00) y capacidad ociosa en turnos tempranos y nocturnos.
2. **Fenómeno Cross-Dining (Inter-Hotel)**: Huéspedes de un hotel (ej. *Grand Tulum*) que reservan en restaurantes ubicados físicamente en otro hotel del complejo (ej. *Luxury Akumal*), lo que genera desbalances de costos, rotación de mesas y necesidad de transporte interno.
3. **Servicio VIP y Familias**: Requerimientos prioritarios de atención protocolar para miembros de fidelidad (*Privilege Club*, *VIP1*, *VIP2*) y necesidades de mobiliario infantil (periqueras/sillas altas).
4. **Dimensionamiento de Personal**: Planificación de dotación de meseros y cocineros según la ocupación hotelera proyectada.

### Solución Desarrollada:
Una solución analítica integral que combina un **Data Warehouse bajo Esquema en Estrella (Star Schema)**, un **Pipeline ETL modular y automatizado**, un **Motor Predictivo con Machine Learning (Scikit-Learn)** y una **Aplicación Web Interactiva en Streamlit** para la toma de decisiones gerenciales en tiempo real, lista para desplegarse **100% GRATIS 24/7** en **GitHub y Streamlit Community Cloud**.

---

## 2. 🏛️ Arquitectura del Esquema en Estrella (Star Schema)

El almacén de datos modela los eventos transaccionales de reservas conectando una **Tabla de Hechos Central** con **6 Tablas de Dimensiones**:

```mermaid
erDiagram
    Dim_Hotel ||--o{ Dim_Restaurante : "ubica físicamente"
    Dim_Hotel ||--o{ Fact_Reservas_Restaurantes : "hospeda al comensal"
    Dim_Hotel ||--o{ Dim_Habitacion : "contiene cuartos"
    Dim_Restaurante ||--o{ Fact_Reservas_Restaurantes : "recibe reserva"
    Dim_Horario ||--o{ Fact_Reservas_Restaurantes : "define turno"
    Dim_Tipo_Atencion ||--o{ Fact_Reservas_Restaurantes : "clasifica comensal"
    Dim_Tiempo ||--o{ Fact_Reservas_Restaurantes : "fecha servicio"
    Dim_Habitacion ||--o{ Fact_Reservas_Restaurantes : "cuarto asociado (futuro)"

    Fact_Reservas_Restaurantes {
        int id_reserva PK "ID original de reserva"
        date id_fecha FK "Fecha de servicio"
        varchar id_restaurante FK "Restaurante de especialidad"
        int id_hotel_hospedaje FK "Hotel donde duerme el huésped"
        varchar id_tipo_atencion FK "Categoría y protocolo VIP"
        varchar id_horario FK "Turno y franja horaria"
        int id_habitacion FK "Conexión escalable PMS"
        int num_adultos "Adultos"
        int num_ninos "Niños"
        int num_bebes "Bebés"
        int total_pax "Adultos + Niños + Bebés"
        float habs_invitadas "Habitaciones invitadas"
        boolean es_cross_dining "True si Hotel != Hotel Res."
        boolean requiere_periquera "True si infantes presentes"
        text observaciones_limpias "Notas sanitizadas"
    }

    Dim_Hotel {
        int id_hotel PK "1, 4, 10, 16, 21"
        varchar nombre_hotel "Nombre comercial hotel"
        varchar codigo_origen UK "BPG, AP3, TOI, BPS, BPB"
        varchar categoria "Grand o Luxury"
    }

    Dim_Restaurante {
        varchar id_restaurante PK "DPI, MIK, TEQ, etc."
        varchar nombre_restaurante "Nombre del restaurante"
        varchar especialidad "Gourmet, Japonesa, etc."
        int id_hotel_ubicacion FK "Hotel donde radica"
        int capacidad_maxima_pax "Aforo máximo"
    }

    Dim_Horario {
        varchar id_horario PK "T1_1730, T2_1930, etc."
        int turno "1, 2, 3"
        varchar horario_texto "17:30 - 19:00"
        varchar franja_horaria "Temprano, Central, Nocturno"
    }

    Dim_Tipo_Atencion {
        varchar id_tipo_atencion PK "STANDARD, VIP1, ATE01, etc."
        varchar categoria_atencion "Standard, VIP, Fidelidad, Especial"
        int prioridad_servicio "1 (Máxima) a 4 (Estándar)"
    }

    Dim_Tiempo {
        date id_fecha PK "Fecha calendario"
        int anio "Año"
        int mes "Mes"
        int dia "Día"
        varchar dia_semana "Lunes a Domingo"
        boolean es_fin_de_semana "Viernes, Sábado o Domingo"
        varchar temporada "Alta, Media, Baja"
    }

    Dim_Habitacion {
        int id_habitacion PK "ID habitación"
        varchar numero_habitacion "Número físico de cuarto"
        int id_hotel FK "Hotel al que pertenece"
        varchar tipo_categoria_cuarto "Junior Suite, Presidential, etc."
        varchar pais_origen_agrupado "USA, Canadá, España, etc."
        varchar segmento_mercado "Directo, OTA, Privilege Club"
    }
```

### Distribución de los 20 Restaurantes en los 5 Hoteles:
- **Bahía Príncipe Grand Tulum (`BPG` / ID: 1)**: Don Pablo Gourmet (`DPI`), Tequila Mexicano (`TEQ`), Thali Flavors of India (`HIN`), Portofino Trattoria (`POR`).
- **Bahía Príncipe Luxury Akumal (`AP3` / ID: 4)**: Mikado Teppanyaki & Sushi (`MIK`), Frutos del Mar (`FRU`), Dolce Vita Ristorante (`DOL`), Arlequín Haute Cuisine (`ARK`).
- **Bahía Príncipe Grand Coba (`TOI` / ID: 10)**: Le Gourmet Rodizio Grill (`ROD`), Mediterráneo Coastal Bistro (`MED`), Ku'uk Mayan Gastronomy (`KUB`), Oasis Rodizio & Smokehouse (`OAS`).
- **Bahía Príncipe Luxury Sian Ka'an (`BPS` / ID: 16)**: Alux Cenote Experience (`ALB`), Takara Pan-Asian (`TAK`), Cenote Maya Yucateco (`YUC`), Gran Tortuga Rodizio Prime (`GRA`).
- **Bahía Príncipe Grand Bouganville (`BPB` / ID: 21)**: El Pescador Caribeño (`CAR`), Bella Italia Pizzeria (`BEA`), Bouganville Gourmet Lounge (`GOU`), Los Corales Steakhouse (`LOS`).

---

## 3. ⚙️ Pipeline ETL (`etl_pipeline.py`)

El pipeline modular procesa archivos transaccionales `.xlsx` y `.csv` con las siguientes columnas originales del sistema de reservas:
```
['Remarks', 'Actions', 'Cargado', 'Obs.', 'Cross', 'Atención', '#Adultos', '#Niños', '#Bebés', 
 'Nº Habs. Invitadas', 'Fecha Servicio', 'Servicio', 'Turno', 'Horario', 'Id', 'Usuario', 'Origen', 'Hotel', 'Hotel Res.']
```

### Reglas de Transformación Aplicadas:
1. **Cálculo de Comensales**: `total_pax = #Adultos + #Niños + #Bebés` (garantizando mínimo 1 adulto por reserva).
2. **Identificación de Cross-Dining**: `es_cross_dining = True` cuando el hotel de hospedaje `Hotel Res.` es distinto al hotel donde se ubica el restaurante `Hotel`.
3. **Detección de Mobiliario Infantil**: `requiere_periquera = True` si hay bebés presentes o si en las observaciones se solicita trona / cuna / periquera.
4. **Anonimización y Cumplimiento GDPR**: Se eliminan números de teléfono, datos bancarios y correos de las observaciones, conservando notas de alergias y protocolos de servicio. Los usuarios son encriptados en hashes alfanuméricos.
5. **Carga en Lote con Integridad**: Carga atómica con sincronización de dimensiones temporales en `Dim_Tiempo` y prevención de duplicados en `Fact_Reservas_Restaurantes`.

---

## 4. 🖥️ Módulos de la Aplicación Web (`app.py`)

La suite analítica en Streamlit se organiza en 7 módulos estratégicos:

1. 📊 **Resumen Ejecutivo & KPIs en Tiempo Real**: Tarjetas de métricas de alto impacto, tendencias temporales y semáforo visual de ocupación por restaurante (🟢 Normal < 75%, 🟡 Alta 75-90%, 🔴 Saturación > 90%).
2. ⏰ **Yield Management & Horarios Críticos**: Mapa de calor por restaurante y turno, identificación automática de Horas Pico vs Horas Valle, y matriz recomendada de configuración de mesas (mesas de 2, 4-6 y grupos >6).
3. 👑 **Segmentación VIP & Familias**: Desglose por niveles de fidelidad (*Privilege Club*, *VIP1*, *VIP2*, *Honeymoon*), conteo de periqueras y **Consola del Maître** con alertas en vivo.
4. 🏨 **Flujo Inter-Hotel (Cross-Dining)**: Diagrama de Sankey interactivo y matriz de migración de huéspedes entre los 5 hoteles del complejo.
5. 🤖 **Modelo Predictivo & Simulador de Demanda**: Algoritmo de Machine Learning (*Random Forest Regressor*) para proyectar la demanda a 7 días y **Simulador de Dotación de Personal** para calcular meseros, cocineros y mesas según la ocupación hotelera esperada.
6. 🔮 **Escalabilidad Futura (Habitaciones & Origen)**: Demostración visual conectada a `Dim_Habitacion` con distribución geográfica de huéspedes y canales de venta.
7. 📥 **Exportación & Reportes**: Descarga de datos filtrados en CSV, reportes ejecutivos formateados en Excel (.xlsx) multihija y resumen ejecutivo para la Dirección de A&B.

---

## 5. 🚀 Instalación y Ejecución Local

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/TU-USUARIO/bahia-principe-bi.git
cd bahia-principe-bi
```

### Paso 2: Crear y Activar Entorno Virtual
```bash
# En Windows:
python -m venv .venv
.venv\Scripts\activate

# En Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Inicializar Base de Datos y Datos Demo
```bash
python etl_pipeline.py
```
> Esto creará la base de datos `bahia_principe_bi.db` con el Esquema en Estrella y generará los archivos de prueba `sample_reservas.csv` y `sample_reservas.xlsx`.

### Paso 5: Lanzar la Aplicación Web
```bash
streamlit run app.py
```
Abre tu navegador en `http://localhost:8501`.

Para levantar el sistema completo en Windows, incluyendo ETL inicial, API y dashboard:
```bat
start_all.bat
```
Puedes comprobar las rutas sin iniciar servicios con `start_all.bat /check` o saltar la carga inicial con `start_all.bat /no-etl`.

---

## 6. 🌐 Despliegue y actualizacion automatica

GitHub almacena el codigo y ejecuta el ETL programado mediante GitHub Actions; no es un servidor web 24/7. Streamlit Community Cloud mantiene el dashboard publicado. La API FastAPI debe publicarse aparte en Render, Railway, Fly.io u otro servicio equivalente si tambien se necesita para Android.

### Paso A: Subir el Proyecto a GitHub
Usa la URL real de tu repositorio en lugar de `URL_DEL_REPOSITORIO` (no se incluyo una URL concreta en la solicitud):
```bash
git init
git add .
git commit -m "feat: Suite Analitica de Reservas Bahia Principe BI"
git branch -M main
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```
No subas `.env`, contrasenas, tokens, archivos Excel reales ni bases de datos locales.

### Paso B: Conectar y Desplegar en Streamlit Cloud
1. Inicia sesión en [share.streamlit.io](https://share.streamlit.io/) con tu cuenta de GitHub.
2. Haz clic en el botón azul **"New app"**.
3. Configura los datos de tu repositorio:
    - **Repository**: el repositorio que acabas de subir
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. En **Advanced settings** -> **Secrets**, configura la misma base PostgreSQL compartida por el ETL:
   - Despliega la pestaña **"Advanced settings"** -> **"Secrets"**.
   - Agrega tu variable de conexión:
     ```toml
     DATABASE_URL = "postgresql://usuario:password@host.region.pooler.supabase.com:6543/postgres"
     ```
5. Haz clic en **"Deploy!"**.
6. La URL publica aparecera en Streamlit Cloud. El servicio puede dormir por inactividad en el plan gratuito; no debe considerarse un SLA 24/7.

### Paso C: Actualizar datos cada tres horas
El workflow `.github/workflows/etl.yml` se ejecuta cada tres horas y tambien permite ejecucion manual. En GitHub, abre **Settings -> Secrets and variables -> Actions** y crea:

- `DATABASE_URL`: la URL PostgreSQL usada tambien por Streamlit.
- `ETL_SOURCE_URL`: URL HTTPS del CSV/XLSX actualizado por el sistema de reservas.
- `ETL_SOURCE_TOKEN`: opcional, si la URL requiere autenticacion Bearer.
- `ETL_SOURCE_FORMAT`: variable opcional con `csv` o `xlsx` cuando la URL no termina en esa extension.

El job falla de forma intencional si `ETL_SOURCE_URL` no existe; asi no reemplaza datos reales por datos demo. GitHub Actions no puede leer directamente un archivo que solo exista en tu PC.

### Paso D: Conectar FastAPI y Android
Publica `main.py` como servicio Python con el comando `uvicorn main:app --host 0.0.0.0 --port $PORT`, configura la misma `DATABASE_URL` y verifica `/health`. Luego coloca la URL HTTPS publica de esa API en la configuracion de la aplicacion Android. Streamlit y FastAPI deben apuntar al mismo PostgreSQL para que todos vean los mismos datos.

---

## 7. 📁 Estructura del Repositorio

```plaintext
bahia-principe-bi/
├── .streamlit/
│   └── config.toml          # Tema visual corporativo Bahía Príncipe (Navy & Gold)
├── config_db.py             # Modelos SQLAlchemy 2.0 y gestión de conexión dual (SQLite/PostgreSQL)
├── etl_pipeline.py          # Pipeline ETL, validación, anonimización y generador mock
├── app.py                   # Aplicación Web Interactiva Streamlit con 7 módulos analíticos
├── requirements.txt         # Dependencias del proyecto
├── sample_reservas.csv      # Archivo de datos de muestra para pruebas manuales de carga
├── sample_reservas.xlsx     # Archivo Excel de muestra con 1,250 reservas
└── README.md                # Documentación técnica y manual de despliegue
```

---

## 8. 👨‍💻 Autor y Créditos
- **Cadena Hotelera**: Bahía Príncipe Hotels & Resorts.
- **División**: Dirección de Alimentos y Bebidas (A&B) & Business Intelligence Corporativo.
- **Tecnologías**: Python 3, Streamlit, SQLAlchemy, PostgreSQL/SQLite, Pandas, Plotly, Scikit-Learn.
