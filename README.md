# Discord Guard Bot

Bu bot, sunucunuzdaki önemli olayları (everyone etiketleri, rol değişiklikleri, kanal işlemleri vb.) takip eder ve belirlediğiniz bir log kanalına raporlar.

## Özellikler
- **Log Kanalı Ayarlama:** `!log #kanal` komutu ile raporların gideceği kanalı belirleyebilirsiniz.
- **Etiket Koruması:** Birisi `@everyone` veya `@here` attığında anında log kanalına bilgi düşer.
- **Rol Takibi:** Kim hangi rolü aldı veya verdi görebilirsiniz.
- **Kanal Takibi:** Oluşturulan veya silinen kanalları raporlar.
- **Render Uyumluluğu:** İçindeki web sunucusu sayesinde Render gibi platformlarda 7/24 aktif kalabilir.

## Kurulum
1. [Discord Developer Portal](https://discord.com/developers/applications) üzerinden bir bot oluşturun.
2. **Privileged Gateway Intents** kısmından tüm intentleri (özellikle Message Content) aktif edin.
3. Botunuzun tokenini kopyalayın.
4. Render veya benzeri bir platformda projeyi başlatırken `DISCORD_TOKEN` adında bir çevre değişkeni (Environment Variable) ekleyin ve tokeninizi buraya yapıştırın.

## Komutlar
- `!log #kanal`: Log kanalını ayarlar (Yönetici yetkisi gerektirir).

## Render İçin Ping
Botun uyumaması için Render'ın size verdiği URL'i (örn: `https://bot-adiniz.onrender.com`) bir uptime servisine (UptimeRobot vb.) ekleyerek 5 dakikada bir ping atılmasını sağlayabilirsiniz.
