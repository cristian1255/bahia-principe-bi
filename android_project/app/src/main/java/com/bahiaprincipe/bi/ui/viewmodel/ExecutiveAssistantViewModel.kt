package com.bahiaprincipe.bi.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bahiaprincipe.bi.data.ExecutiveRepository
import com.bahiaprincipe.bi.data.model.ChatMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ExecutiveAssistantViewModel(
    private val repository: ExecutiveRepository
) : ViewModel() {

    private val _chatMessages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val chatMessages: StateFlow<List<ChatMessage>> = _chatMessages.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    init {
        viewModelScope.launch {
            repository.chatHistory.collect { history ->
                if (history.isNotEmpty()) {
                    _chatMessages.value = history
                } else {
                    _chatMessages.value = listOf(
                        ChatMessage("Hola, soy tu asistente ejecutivo de Bahía Príncipe. ¿En qué puedo ayudarte hoy?", false)
                    )
                }
            }
        }
    }

    fun sendMessage(text: String) {
        if (text.isBlank()) return

        val userMessage = ChatMessage(text, true)
        _chatMessages.value = _chatMessages.value + userMessage
        viewModelScope.launch {
            repository.persistChatMessage(userMessage)
        }

        processAiResponse(text)
    }

    private fun processAiResponse(prompt: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val history = _chatMessages.value.map { it.content }
                val response = repository.chatWithGemini(history, prompt)
                val aiMessage = ChatMessage(response, false)
                _chatMessages.value = _chatMessages.value + aiMessage
                repository.persistChatMessage(aiMessage)
            } catch (e: Exception) {
                val detail = e.message ?: "Error desconocido"
                val errorMsg = "Fallo de Conexión IA: $detail. Verifica si tu API Key es válida para el modelo Gemini Pro."
                val aiError = ChatMessage(errorMsg, false)
                _chatMessages.value = _chatMessages.value + aiError
                repository.persistChatMessage(aiError)
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun startDeepQuery(context: String, question: String) {
        val initialPrompt = "Analizando contexto: $context. Pregunta: $question"
        _chatMessages.value = listOf(ChatMessage(initialPrompt, true))
        processAiResponse(initialPrompt)
    }

    fun clearChat() {
        viewModelScope.launch {
            repository.clearChatHistory()
            _chatMessages.value = listOf(ChatMessage("Chat reiniciado. ¿En qué más puedo ayudarte?", false))
            repository.persistChatMessage(_chatMessages.value.first())
        }
    }
}
