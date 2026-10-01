package com.bahiaprincipe.bi.ui.screens

import android.content.Context
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.os.Environment
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bahiaprincipe.bi.data.model.KpiData
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveViewModel
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val CorporateGreen = Color(0xFF006B3F)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExecutiveReportGenerator(viewModel: ExecutiveViewModel) {
    var selectedReportType by remember { mutableStateOf("Análisis Estratégico IA") }
    var selectedRegion by remember { mutableStateOf("Todas las Regiones") }
    var isGenerating by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val dashboardState by viewModel.dashboardState.collectAsState()
    val reportsState by viewModel.reportsState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Generador de Reportes IA", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CorporateGreen)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            Text(
                text = "Reporte Redactado por IA",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = CorporateGreen
            )

            if (reportsState.aiAnalysis == null && !reportsState.isLoading) {
                Button(
                    onClick = { viewModel.generateExecutiveReport() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.AutoAwesome, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Redactar Análisis con Gemini")
                }
            } else if (reportsState.isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = CorporateGreen)
                Text("Gemini está redactando el informe...", fontSize = 12.sp, color = Color.Gray)
            } else {
                Card(
                    modifier = Modifier.fillMaxWidth().heightIn(max = 300.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F3F4))
                ) {
                    Column(modifier = Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
                        Text("Análisis de IA:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(reportsState.aiAnalysis ?: "", fontSize = 13.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            Button(
                onClick = {
                    isGenerating = true
                    val reportTitle = "Informe Bahía BI - ${SimpleDateFormat("dd/MM", Locale.getDefault()).format(Date())}"
                    generateExecutivePdf(context, dashboardState.kpis, reportsState.aiAnalysis ?: "Análisis manual adjunto.") { success, path ->
                        isGenerating = false
                        if (success) {
                            viewModel.saveReportMetadata(reportTitle, path)
                            Toast.makeText(context, "Reporte guardado en Descargas", Toast.LENGTH_LONG).show()
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = CorporateGreen),
                enabled = !isGenerating && reportsState.aiAnalysis != null
            ) {
                if (isGenerating) {
                    CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                } else {
                    Icon(Icons.Default.Download, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Exportar Reporte a PDF", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

fun generateExecutivePdf(context: Context, kpis: List<KpiData>, aiText: String, onComplete: (Boolean, String) -> Unit) {
    try {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val fileName = "Reporte_IA_Bahia_$timeStamp.pdf"

        val outputDir = context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)
            ?: context.filesDir
        val filePath = File(outputDir, fileName)
        if (!filePath.parentFile?.exists()!!) {
            filePath.parentFile?.mkdirs()
        }

        val pdf = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
        val page = pdf.startPage(pageInfo)
        val canvas = page.canvas
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = android.graphics.Color.rgb(0, 107, 63)
            textSize = 18f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        }
        var y = 48f
        canvas.drawText("BAHÍA PRÍNCIPE BI - INTELIGENCIA ESTRATÉGICA", 40f, y, paint)
        paint.textSize = 10f
        paint.typeface = android.graphics.Typeface.DEFAULT
        paint.color = android.graphics.Color.DKGRAY
        y += 28f
        canvas.drawText("Informe analítico generado por Gemini AI", 40f, y, paint)
        y += 24f
        canvas.drawText("Fecha: ${SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()).format(Date())}", 40f, y, paint)
        y += 32f
        paint.typeface = android.graphics.Typeface.DEFAULT_BOLD
        paint.color = android.graphics.Color.rgb(0, 107, 63)
        canvas.drawText("1. MÉTRICAS CLAVE (KPIs)", 40f, y, paint)
        paint.typeface = android.graphics.Typeface.DEFAULT
        paint.color = android.graphics.Color.DKGRAY
        y += 22f
        kpis.forEach { kpi ->
            canvas.drawText("${kpi.title}: ${kpi.value} (${kpi.trend})", 48f, y, paint)
            y += 18f
        }
        y += 18f
        paint.typeface = android.graphics.Typeface.DEFAULT_BOLD
        paint.color = android.graphics.Color.rgb(0, 107, 63)
        canvas.drawText("2. ANÁLISIS ESTRATÉGICO GENERADO POR IA", 40f, y, paint)
        paint.typeface = android.graphics.Typeface.DEFAULT
        paint.color = android.graphics.Color.DKGRAY
        y += 22f
        aiText.split("\n").forEach { line ->
            if (y > 790f) return@forEach
            canvas.drawText(line.take(92), 48f, y, paint)
            y += 16f
        }
        pdf.finishPage(page)
        FileOutputStream(filePath).use { output -> pdf.writeTo(output) }
        pdf.close()
        
        // Notificar al sistema que hay un nuevo archivo para que aparezca en descargas
        android.media.MediaScannerConnection.scanFile(context, arrayOf(filePath.absolutePath), null, null)
        
        onComplete(true, filePath.absolutePath)
    } catch (e: Exception) {
        e.printStackTrace()
        onComplete(false, "")
    }
}

@Composable
fun ReportOptionCard(title: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(title, fontSize = 12.sp, color = Color.Gray)
                Text(value, fontSize = 16.sp, fontWeight = FontWeight.Medium)
            }
            Icon(icon, contentDescription = null, tint = CorporateGreen)
        }
    }
}
