package com.bahiaprincipe.bi.ui.viewmodel

import androidx.compose.ui.graphics.Color
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bahiaprincipe.bi.data.ExecutiveRepository
import com.bahiaprincipe.bi.data.local.GeneratedReportEntity
import com.bahiaprincipe.bi.data.model.*
import com.bahiaprincipe.bi.util.NotificationService
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class DashboardUiState(
    val isLoading: Boolean = false,
    val kpis: List<KpiData> = emptyList(),
    val trendData: List<TrendPoint> = emptyList(),
    val revenueData: List<TrendPoint> = emptyList(),
    val currentUser: User? = null,
    val loginError: String? = null,
    val isLoggedIn: Boolean = false,
    val kpiOrder: List<String> = emptyList()
)

data class ReportsUiState(
    val isLoading: Boolean = false,
    val reports: List<ReportEntry> = emptyList(),
    val generatedReports: List<GeneratedReportEntity> = emptyList(),
    val aiAnalysis: String? = null
)

class ExecutiveViewModel(
    private val repository: ExecutiveRepository,
    private val notificationService: NotificationService
) : ViewModel() {

    private val _dashboardState = MutableStateFlow(DashboardUiState())
    val dashboardState: StateFlow<DashboardUiState> = _dashboardState.asStateFlow()

    private val _reportsState = MutableStateFlow(ReportsUiState())
    val reportsState: StateFlow<ReportsUiState> = _reportsState.asStateFlow()

    init {
        checkAutoLogin()
        
        // Observar KPIs desde la base de datos local
        repository.allKpis.onEach { kpis ->
            if (kpis.isEmpty()) {
                loadMockData() // Fallback si está vacío
            } else {
                _dashboardState.value = _dashboardState.value.copy(kpis = kpis)
                
                // Alerta si la ocupación es crítica
                kpis.find { it.title.contains("Ocupación") }?.let { occupancy ->
                    val valDouble = occupancy.value.replace("%", "").toDoubleOrNull() ?: 100.0
                    if (valDouble < 85.0) {
                        notificationService.showExecutiveAlert("Alerta de Ocupación", "La ocupación ha bajado del 85%. Se recomienda revisar estrategia.")
                    }
                }
            }
        }.launchIn(viewModelScope)

        // Observar Reportes desde la DB
        repository.allReports.onEach { reports ->
            _reportsState.value = _reportsState.value.copy(generatedReports = reports)
        }.launchIn(viewModelScope)

        loadDashboardData()
        loadReportsData()
    }

    fun saveReportMetadata(title: String, path: String) {
        viewModelScope.launch {
            repository.saveGeneratedReport(title, path, "MANUAL")
        }
    }

    fun login(email: String, pass: String) {
        viewModelScope.launch {
            _dashboardState.value = _dashboardState.value.copy(isLoading = true, loginError = null)
            val result = repository.login(email, pass)
            result.onSuccess { userEntity ->
                _dashboardState.value = _dashboardState.value.copy(
                    isLoading = false,
                    isLoggedIn = true,
                    currentUser = User(userEntity.name, userEntity.role, userEntity.email)
                )
            }.onFailure { error ->
                _dashboardState.value = _dashboardState.value.copy(
                    isLoading = false,
                    loginError = error.message
                )
            }
        }
    }

    fun loadDashboardData() {
        viewModelScope.launch {
            repository.syncKpis()
            
            // Datos de tendencia simulados (esto vendría del ETL en el futuro)
            val mockTrends = listOf(
                TrendPoint("Ene", 75f), TrendPoint("Feb", 82f), TrendPoint("Mar", 88f),
                TrendPoint("Abr", 85f), TrendPoint("May", 92f), TrendPoint("Jun", 89f)
            )

            val mockRevenue = listOf(
                TrendPoint("Ene", 120f), TrendPoint("Feb", 150f), TrendPoint("Mar", 140f),
                TrendPoint("Abr", 180f), TrendPoint("May", 210f), TrendPoint("Jun", 205f)
            )

            _dashboardState.value = _dashboardState.value.copy(
                trendData = mockTrends,
                revenueData = mockRevenue
            )
        }
    }

    fun reorderKpis(fromIndex: Int, toIndex: Int) {
        val currentKpis = _dashboardState.value.kpis.toMutableList()
        if (fromIndex in currentKpis.indices && toIndex in currentKpis.indices) {
            val item = currentKpis.removeAt(fromIndex)
            currentKpis.add(toIndex, item)
            _dashboardState.value = _dashboardState.value.copy(kpis = currentKpis)
        }
    }

    private fun checkAutoLogin() {
        viewModelScope.launch {
            val user = repository.getAnyUser()
            if (user != null) {
                _dashboardState.value = _dashboardState.value.copy(
                    isLoggedIn = true,
                    currentUser = User(user.name, user.role, user.email)
                )
            }
        }
    }

    private fun loadMockData() {
        val mockKpis = listOf(
            KpiData("Ingresos Totales", "$4.2M", "+12.5%", true, "#006B3F"),
            KpiData("Ocupación Media", "88.2%", "+2.1%", true, "#2E7D32"),
            KpiData("ADR (Tarifa)", "$245", "-1.5%", false, "#C62828"),
            KpiData("RevPAR", "$216", "+3.4%", true, "#1565C0")
        )
        _dashboardState.value = _dashboardState.value.copy(kpis = mockKpis)
    }

    fun generateExecutiveReport() {
        viewModelScope.launch {
            _reportsState.value = _reportsState.value.copy(isLoading = true)
            val analysis = repository.generateAiReportContent(_dashboardState.value.kpis)
            _reportsState.value = _reportsState.value.copy(
                isLoading = false,
                aiAnalysis = analysis
            )
        }
    }

    fun loadReportsData() {
        viewModelScope.launch {
            _reportsState.value = _reportsState.value.copy(isLoading = true)

            val mockReports = listOf(
                ReportEntry("1", "Cierre Mensual Agosto", "2026-09-01", "Global", "Financiero", "Completado"),
                ReportEntry("2", "Previsión Q4 2026", "2026-08-25", "Caribe", "Estratégico", "En Revisión"),
                ReportEntry("3", "Análisis Competitivo Semanal", "2026-09-05", "España", "Mercado", "Nuevo")
            )

            _reportsState.value = _reportsState.value.copy(
                isLoading = false,
                reports = mockReports
            )
        }
    }
}
