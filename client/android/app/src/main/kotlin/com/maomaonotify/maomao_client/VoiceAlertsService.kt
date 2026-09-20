package com.maomaonotify.maomao_client

import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat

/// Voice Alerts Mode foreground service (§57): keeps the client alive to play
/// voice notifications reliably in the background. Shows a persistent
/// notification so the user always knows it is running.
class VoiceAlertsService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, "maomao_voice_alerts")
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("MaoMaoNotify Voice Alerts")
            .setContentText("Active — will speak incoming voice notifications")
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1001, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(1001, notification)
        }
        return START_STICKY
    }
}
