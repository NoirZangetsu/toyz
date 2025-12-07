# 🚀 Google Cloud'da Piccolo Monitor Çalıştırma

## 🎯 Hızlı Başlangıç (Tek Komut)

Google Cloud SSH'de çalıştır:

```bash
cd ~/toyz && bash GOOGLE_CLOUD_SETUP.sh
```

Bu komut:
- ✅ Tüm bağımlılıkları kurar
- ✅ Chrome'u kurur
- ✅ WebDriver cache'i temizler
- ✅ Playwright browser'larını kurar
- ✅ Testi çalıştırır

---

## 🔍 Google Cloud'da Neden Çalışmıyor?

### Sorun: "0 ID bulundu"

**Sebepleri:**
1. **Headless mode** - Cloudflare headless browser'ları detect ediyor
2. **Google Cloud IP** - ISP IP'si blok ediliyor
3. **JavaScript rendering** - Headless modda sayfayı farklı render ediyor

### Çözüm: Test Et!

Google Cloud'da:

```bash
cd ~/toyz
source venv/bin/activate

# Test script'i çalıştır
python test_piccolo_gcloud.py
```

Bu script şunları test eder:
- ✅ **Headless Mode** (lokal gibi)
- ✅ **GUI Mode** (Cloudflare bypass - önerilen)

**Çıktı örneği:**
```
ÖZET
=====================================
Headless Mode: ❌ BAŞARILI DEĞİL
GUI Mode:      ✅ BAŞARILI

💡 Sonuç: GUI Mode'u kullanmalısın!
```

---

## 💻 Google Cloud'da Gerçek Çalıştırma

### Seçenek A: API Mode (Önerilen)

Eğer test başarılıysa:

```bash
cd ~/toyz
source venv/bin/activate

# Multi-site monitor'u başlat (3 dakika aralık)
python multi_site_monitor.py 180
```

### Seçenek B: Headless=False (GUI Mode)

Eğer GUI Mode test başarılıysa, kodu şu şekilde çalıştır:

```python
# api_monitor.py'de şu satırı değiştir:
driver = setup_piccolo_driver(headless=False)  # GUI Mode
```

---

## 📋 Adım Adım Kurulum

### 1. Google Cloud VM'ye Bağlan

```bash
gcloud compute ssh instance-name --zone=us-central1-a
```

### 2. Setup Script'i Çalıştır

```bash
cd ~/toyz
bash GOOGLE_CLOUD_SETUP.sh
```

### 3. Test Et

```bash
python test_piccolo_gcloud.py
```

**Beklenen çıktı:**
```
✅ BAŞARILI
   IDs bulundu: 10
   data-id elements: 50
   Page title: Hot Wheels Premium
```

### 4. Monitor Başlat

```bash
# Screen session başlat
screen -S piccolo

# İçinde çalıştır
source venv/bin/activate
python multi_site_monitor.py 180

# Detach: Ctrl+A, D
```

### 5. Status Kontrol

```bash
# Session'ları listele
screen -ls

# Log'ları görmek
tail -f monitor.log

# Session'a geri dön
screen -r piccolo
```

---

## 🆘 Sorun Giderme

### Sorun 1: "Chrome bulunamadı"

```bash
# Chrome kur
sudo apt update
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list'
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo apt update
sudo apt install -y google-chrome-stable

# Kontrol
google-chrome --version
```

### Sorun 2: "Version mismatch"

```bash
# WebDriver cache temizle
rm -rf ~/.wdm/

# Tekrar dene
python api_monitor.py
```

### Sorun 3: "Playwright error"

```bash
source venv/bin/activate
playwright install chromium
```

### Sorun 4: "0 ID bulunamadı"

```bash
# Test et (hangi mode çalışıyor öğren)
python test_piccolo_gcloud.py

# Debug HTML'i kontrol et
cat piccolo_debug.html | head -100
```

---

## 📊 Test Sonuçlarını Anlama

Test script çıktısında:

```
✅ SONUÇLAR:
   IDs bulundu: 10           # ✅ Başarı!
   data-id elements: 50      # Element sayısı
   Total elements: 3000      # Tüm DOM element'leri
   Page title: Hot Wheels... # Sayfa başlığı
   HTML size: 250000 bytes   # Sayfa boyutu
```

**Eğer IDs = 0:**
- GUI Mode'u dene
- `test_piccolo_gcloud.py` ile headless=False test et

---

## 🎯 Recommended Setup

Google Cloud'da en iyi sonuç için:

```bash
# 1. Setup
bash GOOGLE_CLOUD_SETUP.sh

# 2. Test
python test_piccolo_gcloud.py

# 3. Eğer GUI Mode başarılıysa:
# api_monitor.py'de setup_piccolo_driver(headless=False) yap

# 4. Monitor başlat
screen -S piccolo
python multi_site_monitor.py 180
```

---

## 📝 Kontrol Listesi

- [ ] Google Cloud VM oluşturuldu
- [ ] SSH bağlantısı çalışıyor
- [ ] `cd ~/toyz && bash GOOGLE_CLOUD_SETUP.sh` çalıştırıldı
- [ ] `python test_piccolo_gcloud.py` başarılı
- [ ] Monitor `screen -S piccolo` ile başlatıldı
- [ ] Log'larda "✅ 10 ürün bulundu" görüldü
- [ ] Telegram'dan bildirim alındı

---

**Sorular? Loglardaki hata mesajlarını göster!** 🚀

