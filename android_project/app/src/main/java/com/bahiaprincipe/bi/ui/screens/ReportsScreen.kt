package com.bahiaprincipe.bi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bahiaprincipe.bi.data.model.ReportEntry
import com.bahiaprincipe.bi.ui.theme.BahiaCorporateGreen
import com.bahiaprincipe.bi.ui.theme.BahiaDeepNavy
import com.bahiaprincipe.bi.ui.theme.BahiaGold
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveViewModel

@Composable
fun ReportsScreen(viewModel: ExecutiveViewModel) {
    val uiState by viewModel.reportsState.collectAsState()
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8F9FA))
            .padding(16.dp)
    ) {
        Text(
            text = "Centro de Reportes",
            fontSize = 30.sp,
            fontWeight = FontWeight.ExtraBold,
            color = BahiaDeepNavy
        )
        Text(
            text = "Historial de análisis y reportes semanales",
            fontSize = 14.sp,
            color = Color.Gray,
            modifier = Modifier.padding(bottom = 20.dp)
        )

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier.fillMaxSize()
        ) {
            item {
                Text("Reportes Automáticos", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.Gray)
            }
            items(uiState.reports) { report ->
                ReportCard(report)
            }

            if (uiState.generatedReports.isNotEmpty()) {
                item {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Análisis Personalizados (IA)", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.Gray)
                }
                items(uiState.generatedReports) { generated ->
                    GeneratedReportCard(generated) {
                        openPdf(context, generated.filePath)
                    }
                }
            } else {
                item {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = Color.White,
                        shape = RoundedCornerShape(18.dp),
                        tonalElevation = 0.dp
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(18.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.PictureAsPdf, contentDescription = null, tint = BahiaGold, modifier = Modifier.size(32.dp))
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = "No hay reportes exportados aún.",
                                color = Color.DarkGray,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun GeneratedReportCard(report: com.bahiaprincipe.bi.data.local.GeneratedReportEntity, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(18.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .background(BahiaCorporateGreen.copy(alpha = 0.08f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.PictureAsPdf, contentDescription = null, tint = Color(0xFFB71C1C), modifier = Modifier.size(28.dp))
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(text = report.title, fontWeight = FontWeight.Bold, fontSize = 17.sp, color = BahiaDeepNavy)
                Text(text = "Generado el ${report.date}", fontSize = 13.sp, color = Color.Gray)
            }
            Text("Abrir", color = BahiaCorporateGreen, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        }
    }
}

fun openPdf(context: android.content.Context, filePath: String) {
    try {
        val file = java.io.File(filePath)
        if (!file.exists()) {
            android.widget.Toast.makeText(context, "El PDF no existe o no está disponible en este dispositivo.", android.widget.Toast.LENGTH_SHORT).show()
            return
        }

        val uri = androidx.core.content.FileProvider.getUriForFile(
            context,
            "${context.packageName}.provider",
            file
        )
        val intent = android.content.Intent(android.content.Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/pdf")
            addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(android.content.Intent.createChooser(intent, "Abrir Reporte"))
    } catch (e: Exception) {
        android.widget.Toast.makeText(context, "No hay una app para abrir PDFs. ${e.localizedMessage}", android.widget.Toast.LENGTH_LONG).show()
    }
}

@Composable
fun ReportCard(report: ReportEntry) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        shape = RoundedCornerShape(18.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = report.title, fontWeight = FontWeight.Bold, fontSize = 18.sp, color = BahiaDeepNavy)
                Surface(
                    color = Color(0xFFF1F3F4),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Text(
                        text = report.status,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = BahiaDeepNavy,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.height(10.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(text = "Región: ${report.region}", fontSize = 14.sp, color = Color.DarkGray)
                Text(text = report.date, fontSize = 14.sp, color = Color.DarkGray)
            }
        }
    }
}
