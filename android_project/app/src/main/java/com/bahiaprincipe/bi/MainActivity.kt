package com.bahiaprincipe.bi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.bahiaprincipe.bi.data.ApiService
import com.bahiaprincipe.bi.data.ExecutiveRepository
import com.bahiaprincipe.bi.data.local.LocalDatabase
import com.bahiaprincipe.bi.ui.navigation.ExecutiveBottomBar
import com.bahiaprincipe.bi.ui.navigation.Screen
import com.bahiaprincipe.bi.ui.screens.*
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveAssistantViewModel
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveViewModel
import com.bahiaprincipe.bi.util.NotificationService
import retrofit2.Retrofit
import androidx.compose.ui.platform.LocalContext
import retrofit2.converter.gson.GsonConverterFactory

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat

const val BASE_URL = "http://192.168.1.233:8000/" // IP local de la PC para conexión desde celular real

class MainActivity : ComponentActivity() {
    
    // Manual DI
    private val database by lazy { LocalDatabase.getDatabase(this) }
    val notificationService by lazy { NotificationService(this) }
    
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        // Manejar permisos si es necesario
    }

    private val apiService: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    private val repository: ExecutiveRepository by lazy {
        ExecutiveRepository(apiService, database.executiveDao(), false)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        checkAndRequestPermissions()

        setContent {
            val factory = remember { ExecutiveViewModelFactory(repository, notificationService) }
            val viewModel: ExecutiveViewModel = viewModel(factory = factory)
            val dashboardState by viewModel.dashboardState.collectAsState()

            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = androidx.compose.ui.graphics.Color(0xFF006B3F), // Verde Corporativo
                    secondary = androidx.compose.ui.graphics.Color(0xFF666666),
                    onPrimary = androidx.compose.ui.graphics.Color.White
                )
            ) {
                if (!dashboardState.isLoggedIn) {
                    LoginScreen(viewModel = viewModel)
                } else {
                    MainAppScaffold(repository, viewModel, factory)
                }
            }
        }
    }

    private fun checkAndRequestPermissions() {
        val permissionsToRequest = mutableListOf(Manifest.permission.INTERNET)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissionsToRequest.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        
        val permissionsNotGranted = permissionsToRequest.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (permissionsNotGranted.isNotEmpty()) {
            requestPermissionLauncher.launch(permissionsNotGranted.toTypedArray())
        }
    }
}

class ExecutiveViewModelFactory(
    private val repository: ExecutiveRepository,
    private val notificationService: NotificationService
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ExecutiveViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ExecutiveViewModel(repository, notificationService) as T
        }
        if (modelClass.isAssignableFrom(ExecutiveAssistantViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ExecutiveAssistantViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScaffold(
    repository: ExecutiveRepository, 
    viewModel: ExecutiveViewModel,
    factory: ExecutiveViewModelFactory
) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("BAHÍA PRÍNCIPE BI", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold) },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        },
        bottomBar = {
            ExecutiveBottomBar(
                currentRoute = currentRoute,
                onNavigate = { route ->
                    navController.navigate(route) {
                        popUpTo(navController.graph.startDestinationId)
                        launchSingleTop = true
                    }
                }
            )
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.DashboardPremium.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.DashboardPremium.route) {
                DashboardPremium(viewModel, navController)
            }
            composable(Screen.AIAssistant.route) {
                val assistantViewModel: ExecutiveAssistantViewModel = viewModel(factory = factory)
                AIAssistantScreen(assistantViewModel)
            }
            composable(Screen.ReportGenerator.route) {
                ExecutiveReportGenerator(viewModel)
            }
            composable(Screen.Reports.route) {
                ReportsScreen(viewModel)
            }
            composable(Screen.Support.route) {
                SupportScreen()
            }
            composable(Screen.Profile.route) {
                // Pantalla de Perfil simple
                Surface(modifier = Modifier.padding(16.dp)) {
                    val state by viewModel.dashboardState.collectAsState()
                    Column {
                        Text("Perfil Ejecutivo", style = MaterialTheme.typography.headlineMedium)
                        Text("Nombre: ${state.currentUser?.name ?: ""}")
                        Text("Rol: ${state.currentUser?.role ?: ""}")
                        Text("Email: ${state.currentUser?.email ?: ""}")
                    }
                }
            }
        }
    }
}

