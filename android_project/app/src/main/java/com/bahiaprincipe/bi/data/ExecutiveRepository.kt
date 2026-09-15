package com.bahiaprincipe.bi.data

import com.bahiaprincipe.bi.data.local.ChatMessageEntity
import com.bahiaprincipe.bi.data.local.ExecutiveDao
import com.bahiaprincipe.bi.data.local.GeneratedReportEntity
import com.bahiaprincipe.bi.data.local.KpiEntity
import com.bahiaprincipe.bi.data.local.UserEntity
import com.bahiaprincipe.bi.data.model.AiConsultRequest
import com.bahiaprincipe.bi.data.model.AiConsultResponse
import com.bahiaprincipe.bi.data.model.ChatMessage
import com.bahiaprincipe.bi.data.model.KpiData
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.text.SimpleDateFormat
import java.util.*

class ExecutiveRepository(
    private val apiService: ApiService,
    private val executiveDao: ExecutiveDao,
    private val isDemoMode: Boolean = false
) {
    // Escucha cambios locales (Offline-First)
    val allKpis: Flow<List<KpiData>> = executiveDao.getAllKpis().map { entities ->
        entities.map { entity ->
            KpiData(
                title = entity.title,
                value = entity.value,
                trend = entity.trend,
                isPositiveTrend = entity.isPositiveTrend,
                colorHex = entity.colorHex
            )
        }
    }

    // Escucha reportes generados
    val allReports: Flow<List<GeneratedReportEntity>> = executiveDao.getAllReports()

    val chatHistory: Flow<List<ChatMessage>> = executiveDao.getAllChatMessages().map { entities ->
        entities.map { entity -> ChatMessage(entity.content, entity.isUser, entity.timestamp) }
    }

    suspend fun saveGeneratedReport(title: String, path: String, type: String) {
        val report = GeneratedReportEntity(
            title = title,
            date = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date()),
            filePath = path,
            type = type
        )
        executiveDao.insertReport(report)
    }

    suspend fun syncKpis() {
        try {
            val response = apiService.getKpiSummary()
            if (response.isSuccessful) {
                val remoteKpis = response.body() ?: emptyList()
                val entities = remoteKpis.map {
                    KpiEntity(it.title, it.value, it.trend, it.isPositiveTrend, it.colorHex)
                }
                executiveDao.insertKpis(entities)
                
                // Lógica de Alerta Proactiva
                remoteKpis.find { it.title.contains("Ocupación") }?.let { occupancy ->
                    val valueInt = occupancy.value.replace("%", "").toDoubleOrNull() ?: 100.0
                    if (valueInt < 80.0) {
                        // Notificación proactiva
                    }
                }
            }
        } catch (e: Exception) {
            // Log error
        }
    }

    suspend fun login(email: String, pass: String): Result<UserEntity> {
        // Simulación: si no existe el usuario en local, lo creamos para la demo
        val existing = executiveDao.getUser(email)
        return if (existing != null) {
            if (existing.password == pass) Result.success(existing)
            else Result.failure(Exception("Contraseña incorrecta"))
        } else {
            // Demo mode: auto-registro
            val newUser = UserEntity(email, "Ejecutivo Demo", "Director Regional", pass)
            executiveDao.insertUser(newUser)
            Result.success(newUser)
        }
    }

    suspend fun generateAiReportContent(kpis: List<KpiData>): String {
        if (isDemoMode) {
            return generateSimulatedAiReport(kpis)
        }

        val prompt = """
            Actúa como un analista ejecutivo de hotelería para Bahía Príncipe.
            Analiza estos KPIs empresariales y redacta un resumen ejecutivo formal en español:
            ${kpis.joinToString { "${it.title}: ${it.value} (${it.trend})" }}

            Debe incluir:
            1) resumen del rendimiento actual,
            2) riesgos o oportunidades del negocio,
            3) recomendación estratégica para la dirección.
        """.trimIndent()

        return try {
            val request = AiConsultRequest(
                prompt = prompt,
                context = mapOf(
                    "hotel_info" to mapOf(
                        "chain" to "Bahía Príncipe Hotels & Resorts",
                        "property" to "Bahia Principe Grand Bavaro",
                        "region" to "Punta Cana, República Dominicana",
                        "date" to SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                    ),
                    "kpis" to mapOf(
                        "occupancy_rate" to 88.5,
                        "adr_usd" to 215.0,
                        "revpar_usd" to 190.27,
                        "total_revenue_usd" to 142700.0,
                        "food_and_beverage_usd" to 45200.0,
                        "forecast_occupancy_next_7d" to 92.1
                    ),
                    "competitor_compset" to mapOf(
                        "average_occupancy" to 84.0,
                        "average_adr_usd" to 225.0
                    )
                )
            )
            val response = apiService.consultAi(request)
            if (response.isSuccessful) {
                val body = response.body()
                body?.analysis ?: generateSimulatedAiReport(kpis)
            } else {
                generateSimulatedAiReport(kpis)
            }
        } catch (e: Exception) {
            generateSimulatedAiReport(kpis)
        }
    }

    private fun generateSimulatedAiReport(kpis: List<KpiData>): String {
        val occupancy = kpis.find { it.title.contains("Ocupación") }?.value ?: "85%"
        val revenue = kpis.find { it.title.contains("Ingresos") }?.value ?: "$4M"
        
        return """
            El rendimiento operativo actual muestra una solidez notable, con una Ocupación Media del $occupancy y un flujo de Ingresos Totales que alcanza los $revenue. Estos resultados reflejan la efectividad de las campañas de marketing estacional y la fidelización del cliente premium.
            
            Sin embargo, observamos una tendencia que requiere atención en los márgenes operativos. Aunque los ingresos crecen, el ADR (Tarifa Media Diaria) muestra ligeras fluctuaciones, lo que sugiere una presión competitiva en ciertos destinos. Es vital monitorizar el RevPAR para asegurar que el volumen de ocupación no sacrifique la rentabilidad por unidad.
            
            Se recomienda implementar una estrategia de yield management dinámica para el próximo trimestre, priorizando la venta directa sobre intermediarios y ajustando las tarifas en tiempo real según la demanda detectada por nuestro motor de BI. Esto garantizará un cierre de año fiscal récord para Bahía Príncipe.
        """.trimIndent()
    }

    suspend fun getAnyUser(): UserEntity? {
        // Obtenemos el primer usuario para auto-login (simplificación demo)
        return executiveDao.getUser("admin@bahiaprincipe.com") ?: 
               executiveDao.getUser("ejecutivo@bahiaprincipe.com")
    }

    suspend fun persistChatMessage(message: ChatMessage) {
        executiveDao.insertChatMessage(
            ChatMessageEntity(
                content = message.content,
                isUser = message.isUser,
                timestamp = message.timestamp
            )
        )
    }

    suspend fun clearChatHistory() {
        executiveDao.clearChatMessages()
    }

    suspend fun chatWithGemini(history: List<String>, newMessage: String): String {
        if (isDemoMode) return "Simulación: El mercado muestra signos de recuperación en la región seleccionada."

        return try {
            val request = AiConsultRequest(
                prompt = newMessage,
                context = mapOf(
                    "history" to history,
                    "hotel_info" to mapOf(
                        "chain" to "Bahía Príncipe Hotels & Resorts",
                        "property" to "Bahia Principe Grand Bavaro",
                        "region" to "Punta Cana, República Dominicana",
                        "date" to SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                    ),
                    "kpis" to mapOf(
                        "occupancy_rate" to 88.5,
                        "adr_usd" to 215.0,
                        "revpar_usd" to 190.27,
                        "total_revenue_usd" to 142700.0,
                        "food_and_beverage_usd" to 45200.0,
                        "forecast_occupancy_next_7d" to 92.1
                    )
                )
            )

            val response = apiService.consultAi(request)
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    val recs = if (body.recommendations.isNotEmpty()) {
                        "\n\n📋 Recomendaciones Estratégicas:\n" + body.recommendations.joinToString("\n") { "• $it" }
                    } else ""
                    val risk = "\n\n⚠️ Nivel de Riesgo Operativo: ${body.risk_level}"
                    "${body.summary}\n\n${body.analysis}$recs$risk"
                } else {
                    "Sin respuesta del backend."
                }
            } else {
                "No se pudo conectar con la IA del backend (Código: ${response.code()})."
            }
        } catch (e: Exception) {
            "Fallo de conexión IA: ${e.localizedMessage}"
        }
    }
}
