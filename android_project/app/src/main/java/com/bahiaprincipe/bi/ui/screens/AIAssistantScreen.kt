package com.bahiaprincipe.bi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bahiaprincipe.bi.data.model.ChatMessage
import com.bahiaprincipe.bi.ui.viewmodel.ExecutiveAssistantViewModel

private val CorporateGreen = Color(0xFF006B3F)
private val DeepNavy = Color(0xFF003366)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AIAssistantScreen(viewModel: ExecutiveAssistantViewModel) {
    val messages by viewModel.chatMessages.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    val quickQuestions = listOf(
        "¿Previsión ocupación Q4?",
        "¿Por qué bajó el ADR?",
        "Resumen de ingresos hoy",
        "Comparativa vs año pasado"
    )

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF0F2F5))
    ) {
        // Chat Header Premium
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.horizontalGradient(listOf(DeepNavy, CorporateGreen)),
                    shape = RoundedCornerShape(bottomStart = 24.dp, bottomEnd = 24.dp)
                )
                .padding(top = 16.dp, bottom = 16.dp, start = 8.dp, end = 16.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { /* Volver si fuera necesario */ }) {
                    Icon(Icons.Default.ChevronLeft, contentDescription = null, tint = Color.White)
                }
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = Color(0xFFD4AF37), // Gold
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = "Inteligencia Ejecutiva",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                    Text(
                        text = "Powered by Gemini AI",
                        color = Color.White.copy(alpha = 0.6f),
                        fontSize = 11.sp
                    )
                }
            }
        }

        // Messages List
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            contentPadding = PaddingValues(vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(messages) { message ->
                ExecutiveChatBubble(message)
            }
            if (isLoading) {
                item {
                    LoadingBubble()
                }
            }
        }

        // Quick Actions Row
        if (messages.size < 3) {
            LazyRow(
                modifier = Modifier.padding(bottom = 8.dp, start = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(quickQuestions) { question ->
                    SuggestionChip(
                        onClick = { viewModel.sendMessage(question) },
                        label = { Text(question, fontSize = 12.sp) },
                        colors = SuggestionChipDefaults.suggestionChipColors(
                            containerColor = Color.White,
                            labelColor = DeepNavy
                        )
                    )
                }
            }
        }

        // Input Area Premium
        Surface(
            modifier = Modifier.fillMaxWidth(),
            tonalElevation = 8.dp,
            shadowElevation = 16.dp,
            color = Color.White
        ) {
            Row(
                modifier = Modifier
                    .padding(16.dp)
                    .imePadding(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    placeholder = { Text("Consultar estrategia...") },
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(28.dp)),
                    colors = TextFieldDefaults.textFieldColors(
                        containerColor = Color(0xFFF1F3F4),
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent
                    )
                )
                Spacer(modifier = Modifier.width(12.dp))
                IconButton(
                    onClick = {
                        if (inputText.isNotBlank()) {
                            viewModel.sendMessage(inputText)
                            inputText = ""
                        }
                    },
                    modifier = Modifier
                        .background(CorporateGreen, CircleShape)
                        .size(48.dp)
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Enviar", tint = Color.White)
                }
            }
        }
    }
}

@Composable
fun ExecutiveChatBubble(message: ChatMessage) {
    val isUser = message.isUser
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
    ) {
        Surface(
            color = if (isUser) DeepNavy else Color.White,
            shape = if (isUser) 
                RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp) 
                else RoundedCornerShape(20.dp, 20.dp, 20.dp, 4.dp),
            shadowElevation = 2.dp,
            tonalElevation = if (isUser) 0.dp else 2.dp
        ) {
            Text(
                text = message.content,
                modifier = Modifier.padding(14.dp),
                color = if (isUser) Color.White else Color.DarkGray,
                fontSize = 15.sp,
                lineHeight = 22.sp
            )
        }
        Text(
            text = if (isUser) "Directivo" else "Gemini Advisor",
            fontSize = 10.sp,
            color = Color.Gray,
            modifier = Modifier.padding(top = 4.dp, start = 4.dp, end = 4.dp)
        )
    }
}

@Composable
fun LoadingBubble() {
    Row(
        modifier = Modifier
            .background(Color.White, RoundedCornerShape(16.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(16.dp),
            color = CorporateGreen,
            strokeWidth = 2.dp
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text("Gemini está analizando...", fontSize = 12.sp, color = Color.Gray)
    }
}
