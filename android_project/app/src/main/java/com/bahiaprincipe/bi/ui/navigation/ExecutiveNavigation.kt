package com.bahiaprincipe.bi.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object DashboardPremium : Screen("dashboard_premium", "Dashboard", Icons.Default.AutoGraph)
    object AIAssistant : Screen("ai_assistant", "Asistente AI", Icons.Default.AutoAwesome)
    object Reports : Screen("reports", "Reportes", Icons.Default.Description)
    object Support : Screen("support", "Soporte", Icons.Default.HeadsetMic)
    object Profile : Screen("profile", "Mi Cuenta", Icons.Default.AccountCircle)
    object ReportGenerator : Screen("report_generator", "Exportar", Icons.Default.PictureAsPdf)
}

@Composable
fun ExecutiveBottomBar(
    currentRoute: String?,
    onNavigate: (String) -> Unit
) {
    val items = listOf(
        Screen.DashboardPremium,
        Screen.AIAssistant,
        Screen.Reports,
        Screen.ReportGenerator,
        Screen.Support
    )

    NavigationBar(
        containerColor = Color.White,
        tonalElevation = 8.dp
    ) {
        items.forEach { screen ->
            val selected = currentRoute == screen.route
            NavigationBarItem(
                icon = { 
                    Icon(
                        screen.icon, 
                        contentDescription = screen.title,
                        tint = if (selected) Color(0xFF006B3F) else Color.Gray
                    ) 
                },
                label = { 
                    Text(
                        screen.title, 
                        color = if (selected) Color(0xFF006B3F) else Color.Gray,
                        style = MaterialTheme.typography.labelSmall
                    ) 
                },
                selected = selected,
                onClick = { onNavigate(screen.route) },
                colors = NavigationBarItemDefaults.colors(
                    indicatorColor = Color(0xFF006B3F).copy(alpha = 0.1f)
                )
            )
        }
    }
}
