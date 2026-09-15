package com.bahiaprincipe.bi.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.HeadsetMic
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val CorporateGreen = Color(0xFF006B3F)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SupportScreen() {
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8F9FA))
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        Text(
            text = "Centro de Soporte",
            fontSize = 28.sp,
            fontWeight = FontWeight.ExtraBold,
            color = CorporateGreen
        )
        Text(
            text = "Asistencia técnica exclusiva para directivos.",
            fontSize = 14.sp,
            color = Color.Gray,
            modifier = Modifier.padding(bottom = 32.dp)
        )

        SupportCard(
            title = "Línea Directa",
            subtitle = "+34 900 000 000",
            icon = Icons.Default.Phone,
            onClick = {
                val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:+34900000000"))
                context.startActivity(intent)
            }
        )

        Spacer(modifier = Modifier.height(16.dp))

        SupportCard(
            title = "Email de Soporte BI",
            subtitle = "soporte.bi@bahiaprincipe.com",
            icon = Icons.Default.Email,
            onClick = {
                val intent = Intent(Intent.ACTION_SENDTO).apply {
                    data = Uri.parse("mailto:soporte.bi@bahiaprincipe.com")
                    putExtra(Intent.EXTRA_SUBJECT, "Consulta BI Ejecutivo")
                }
                context.startActivity(intent)
            }
        )

        Spacer(modifier = Modifier.height(16.dp))

        SupportCard(
            title = "Chat de Ayuda en Vivo",
            subtitle = "Conectar con un agente",
            icon = Icons.Default.HeadsetMic,
            onClick = { /* Abrir chat real */ }
        )

        Spacer(modifier = Modifier.height(48.dp))

        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Info, contentDescription = null, tint = CorporateGreen)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Información del Sistema", fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text("Versión de la App: 2.0.0-PRO", fontSize = 12.sp)
                Text("Estado del Servidor: Online", fontSize = 12.sp, color = CorporateGreen)
                Text("Última Sincronización: Hace 5 minutos", fontSize = 12.sp)
            }
        }
    }
}

@Composable
fun SupportCard(title: String, subtitle: String, icon: ImageVector, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                color = CorporateGreen.copy(alpha = 0.1f),
                shape = CircleShape,
                modifier = Modifier.size(48.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(icon, contentDescription = null, tint = CorporateGreen)
                }
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Text(subtitle, color = Color.Gray, fontSize = 14.sp)
            }
        }
    }
}
