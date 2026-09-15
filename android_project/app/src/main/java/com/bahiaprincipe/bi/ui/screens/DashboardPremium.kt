package com.bahiaprincipe.bi.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.bahiaprincipe.bi.data.model.KpiData
import com.bahiaprincipe.bi.ui.navigation.Screen
import com.bahiaprincipe.bi.ui.theme.BahiaCorporateGreen
import com.bahiaprincipe.bi.ui.theme.BahiaDeepNavy
import com.bahiaprincipe.bi.ui.theme.BahiaGold
import com.bahiaprincipe.bi.ui.theme.BahiaLogoMark
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveViewModel
import com.patrykandpatrick.vico.compose.cartesian.CartesianChartHost
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberBottomAxis
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberStartAxis
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberColumnCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLineCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.rememberCartesianChart
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLineSpec
import com.patrykandpatrick.vico.core.cartesian.HorizontalLayout
import com.patrykandpatrick.vico.compose.cartesian.fullWidth
import com.patrykandpatrick.vico.core.common.shader.DynamicShader
import com.patrykandpatrick.vico.core.cartesian.data.CartesianChartModelProducer
import com.patrykandpatrick.vico.core.cartesian.data.columnSeries
import com.patrykandpatrick.vico.core.cartesian.data.lineSeries

private val CorporateGreen = BahiaCorporateGreen
private val DeepNavy = BahiaDeepNavy
private val GoldAccent = BahiaGold
private val SoftWhite = Color(0xFFF8F9FA)

@Composable
fun DashboardPremium(viewModel: ExecutiveViewModel, navController: NavController) {
    val uiState by viewModel.dashboardState.collectAsState()
    val configuration = LocalConfiguration.current
    val isLandscape = configuration.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE

    Scaffold(
        containerColor = SoftWhite,
        floatingActionButton = {
            FloatingActionButton(
                onClick = { navController.navigate(Screen.AIAssistant.route) },
                containerColor = CorporateGreen,
                contentColor = Color.White,
                shape = CircleShape
            ) {
                Icon(Icons.Default.AutoAwesome, contentDescription = "Consultar IA")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
        ) {
            HeaderSection(uiState.currentUser?.name ?: "Ejecutivo", navController)

            if (isLandscape) {
                LandscapeLayout(uiState, navController)
            } else {
                PortraitLayout(uiState, navController)
            }
        }
    }
}

@Composable
fun HeaderSection(name: String, navController: NavController) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(DeepNavy, CorporateGreen)
                )
            )
            .padding(horizontal = 24.dp, vertical = 18.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
                modifier = Modifier.fillMaxWidth()
            ) {
                BahiaLogoMark(size = 44.dp, accentColor = GoldAccent)
                Spacer(modifier = Modifier.width(16.dp))
                Text(
                    text = "BAHÍA PRÍNCIPE BI",
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.ExtraBold,
                    maxLines = 2
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            Card(
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.12f)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Lightbulb, contentDescription = null, tint = GoldAccent)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "Análisis IA: la ocupación en el Caribe ha subido un 5% respecto a la previsión.",
                        color = Color.White,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}

@Composable
fun PortraitLayout(uiState: com.bahiaprincipe.bi.ui.viewmodel.DashboardUiState, navController: NavController) {
    Column(modifier = Modifier.padding(16.dp)) {
        Text(
            text = "Indicadores Clave",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.ExtraBold,
            modifier = Modifier.padding(vertical = 16.dp)
        )
        
        KpiGrid(uiState.kpis, navController)
        
        Spacer(modifier = Modifier.height(24.dp))
        
        VicoChartCard("Tendencia de Ocupación (%)", uiState.trendData.map { it.value }, true)
        
        Spacer(modifier = Modifier.height(24.dp))
        
        VicoChartCard("Ingresos por Región (M USD)", uiState.revenueData.map { it.value }, false)
        
        Spacer(modifier = Modifier.height(80.dp))
    }
}

@Composable
fun LandscapeLayout(uiState: com.bahiaprincipe.bi.ui.viewmodel.DashboardUiState, navController: NavController) {
    Row(modifier = Modifier.padding(16.dp)) {
        Column(modifier = Modifier.weight(1f)) {
            KpiGrid(uiState.kpis, navController)
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1.2f)) {
            VicoChartCard("Ocupación vs Revenue", uiState.trendData.map { it.value }, true)
            Spacer(modifier = Modifier.height(16.dp))
            VicoChartCard("Distribución de Ingresos", uiState.revenueData.map { it.value }, false)
        }
    }
}

@Composable
fun KpiGrid(kpis: List<KpiData>, navController: NavController) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.heightIn(max = 400.dp)
    ) {
        items(kpis) { kpi ->
            PremiumKpiCard(kpi) {
                // Navegar a la IA con contexto de este KPI
                navController.navigate(Screen.AIAssistant.route)
            }
        }
    }
}


@Composable
fun PremiumKpiCard(kpi: KpiData, onClick: () -> Unit) {
    val kpiColor = remember(kpi.colorHex) { 
        try { Color(android.graphics.Color.parseColor(kpi.colorHex)) } 
        catch (e: Exception) { CorporateGreen } 
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(4.dp, RoundedCornerShape(20.dp))
            .clickable(onClick = onClick)
            .animateContentSize(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .background(kpiColor, CircleShape)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = kpi.title,
                    fontSize = 12.sp,
                    color = Color.Gray,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = kpi.value,
                fontSize = 22.sp,
                fontWeight = FontWeight.Black,
                color = DeepNavy
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 4.dp)
            ) {
                Icon(
                    imageVector = if (kpi.isPositiveTrend) Icons.Default.TrendingUp else Icons.Default.TrendingDown,
                    contentDescription = null,
                    tint = if (kpi.isPositiveTrend) CorporateGreen else Color.Red,
                    modifier = Modifier.size(14.dp)
                )
                Text(
                    text = kpi.trend,
                    fontSize = 11.sp,
                    color = if (kpi.isPositiveTrend) CorporateGreen else Color.Red,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(start = 4.dp)
                )
            }
        }
    }
}

@Composable
fun VicoChartCard(title: String, values: List<Float>, isLine: Boolean) {
    val modelProducer = remember { CartesianChartModelProducer() }
    
    LaunchedEffect(values) {
        if (values.isNotEmpty()) {
            modelProducer.runTransaction {
                if (isLine) {
                    lineSeries { series(values) }
                } else {
                    columnSeries { series(values) }
                }
            }
        }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(260.dp)
            .shadow(8.dp, RoundedCornerShape(24.dp))
            .animateContentSize(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(text = title, fontWeight = FontWeight.ExtraBold, color = DeepNavy, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(16.dp))
            
            CartesianChartHost(
                chart = rememberCartesianChart(
                    if (isLine) {
                        rememberLineCartesianLayer(
                            lines = listOf(
                                rememberLineSpec()
                            )
                        )
                    } else {
                        rememberColumnCartesianLayer()
                    },
                    startAxis = rememberStartAxis(),
                    bottomAxis = rememberBottomAxis(),
                ),
                modelProducer = modelProducer,
                modifier = Modifier.fillMaxSize(),
                horizontalLayout = HorizontalLayout.fullWidth()
            )
        }
    }
}
