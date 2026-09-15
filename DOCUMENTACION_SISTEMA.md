# 🏖️🍽️ Bahía Príncipe Hotels & Resorts
## Manual Técnico y Documentación Integral del Sistema de Business Intelligence y Analítica Predictiva

---

## 1. Ficha Técnica y Resumen Ejecutivo

| Parámetro | Detalle |
| :--- | :--- |
| **Nombre del Sistema** | Sistema Analítico Operativo y Predictivo de Reservas para Restaurantes de Especialidad |
| **Organización** | Bahía Príncipe Hotels & Resorts |
| **División Operativa** | Dirección de Alimentos y Bebidas (A&B) & Business Intelligence |
| **Alcance Operativo** | Complejo hotelero con **5 Hoteles** y **20 Restaurantes de Especialidad** |
| **Arquitectura de Datos** | Data Warehouse relacional bajo **Esquema en Estrella (Star Schema)** |
| **Stack Tecnológico** | Python 3.12, Streamlit, SQLAlchemy 2.0, PostgreSQL/SQLite, Pandas, Plotly, Scikit-Learn, OpenPyXL |
| **Disponibilidad y Despliegue** | Diseñado para operar **24/7 sin coste de servidor** en **Streamlit Community Cloud** conectado a **GitHub** |
| **Cumplimiento y Privacidad** | Anonimización pasiva GDPR para supresión de datos personales identificables (PII) |

### Objetivo Estratégico del Proyecto
Optimizar la toma de decisiones en la gestión de reservas de cenas de especialidad en los resorts todo incluido de Bahía Príncipe mediante:
1. **Mitigación de saturación en horarios pico** y balanceo de comensales hacia horarios valle (Yield Management).
2. **Monitoreo y control del flujo Cross-Dining**, identificando el intercambio de comensales entre hoteles y restaurantes "imán".
3. **Atención prioritaria y protocolar** para comensales VIP (VIP1, VIP2, Privilege Club) y dimensionamiento de mobiliario infantil (periqueras).
4. **Proyección de demanda futura mediante Machine Learning** y simulación interactiva de dotación de personal (meseros y cocineros).

---

## 2. Estructura de Archivos del Proyecto

El repositorio está organizado con una arquitectura modular y desacoplada:

```plaintext
bahia-principe-bi/
├── .streamlit/
│   └── config.toml               # Configuración de tema visual (Navy #0B1528, Oro #C5A059) y servidor
├── .venv/                        # Entorno virtual aislado de Python con dependencias instaladas
├── config_db.py                  # Modelos SQLAlchemy 2.0 para el Esquema en Estrella y gestión dual SQLite/PostgreSQL
├── etl_pipeline.py               # Pipeline ETL automatizado, validación, anonimización y generador de datos mock
├── app.py                        # Aplicación web interactiva Streamlit con 7 módulos analíticos
├── requirements.txt              # Dependencias fijadas del proyecto
├── sample_reservas.csv           # Dataset de muestra con 1,250 registros para pruebas de carga
├── sample_reservas.xlsx          # Dataset de muestra en Excel multihija con formato estándar
├── test_suite.py                 # Suite de pruebas unitarias automatizadas con unittest
├── bahia_principe_bi.db          # Base de datos SQLite local inicializada con datos demo
├── .gitignore                    # Exclusiones de Git (.venv, __pycache__, logs)
├── README.md                     # Guía rápida y manual de despliegue en la nube
└── DOCUMENTACION_SISTEMA.md      # Manual técnico exhaustivo (este documento)
```

---

## 3. Arquitectura de Base de Datos: Esquema en Estrella (Star Schema)

El almacén analítico desacopla los atributos descriptivos en **Tablas de Dimensiones** y centraliza las transacciones cuantitativas en una **Tabla de Hechos Central**.

```mermaid
erDiagram
    Dim_Hotel ||--o{ Dim_Restaurante : "ubica físicamente"
    Dim_Hotel ||--o{ Fact_Reservas_Restaurantes : "hospeda al comensal"
    Dim_Hotel ||--o{ Dim_Habitacion : "alberga habitaciones"
    Dim_Restaurante ||--o{ Fact_Reservas_Restaurantes : "recibe reserva"
    Dim_Horario ||--o{ Fact_Reservas_Restaurantes : "define turno"
    Dim_Tipo_Atencion ||--o{ Fact_Reservas_Restaurantes : "clasifica comensal"
    Dim_Tiempo ||--o{ Fact_Reservas_Restaurantes : "fecha servicio"
    Dim_Habitacion ||--o{ Fact_Reservas_Restaurantes : "cuarto asociado (futuro)"

    Fact_Reservas_Restaurantes {
        int id_reserva PK "Identificador único original de la reserva"
        date id_fecha FK "Fecha de servicio (-> Dim_Tiempo)"
        varchar id_restaurante FK "Código de restaurante (-> Dim_Restaurante)"
        int id_hotel_hospedaje FK "Hotel de hospedaje del huésped (-> Dim_Hotel)"
        varchar id_tipo_atencion FK "Categoría protocolar (-> Dim_Tipo_Atencion)"
        varchar id_horario FK "Turno y franja horaria (-> Dim_Horario)"
        int id_habitacion FK "Clave escalable al PMS hotelero (-> Dim_Habitacion)"
        int num_adultos "Número de adultos"
        int num_ninos "Número de niños"
        int num_bebes "Número de bebés"
        int total_pax "Comensales totales (#Adultos + #Niños + #Bebés)"
        float habs_invitadas "Habitaciones invitadas asociadas"
        boolean es_cross_dining "True si Hotel Hospedaje != Hotel Restaurante"
        boolean requiere_periquera "True si hay bebés o solicitud de trona"
        text observaciones_limpias "Notas operativas sin datos sensibles"
        datetime fecha_carga_etl "Marca temporal de inserción UTC"
    }

    Dim_Hotel {
        int id_hotel PK "ID canónico: 1, 4, 10, 16, 21"
        varchar nombre_hotel "Nombre oficial del hotel"
        varchar codigo_origen UK "Código transaccional: BPG, AP3, TOI, BPS, BPB"
        varchar categoria "Grand o Luxury"
    }

    Dim_Restaurante {
        varchar id_restaurante PK "Código único: DPI, MIK, TEQ, etc."
        varchar nombre_restaurante "Nombre comercial del restaurante"
        varchar especialidad "Cocina: Gourmet, Japonesa, Mexicana, etc."
        int id_hotel_ubicacion FK "Hotel donde radica físicamente"
        int capacidad_maxima_pax "Capacidad instalada de comensales"
    }

    Dim_Horario {
        varchar id_horario PK "T1_1730, T2_1930, etc."
        int turno "Turno operativo: 1, 2, 3"
        varchar horario_texto "Horario impreso: '17:30 - 19:00'"
        varchar franja_horaria "Descripción de franja: Temprano, Central, Nocturno"
    }

    Dim_Tipo_Atencion {
        varchar id_tipo_atencion PK "STANDARD, VIP1, VIP2, GEB06, ATE01, etc."
        varchar categoria_atencion "Standard, VIP, Fidelidad, Especial"
        int prioridad_servicio "1 (Máxima) a 4 (Estándar)"
    }

    Dim_Tiempo {
        date id_fecha PK "Fecha en formato YYYY-MM-DD"
        int anio "Año"
        int mes "Mes (1 a 12)"
        int dia "Día del mes"
        varchar dia_semana "Lunes a Domingo"
        boolean es_fin_de_semana "True para Viernes, Sábado y Domingo"
        varchar temporada "Alta, Media o Baja"
    }

    Dim_Habitacion {
        int id_habitacion PK "ID habitación"
        varchar numero_habitacion "Número físico de cuarto"
        int id_hotel FK "Hotel al que pertenece"
        varchar tipo_categoria_cuarto "Junior Suite, Presidential Suite, etc."
        varchar pais_origen_agrupado "País de residencia anonimizado"
        varchar segmento_mercado "Directo Web, Privilege Club, OTA, Mayorista"
    }
```

---

## 4. Catálogo del Complejo Hotelero: 5 Hoteles y 20 Restaurantes

| Hotel | Código | Categoría | ID | Restaurantes de Especialidad | Especialidad Culinaria | Capacidad |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: |
| **Grand Tulum** | `BPG` | Grand | 1 | **DPI**: Don Pablo Gourmet Cuisine<br>**TEQ**: Tequila Mexican Experience<br>**HIN**: Thali Flavors of India<br>**POR**: Portofino Trattoria | Gourmet / Francesa<br>Mexicana Auténtica<br>India / Especias<br>Italiana Tradicional | 110 pax<br>140 pax<br>95 pax<br>130 pax |
| **Luxury Akumal** | `AP3` | Luxury | 4 | **MIK**: Mikado Teppanyaki & Sushi<br>**FRU**: Frutos del Mar Seafood<br>**DOL**: Dolce Vita Ristorante<br>**ARK**: Arlequín Haute Cuisine | Japonesa / Teppanyaki<br>Mariscos & Pescados<br>Italiana Gourmet<br>Cocina de Autor | 120 pax<br>105 pax<br>115 pax<br>90 pax |
| **Grand Coba** | `TOI` | Grand | 10 | **ROD**: Le Gourmet Rodizio Grill<br>**MED**: Mediterráneo Coastal Bistro<br>**KUB**: Ku'uk Mayan Gastronomy<br>**OAS**: Oasis Rodizio & Smokehouse | Cortes & Brasileña<br>Mediterránea Fusión<br>Fusión Maya Peninsular<br>Carnes & Ahumados | 150 pax<br>130 pax<br>110 pax<br>140 pax |
| **Luxury Sian Ka'an** | `BPS` | Luxury (Adults Only) | 16 | **ALB**: Alux Cenote Experience<br>**TAK**: Takara Pan-Asian Gourmet<br>**YUC**: Cenote Maya Yucateco<br>**GRA**: Gran Tortuga Rodizio Prime | Cocina Sensorial Vanguardia<br>Asiática Pan-Pacífico<br>Regional Yucateca<br>Brasileña Prime | 85 pax<br>95 pax<br>90 pax<br>100 pax |
| **Grand Bouganville** | `BPB` | Grand | 21 | **CAR**: El Pescador Caribeño<br>**BEA**: Bella Italia Oven & Pasta<br>**GOU**: Bouganville Gourmet Lounge<br>**LOS**: Los Corales Prime Steakhouse | Pescados Caribeños Fusión<br>Italiana Rústica<br>Internacional de Autor<br>Cortes Finos & Parrilla | 125 pax<br>135 pax<br>105 pax<br>145 pax |

---

## 5. Pipeline ETL (`etl_pipeline.py`): Reglas de Procesamiento

El pipeline automatizado recibe archivos `.xlsx` o `.csv` con las siguientes columnas transaccionales del sistema de reservas del resort:
`['Remarks', 'Actions', 'Cargado', 'Obs.', 'Cross', 'Atención', '#Adultos', '#Niños', '#Bebés', 'Nº Habs. Invitadas', 'Fecha Servicio', 'Servicio', 'Turno', 'Horario', 'Id', 'Usuario', 'Origen', 'Hotel', 'Hotel Res.']`

### Algoritmos y Reglas de Negocio Implementadas:
1. **Cálculo de Pax**:
   $$\text{total\_pax} = \max(1, \text{\#Adultos}) + \max(0, \text{\#Niños}) + \max(0, \text{\#Bebés})$$
   Se asegura que ninguna reserva quede con cero comensales si hay adultos no declarados.
2. **Determinación de Cross-Dining**:
   $$\text{es\_cross\_dining} = (\text{Hotel} \neq \text{Hotel Res.})$$
   Indica si el huésped cena en un hotel diferente al hotel donde duerme.
3. **Detección de Mobiliario Infantil (Periqueras)**:
   $$\text{requiere\_periquera} = (\text{\#Bebés} > 0) \lor \text{regex\_match}(\text{"periquera|trona|bebe|cuna"}, \text{Remarks})$$
4. **Anonimización Pasiva GDPR**:
   - Se procesan las columnas `Usuario` generando hashes alfanuméricos irreversibles (`USR_XXXX`).
   - Se sanean las columnas `Remarks` y `Obs.` eliminando números de teléfono, tarjetas de crédito y correos electrónicos mediante expresiones regulares.
5. **Carga en Lote de Alto Rendimiento**:
   - Uso de `session.bulk_insert_mappings()` con manejo de duplicados por bloques, reduciendo el tiempo de procesamiento de 1,250 filas de más de 30 segundos a menos de **0.1 segundos**.

---

## 6. Módulos de la Aplicación Web en Streamlit (`app.py`)

La aplicación interactiva está diseñada con una interfaz ejecutiva y dividida en **7 módulos estratégicos**:

### 📊 1. Resumen Ejecutivo y KPIs en Tiempo Real
- **Tarjetas de Alto Impacto**: Total de Reservas, Total de Comensales (Pax), Relación Adultos vs Menores, Promedio de Comensales por Mesa, Tasa de Cross-Dining (%) y Porcentaje de Ocupación Global A&B.
- **Semáforo Visual de Ocupación por Restaurante**:
  - 🟢 **Normal (< 75%)**: Operación fluida.
  - 🟡 **Alta (75% - 90%)**: Atención de sala y advertencia de mesas.
  - 🔴 **Saturación (> 90%)**: Alerta de sobreventa y cuello de botella.
- **Gráficos Plotly**: Tendencia diaria con línea de reservas y barras de comensales, más gráfico de dona con cuota de mercado por hotel.

### ⏰ 2. Yield Management y Horarios Críticos
- **Heatmap de Ocupación**: Matriz visual de Restaurante vs Franja Horaria.
- **Detección de Horas Pico y Valle**: Identifica automáticamente el turno con mayor sobrecarga (ej. Turno 2: 19:30 - 21:00 con >50% de la demanda) y la hora valle con mayor capacidad ociosa (Turno 3: 21:30 - 23:00) para incentivar redistribución.
- **Matriz Recomendada de Configuración de Mesas**: Sugiere el armado óptimo de sala en mesas para parejas (2 pax), familiares pequeñas (3-4 pax), familiares grandes (5-6 pax) y mesas imperiales (>6 pax).

### 👑 3. Segmentación VIP y Familias
- **Donut Chart de Niveles de Atención**: Desglose porcentual entre Standard, VIP (VIP1, VIP2, GEB06), Fidelidad (Bahia Privilege Club) y Especial (Luna de Miel, Cumpleaños).
- **Control de Mobiliario Infantil**: Conteo global de bebés/niños y tabla de requerimiento de periqueras por restaurante para pre-montaje de sala.
- **Consola Operativa del Maître**: Tabla interactiva filtrada en tiempo real con los clientes de atención prioritaria, mostrando hora de llegada, hotel de origen y requerimientos especiales o alergias alimentarias sanitizadas.

### 🏨 4. Flujo Inter-Hotel (Cross-Dining)
- **Diagrama de Sankey Interactivo**: Visualización gráfica del flujo de personas desde el hotel donde se alojan (nodo de origen) hacia el hotel donde cenan (nodo de destino).
- **Matriz de Movilidad Inter-Hotel**: Heatmap cruzado de comensales importados/exportados entre los 5 hoteles.
- **Restaurantes "Imán"**: Ranking de los restaurantes que atraen el mayor volumen de comensales provenientes de otros hoteles.

### 🤖 5. Modelo Predictivo y Simulador de Demanda
- **Machine Learning con Scikit-Learn (`RandomForestRegressor`)**:
  - Entrenado con variables de estacionalidad: mes, día de la semana, fin de semana, turno, capacidad máxima y restaurante.
  - Métricas de rendimiento: Coeficiente de determinación ($R^2$) y Error Medio Absoluto (MAE en pax/turno).
  - Proyección de afluencia a 7 días vista.
- **Simulador Interactivo de Capacidad y Dotación de Personal (Staffing Simulator)**:
  - Sliders interactivos de ocupación proyectada (50% a 100%), ratio comensales por mesero (default: 14) y ratio de cocina (default: 25).
  - Cálculo instantáneo de: comensales esperados, meseros requeridos en sala, cocineros/stewards necesarios y diagnóstico de riesgo operativo.

### 🔮 6. Escalabilidad Futura (Dim_Habitacion)
- Módulo preparado para enlazar con el PMS hotelero (Opera / Protel) mediante `id_habitacion`.
- Demostración analítica con procedencia geográfica (EE.UU., Canadá, España, México, etc.), tipo de suite y canal de reserva.

### 📥 7. Exportación y Reportes
- Vista previa de datos filtrados.
- Descarga en formato **CSV**.
- Descarga de **Reporte Ejecutivo Multihija en Excel (.xlsx)** con hojas formateadas: `Reservas_Filtradas`, `Resumen_Restaurantes` y `Alertas_Maitre`.
- Resumen ejecutivo en texto listo para copiar o remitir por correo al Director General de A&B.

---

## 7. Resultados de las Pruebas y Validación (`test_suite.py`)

La suite de pruebas automatizadas ejecuta 4 baterías de pruebas con `unittest`:
```
....
----------------------------------------------------------------------
Ran 4 tests in 0.673s

OK
```

1. `test_01_star_schema_tables_exist`: Valida que las 6 dimensiones y la tabla de hechos existan con las claves foráneas correctas.
2. `test_02_etl_metric_calculations`: Valida las fórmulas de `total_pax`, `es_cross_dining`, detección de `requiere_periquera` y la anonimización de teléfonos.
3. `test_03_load_from_sample_files`: Valida la carga e idempotencia procesando archivos `.csv` y `.xlsx`.
4. `test_04_machine_learning_pipeline`: Valida el entrenamiento y la capacidad predictiva del modelo de Machine Learning.
5. **Verificación de Servidor Web**: La aplicación Streamlit fue ejecutada en modo headless y respondió satisfactoriamente con **`HTTP Status: 200`** en `http://localhost:8501`.

---

## 8. Guía de Ejecución Local y Despliegue en la Nube

### Ejecución en Entorno Local (Windows / Mac / Linux):
```powershell
# 1. Navegar al directorio del proyecto
cd c:\Users\Informatica\Desktop\bahia-principe-bi

# 2. Activar el entorno virtual
.venv\Scripts\activate      # En Windows PowerShell
source .venv/bin/activate   # En Linux / macOS

# 3. Lanzar la aplicación
streamlit run app.py
```
Abre tu navegador en `http://localhost:8501`.

### Despliegue Gratuito 24/7 en Streamlit Community Cloud:
1. Sube tu proyecto a un repositorio de **GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: Sistema Analitico Bahía Príncipe BI"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/bahia-principe-bi.git
   git push -u origin main
   ```
2. Entra en [share.streamlit.io](https://share.streamlit.io/) con tu usuario de GitHub.
3. Presiona el botón **"New app"** y selecciona:
   - **Repository**: `TU_USUARIO/bahia-principe-bi`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. *(Opcional - Base de datos PostgreSQL en la nube)*: En **Advanced settings** -> **Secrets**, agrega tu cadena de conexión (Supabase, Neon, Render):
   ```toml
   DATABASE_URL = "postgresql://usuario:password@ep-host.region.aws.neon.tech/neondb"
   ```
   *Si no agregas esta variable, la app funcionará automáticamente con SQLite local de forma autónoma.*
5. Haz clic en **"Deploy!"**. En menos de 2 minutos estará disponible con enlace público permanente.

---

## 9. Arquitectura Multi-Database e Introspección Semántica (Próxima Evolución)

Para habilitar conexión agnóstica a cualquier base de datos externa de la cadena (MySQL, SQL Server, PostgreSQL, Snowflake) sin nombres de columnas rígidos, se ha diseñado la siguiente arquitectura de dos módulos complementarios:
- **`db_engine.py`**: Gestor de conexiones universal con prueba de ping en milisegundos y fallback automático a SQLite/archivos locales.
- **`schema_inspector.py`**: Motor de introspección semántica con expresiones regulares para mapear cualquier denominación de columna (`Adults`, `Service_Date`, `Outlet`, `Propiedad`) al modelo canónico en estrella en memoria, con auditoría de anonimización GDPR.
