package com.bahiaprincipe.bi.data.model

data class User(
    val name: String,
    val role: String,
    val email: String,
    val avatarUrl: String? = null
)

data class KpiData(
    val title: String,
    val value: String,
    val trend: String,
    val isPositiveTrend: Boolean,
    val colorHex: String = "#006B3F"
)

data class ReportEntry(
    val id: String,
    val title: String,
    val date: String,
    val region: String,
    val type: String,
    val status: String
)

data class TrendPoint(
    val label: String,
    val value: Float
)

data class ChatMessage(
    val content: String,
    val isUser: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)

data class AiConsultRequest(
    val prompt: String,
    val context: Map<String, Any>? = null
)

data class AiConsultResponse(
    val status: String,
    val summary: String,
    val analysis: String,
    val recommendations: List<String>,
    val risk_level: String
) {
    val riskLevel: String
        get() = risk_level
}
