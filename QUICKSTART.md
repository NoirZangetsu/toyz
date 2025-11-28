# 🚀 Hızlı Başlangıç Kılavuzu

Bu kılavuz, projeyi hızlıca çalıştırmanız için gerekli adımları içerir.

## 📋 Gereksinimler

- Python 3.7 veya üzeri
- Chrome tarayıcısı
- Telegram hesabı (bildirimler için)

## ⚡ 5 Dakikada Kurulum

### 1. Bağımlılıkları Kurun

**Windows (PowerShell):**
```powershell
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
pip install -r requirements.txt
```

### 2. ChromeDriver Kurun

**Windows:**
```powershell
# Chocolatey ile:
choco install chromedriver

# Veya manuel: https://chromedriver.chromium.org/downloads
```

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

### 3. Telegram Bot Oluşturun

1. Telegram'da `@BotFather` botunu açın
2. `/newbot` komutunu gönderin
3. Bot adı ve kullanıcı adı belirleyin
4. Size verilen **TOKEN**'i kopyalayın

### 4. Chat ID'nizi Alın

**Kolay Yol:**
1. Telegram'da `@userinfobot` botuna mesaj gönderin
2. Size verilen ID'yi kopyalayın

### 5. config.py Dosyasını Düzenleyin

`config.py` dosyasını açın ve şunları girin:

```python
TELEGRAM_BOT_TOKEN = "BURAYA_TOKEN_YAPIŞTIRIN"
TELEGRAM_CHAT_ID = "BURAYA_CHAT_ID_YAPIŞTIRIN"
```

### 6. Çalıştırın!

**Tüm siteleri izlemek için:**
```bash
python multi_site_monitor.py
```

İşte bu kadar! 🎉

## 📱 İlk Bildirim

Script başladığında:
- ✅ Telegram'dan bir başlangıç özeti alacaksınız
- ✅ Her sitedeki mevcut ürün sayısını göreceksiniz
- ✅ Yeni ürün eklendiğinde anında bildirim gelecek

## 🎯 Önerilen Ayarlar

### Kontrol Aralıkları

```bash
# Piccolo (API - hızlı)
python api_monitor.py  # 30 saniye

# Tüm siteler (önerilen)
python multi_site_monitor.py  # 5 dakika
```

### Sadece Belirli Siteleri İzlemek

```bash
# Sadece Piccolo
python api_monitor.py

# Sadece DiecastTurkey
python diecastturkey_monitor.py
```

## 🔧 Sorun Giderme

### ChromeDriver Bulunamadı

```bash
# Kurulu olup olmadığını kontrol edin:
which chromedriver  # macOS/Linux
where chromedriver  # Windows

# Yolunu PATH'e ekleyin (gerekirse)
```

### Telegram Bildirimi Gelmiyor

1. `config.py` dosyasındaki TOKEN ve CHAT_ID'yi kontrol edin
2. Botunuza `/start` komutu gönderdiğinizden emin olun
3. Token ve Chat ID'de boşluk veya tırnak işareti olmadığından emin olun

### Selenium Hatası

```bash
# Selenium'u yeniden kurun:
pip install --upgrade selenium
```

## 💡 İpuçları

1. **Arka planda çalıştırma:**
   - Windows: Task Scheduler kullanın
   - macOS/Linux: `nohup python multi_site_monitor.py &`

2. **Sunucuda çalıştırma:**
   - `screen` veya `tmux` kullanın
   - Örnek: `screen -S monitor python multi_site_monitor.py`

3. **Logları kaydetme:**
   ```bash
   python multi_site_monitor.py > logs.txt 2>&1
   ```

## 🆘 Yardım

Daha fazla bilgi için `README.md` dosyasına bakın.

---

**Kolay gelsin! 🎮🚗**

