package com.maomaonotify.maomao_client

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import androidx.core.app.NotificationCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

/// Native bridge for client TTS (§26), text notifications, and Voice Alerts
/// Mode foreground service (§57). Talks to Dart over the `maomao/android`
/// MethodChannel.
class MainActivity : FlutterActivity() {
    private val channelName = "maomao/android"
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var player: MediaPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Android 13+ requires a runtime grant for notifications to appear.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1001)
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        ensureChannels()
        tts = TextToSpeech(applicationContext) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
        }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "speak" -> result.success(
                        speak(call.argument<String>("text") ?: "", call.argument<String>("language"))
                    )
                    "showNotification" -> result.success(
                        showNotification(
                            call.argument<String>("title") ?: "MaoMaoNotify",
                            call.argument<String>("body") ?: "",
                            call.argument<String>("priority") ?: "normal",
                        )
                    )
                    "playAudio" -> result.success(playAudio(call.argument<String>("url") ?: ""))
                    "startVoiceAlerts" -> {
                        startVoiceAlerts(); result.success(null)
                    }
                    "stopVoiceAlerts" -> {
                        stopVoiceAlerts(); result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun ensureChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(
                NotificationChannel(
                    "maomao_notifications", "Notifications", NotificationManager.IMPORTANCE_HIGH,
                )
            )
            nm.createNotificationChannel(
                NotificationChannel(
                    "maomao_voice_alerts", "Voice Alerts", NotificationManager.IMPORTANCE_LOW,
                )
            )
        }
    }

    private fun speak(text: String, lang: String?): Boolean {
        val engine = tts ?: return false
        if (!ttsReady || text.isBlank()) return false
        if (lang != null) engine.language = Locale.forLanguageTag(lang)
        engine.speak(text, TextToSpeech.QUEUE_ADD, null, System.currentTimeMillis().toString())
        return true
    }

    private fun showNotification(title: String, body: String, priority: String): Boolean {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val prio = when (priority) {
            "high", "critical" -> NotificationCompat.PRIORITY_HIGH
            "low" -> NotificationCompat.PRIORITY_LOW
            else -> NotificationCompat.PRIORITY_DEFAULT
        }
        val notification = NotificationCompat.Builder(this, "maomao_notifications")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(prio)
            .setAutoCancel(true)
            .build()
        nm.notify(System.currentTimeMillis().toInt(), notification)
        return true
    }

    private fun playAudio(url: String): Boolean {
        if (url.isBlank()) return false
        return try {
            player?.release()
            player = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                setDataSource(url)
                setOnPreparedListener { it.start() }
                setOnCompletionListener { it.release() }
                prepareAsync()
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun startVoiceAlerts() {
        val intent = Intent(this, VoiceAlertsService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopVoiceAlerts() {
        stopService(Intent(this, VoiceAlertsService::class.java))
    }

    override fun onDestroy() {
        tts?.shutdown()
        player?.release()
        super.onDestroy()
    }
}
