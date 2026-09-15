package com.bahiaprincipe.bi.ui.theme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val BahiaCorporateGreen = Color(0xFF006B3F)
val BahiaDeepNavy = Color(0xFF0E3A66)
val BahiaGold = Color(0xFFD4AF37)
val BahiaSoftCream = Color(0xFFEFE9DF)

@Composable
fun BahiaLogoMark(
    modifier: Modifier = Modifier,
    size: Dp = 88.dp,
    accentColor: Color = BahiaGold
) {
    Box(
        modifier = modifier.size(size),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val centerX = size.toPx() / 2f
            val centerY = size.toPx() / 2f
            val petalWidth = size.toPx() * 0.18f
            val petalHeight = size.toPx() * 0.42f

            repeat(12) { index ->
                rotate(degrees = index * 30f, pivot = Offset(centerX, centerY)) {
                    drawRoundRect(
                        color = accentColor,
                        topLeft = Offset(centerX - petalWidth / 2f, centerY - petalHeight * 0.9f),
                        size = Size(petalWidth, petalHeight),
                        cornerRadius = CornerRadius(petalWidth * 0.9f, petalWidth * 0.9f)
                    )
                }
            }

            drawCircle(
                color = accentColor.copy(alpha = 0.18f),
                radius = size.toPx() * 0.31f,
                center = Offset(centerX, centerY)
            )
            drawCircle(
                color = accentColor,
                radius = size.toPx() * 0.06f,
                center = Offset(centerX, centerY)
            )
        }
    }
}

@Composable
fun BahiaWordmark(
    modifier: Modifier = Modifier,
    large: Boolean = true,
    textColor: Color = BahiaDeepNavy,
    accentColor: Color = BahiaGold
) {
    val headlineSize = if (large) 90.sp else 32.sp
    val subtextSize = if (large) 24.sp else 15.sp

    Box(modifier = modifier) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "BAHIA",
                color = textColor,
                fontSize = headlineSize,
                fontWeight = FontWeight.Bold,
                style = TextStyle(letterSpacing = (-4).sp),
                textAlign = TextAlign.Center,
                lineHeight = if (large) 88.sp else 34.sp
            )
            Text(
                text = "PRINCIPE",
                color = textColor,
                fontSize = headlineSize,
                fontWeight = FontWeight.Bold,
                style = TextStyle(letterSpacing = (-4).sp),
                textAlign = TextAlign.Center,
                lineHeight = if (large) 88.sp else 34.sp
            )
            Text(
                text = "HOTELS & RESORTS",
                color = textColor.copy(alpha = 0.9f),
                fontSize = subtextSize,
                fontWeight = FontWeight.Light,
                style = TextStyle(letterSpacing = 1.sp),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 8.dp)
            )
        }
    }
}
