package com.vera.pulse

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            VeraPulseApp()
        }
    }
}

@Composable
fun VeraPulseApp() {
    var currentScreen by remember { mutableStateOf("home") }
    
    MaterialTheme {
        when (currentScreen) {
            "identity" -> IdentityScreen { currentScreen = "home" }
            "attestation" -> AttestationScreen { currentScreen = "home" }
            "message" -> MessageScreen { currentScreen = "home" }
            else -> HomeScreen { screen -> currentScreen = screen }
        }
    }
}

@Composable
fun HomeScreen(onNavigate: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("VERA Pulse", style = MaterialTheme.typography.headlineLarge)
        Spacer(modifier = Modifier.height(32.dp))
        
        Button(onClick = { onNavigate("identity") }) {
            Text("Identité VERA")
        }
        Spacer(modifier = Modifier.height(16.dp))
        
        Button(onClick = { onNavigate("attestation") }) {
            Text("Attestation")
        }
        Spacer(modifier = Modifier.height(16.dp))
        
        Button(onClick = { onNavigate("message") }) {
            Text("Message Chiffré")
        }
    }
}

@Composable
fun IdentityScreen(onBack: () -> Unit) {
    Column(modifier = Modifier.padding(16.dp)) {
        Button(onClick = onBack) { Text("← Retour") }
        Text("Identité VERA", style = MaterialTheme.typography.headlineMedium)
        Text("Clé publique générée via HPKE")
    }
}

@Composable
fun AttestationScreen(onBack: () -> Unit) {
    Column(modifier = Modifier.padding(16.dp)) {
        Button(onClick = onBack) { Text("← Retour") }
        Text("Attestation", style = MaterialTheme.typography.headlineMedium)
        Text("Intégrité du device vérifiée")
    }
}

@Composable
fun MessageScreen(onBack: () -> Unit) {
    Column(modifier = Modifier.padding(16.dp)) {
        Button(onClick = onBack) { Text("← Retour") }
        Text("Message Chiffré", style = MaterialTheme.typography.headlineMedium)
        Text("Chiffrer / Déchiffrer via vera_core")
    }
}
