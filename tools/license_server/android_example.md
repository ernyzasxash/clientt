Kotlin (Android) örneği — uygulama açıldığında lisans doğrulama

Bu örnek `OkHttp` kullanır. `build.gradle` içinde `implementation 'com.squareup.okhttp3:okhttp:4.11.0'` ekleyin.

Örnek kullanım (Activity içinde):

```kotlin
val client = OkHttpClient()

fun checkLicense(key: String, callback: (Boolean)->Unit) {
  // For your VPS use the IP below (use HTTPS in production)
  val url = "https://5.22.215.107/check?key=${URLEncoder.encode(key, "utf-8") }"
  val req = Request.Builder().url(url).get().build()
  client.newCall(req).enqueue(object: Callback {
    override fun onFailure(call: Call, e: IOException) {
      runOnUiThread { callback(false) }
    }
    override fun onResponse(call: Call, response: Response) {
      val body = response.body?.string()
      // Basit parse
      val ok = body?.contains("success") == true
      runOnUiThread { callback(ok) }
    }
  })
}

// Aktivite açıldığında gösterilecek basit dialog (pseudocode):
// 1) Kullanıcıdan key al
// 2) checkLicense(key) çağır
// 3) Eğer true ise oyuna devam et, false ise dialogu kapatma ve hata göster

```

Notlar
- HTTPS kullanın. Sunucunuzda TLS yoksa Android 9+ cihazlar HTTP'yi engelleyebilir.
- Gerçek uygulamada cevapları JSON parse edin ve hata durumlarını düzgün yönetin.
