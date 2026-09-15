package com.bahiaprincipe.bi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bahiaprincipe.bi.ui.theme.BahiaCorporateGreen
import com.bahiaprincipe.bi.ui.theme.BahiaDeepNavy
import com.bahiaprincipe.bi.ui.theme.BahiaGold
import com.bahiaprincipe.bi.ui.theme.BahiaLogoMark
import com.bahiaprincipe.bi.ui.theme.BahiaWordmark
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveViewModel

@Composable
fun LoginScreen(viewModel: ExecutiveViewModel) {
    val uiState by viewModel.dashboardState.collectAsState()
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFFF4F0E7),
                        Color(0xFFEFE9DF),
                        Color(0xFFE7E2D7)
                    )
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            BahiaLogoMark(
                modifier = Modifier.padding(bottom = 18.dp),
                size = 110.dp,
                accentColor = BahiaGold
            )

            BahiaWordmark(
                modifier = Modifier.padding(bottom = 26.dp),
                large = true,
                textColor = BahiaDeepNavy,
                accentColor = BahiaGold
            )

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.8f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    OutlinedTextField(
                        value = username,
                        onValueChange = { username = it },
                        label = { Text("Usuario (Email)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(16.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = BahiaCorporateGreen,
                            focusedLabelColor = BahiaCorporateGreen,
                            unfocusedBorderColor = Color(0xFFD8D6D2)
                        )
                    )

                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("Contraseña") },
                        visualTransformation = PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(16.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = BahiaCorporateGreen,
                            focusedLabelColor = BahiaCorporateGreen,
                            unfocusedBorderColor = Color(0xFFD8D6D2)
                        )
                    )

                    if (uiState.loginError != null) {
                        Text(
                            text = uiState.loginError!!,
                            color = Color(0xFFB3261E),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }

                    Button(
                        onClick = { viewModel.login(username, password) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        enabled = !uiState.isLoading,
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = BahiaCorporateGreen)
                    ) {
                        if (uiState.isLoading) {
                            CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                        } else {
                            Text("ACCESO EJECUTIVO", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            TextButton(onClick = { /* Soporte técnico */ }, modifier = Modifier.padding(top = 18.dp)) {
                Text("¿Problemas con el acceso?", color = BahiaDeepNavy, fontWeight = FontWeight.Medium)
            }
        }
    }
}
