# Multi-Site Ürün Monitor

Bu proje, **Piccolo** ve **DiecastTurkey** sitelerini periyodik olarak kontrol edip yeni ürünleri Telegram üzerinden bildirir.

## 📍 İzlenen Siteler

1. **Piccolo** - Hot Wheels Premium kategorisi ✅ Aktif
2. **DiecastTurkey** - Hot Wheels ürünleri (tüm koleksiyon) ✅ Aktif

## Kurulum

### 1. Gerekli Paketleri Yükleyin

```bash
pip install -r requirements.txt
```

### 2. Chrome WebDriver Kurulumu (Toyzzshop için)

**Windows:**
```powershell
# Chocolatey ile:
choco install chromedriver

# Veya manuel: https://chromedriver.chromium.org/downloads
# İndirip PATH'e ekleyin
```

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

## Kullanım

### 🎯 Önerilen: Multi-Site Monitor (TÜM SİTELER)

Hem Piccolo hem DiecastTurkey'i aynı anda izler:

```bash
python multi_site_monitor.py
```

Varsayılan olarak her 5 dakikada (300 saniye) bir kontrol eder.

**Özel aralık:**
```bash
python multi_site_monitor.py 180  # 3 dakikada bir
```

**Tek seferlik kontrol:**
```bash
python multi_site_monitor.py 0 once
```

### Sadece Piccolo İzleme

```bash
python api_monitor.py
```

Her 30 saniyede bir API'yi kontrol eder.

**Özel aralık:**
```bash
python api_monitor.py 60  # 60 saniyede bir
```

### Sadece DiecastTurkey İzleme

```bash
python diecastturkey_monitor.py
```

Her 5 dakikada bir kontrol eder ve stok durumunu takip eder.

**Özel aralık:**
```bash
python diecastturkey_monitor.py 180  # 3 dakikada bir
```

## Özellikler

- ✅ **Multi-site izleme** - Birden fazla siteyi aynı anda takip eder
- ✅ **Piccolo API kontrolü** - API endpoint'ini izler
- ✅ **DiecastTurkey web scraping** - Selenium ile ürünleri çeker ve stok takibi yapar
- ✅ **Yeni ürün tespiti** - Ürün listesindeki değişiklikleri algılar
- ✅ **Telegram bildirimi** - Yeni ürün bulunduğunda anında bildirim (önerilen!)
- ✅ **E-posta bildirimi** - Opsiyonel (Gmail kullanabilirsiniz)
- ✅ **Ürün detayları** - Ürün adı, fiyat, stok, link
- ✅ **İlk özet** - İzleme başladığında mevcut ürünlerin özeti
- ✅ **Gelişmiş hata yönetimi** - Timeout, bağlantı, scraping hataları
- ✅ **Zaman damgalı loglar**

## İzlenen Siteler Detay

### 1. Piccolo (API)
- **URL:** https://www.piccolo.com.tr/hot-wheels-premium
- **API:** https://www.piccolo.com.tr/api/Product/GetProductCategoryHierarchy
- **Yöntem:** REST API
- **Kontrol aralığı:** 30 saniye (önerilen)

### 2. DiecastTurkey (Web Scraping - JavaScript Data)
- **URL:** https://www.diecastturkey.com/hot-wheels-12
- **Yöntem:** Selenium WebDriver + JavaScript Data Extraction
- **Kontrol aralığı:** 5 dakika (önerilen)
- **Özellik:** Stok durumu takibi

## Bildirim Ayarları

Sistem yeni ürün tespit ettiğinde bildirim gönderebilir. **Telegram bot** (önerilen - çok kolay!) veya **E-posta** kullanabilirsiniz.

### 🚀 Yöntem 1: Telegram Bot (ÖNERİLEN - SMTP Sunucusu Gerektirmez!)

Telegram bot kullanmak çok daha kolaydır ve SMTP sunucusu gerektirmez!

#### Adım 1: Telegram Bot Oluşturma

1. Telegram uygulamasını açın
2. Arama kutusuna `@BotFather` yazın ve açın
3. `/newbot` komutunu gönderin
4. Bot adını girin (örn: "Piccolo Ürün Bildirim Botu")
5. Bot kullanıcı adını girin (örn: "piccolo_urun_bot" - sonunda `_bot` olmalı)
6. Size verilen **TOKEN**'i kopyalayın (örn: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Adım 2: Chat ID Alma

**Yöntem A:** Basit yöntem
1. Telegram'da `@userinfobot` botuna mesaj gönderin
2. Size verilen ID'yi kopyalayın

**Yöntem B:** Kendi botunuzla
1. Oluşturduğunuz botunuza `/start` yazın
2. Tarayıcıda şu URL'yi açın (TOKEN'i değiştirin):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Gelen JSON'da `"chat":{"id":123456789}` şeklinde bir satır bulun
4. `123456789` numarasını kopyalayın

#### Adım 3: config.py Dosyasını Düzenleme

`config.py` dosyasını açın ve şunları doldurun:

```python
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"  # BotFather'dan aldığınız token
TELEGRAM_CHAT_ID = "123456789"  # Chat ID'niz
```

**Hepsi bu kadar!** Artık yeni ürün bulunduğunda Telegram'dan bildirim alacaksınız! 🎉
Script ilk çalıştığında mevcut ürünlerin özetini (ürün sayısı, ID listesi ve kategori linki) Telegram'a otomatik gönderir.

---

### 📧 Yöntem 2: E-posta (Gmail Kullanabilirsiniz)

E-posta göndermek için **config.py** dosyasını düzenleyin:

1. Proje klasöründeki `config.py` dosyasını açın
2. E-posta bilgilerinizi girin:

```python
# SMTP Sunucu Bilgileri
SMTP_SERVER = "smtp.gmail.com"  # Gmail için: smtp.gmail.com
SMTP_PORT = 587  # Gmail için: 587 (TLS) veya 465 (SSL)
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"  # Gmail için uygulama şifresi gerekli
SMTP_USE_TLS = True  # Port 587 için True, Port 465 için False

# E-posta Bilgileri
EMAIL_FROM = "your-email@gmail.com"
EMAIL_TO = "recipient@example.com"  # Birden fazla için: "email1@example.com,email2@example.com"
```

**Gmail Kullanıyorsanız:**
- Gmail hesabınızda "2 Adımlı Doğrulama" açık olmalı
- "Uygulama Şifreleri" bölümünden yeni bir şifre oluşturun
- Bu şifreyi `SMTP_PASSWORD` alanına girin

### Yöntem 3: Ortam Değişkenleri (E-posta için)

Alternatif olarak terminalde ortam değişkenlerini ayarlayabilirsiniz:

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export EMAIL_FROM="your-email@gmail.com"
export EMAIL_TO="recipient@example.com"
export SMTP_USE_TLS="true"
```

Birden fazla alıcıyı virgülle ayırabilirsiniz. TLS destekleyen sunucularda `SMTP_USE_TLS` değerini `true` bırakın. Port 465 kullanıyorsanız TLS otomatik olarak SSL modunda çalışır.

Yeni ürün bulunduğunda e-posta içeriği kategori bağlantısını da içerir:

```
https://www.piccolo.com.tr/hot-wheels-premium
```

## Çıktı Örneği

Script çalıştığında şu bilgileri gösterir:
- Her kontrol zamanı
- Toplam ürün sayısı
- Var olan ürün ID'leri listesi
- Kategori bilgileri (kategori adları ve ID'leri)
- Değişiklik durumu (ilk yanıt veya değişiklik tespiti)
- Hata durumları (varsa)

## Örnek Çıktı

```
======================================================================
🔍 Piccolo Ürün Kategori Hiyerarşisi Monitor
======================================================================
📡 API URL: https://www.piccolo.com.tr/api/Product/GetProductCategoryHierarchy
📋 Parametreler: {'c': 'trtry0000', 'productIds': '682,1053,1093,...'}
⏱️  Kontrol aralığı: 30 saniye
======================================================================

[2025-11-13 09:58:23] Kontrol #1
======================================================================

✅ İlk yanıt alındı

📊 Ürün Analizi:
----------------------------------------------------------------------
✅ Toplam Ürün Sayısı: 16

📦 Var Olan Ürünler:
   Ürün ID'leri: 682, 1053, 1093, 1094, 1114, 1115, 1116, 1125, 1136, 1165, 1167, 1168, 1169, 1172, 1173, 1174

🏷️  Kategori Bilgileri:
   Kategori seviyesi: 2
   Kategoriler:
      • HOT WHEELS PREMİUM (ID: 64)
      • Model ve Metal Araçlar (ID: 61)
```
