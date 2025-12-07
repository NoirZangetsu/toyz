# 🌐 Cloudflare Bypass Guide

Google Cloud'da Piccolo Scraping - Hızlı Başlangıç

## 🚨 Sorun

Piccolo sitesi **Cloudflare** tarafından korunuyor:
```
Google Cloud VM + Normal HTTP = ❌ 403 Forbidden / Bot Detected
```

## ✅ Çözüm

Yeni kod 2 yöntemle bypass yapıyor:

### Yöntem 1: HTTP API (Hızlı ⚡)
```python
from api_monitor import get_piccolo_monitor

monitor = get_piccolo_monitor()
products, error = monitor.scrape_piccolo_api_direct()
```
- ⚡ **7-10 saniye**
- ✅ Cloudflare headers ile
- ✅ Automatic retry (429 rate limit'e karşı)
- ✅ Selenium gerektirmez

### Yöntem 2: Selenium (Fallback 🔄)
```python
from api_monitor import setup_piccolo_driver, get_piccolo_monitor

monitor = get_piccolo_monitor()
driver = setup_piccolo_driver()
products, error = monitor.scrape_piccolo_selenium(driver)
driver.quit()
```
- 🕐 ~28 saniye
- ✅ Browser CDP (navigator.webdriver gizleme)
- ✅ JavaScript rendering
- ✅ Cloudflare bot detection'ı bypass

### Yöntem 3: Auto-Fallback (Önerilen)
```python
from api_monitor import scrape_piccolo_sync, get_piccolo_monitor

monitor = get_piccolo_monitor()
products, error = scrape_piccolo_sync(monitor, method="auto")
# Otomatik: API dene → başarısız → Selenium'e düş
```

## 🚀 Google Cloud'da Kurulum

### 1. SSH'ye Bağlan
```bash
gcloud compute ssh instance-name --zone=us-central1-a
```

### 2. Python & Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip chromium-browser chromium-chromedriver
cd ~/toyz  # projenizin dizini
pip install -r requirements.txt
```

### 3. Test Et
```bash
python3 api_monitor.py
```

**Beklenen Çıktı:**
```
🚀 Piccolo Monitor Test
======================================================================

Yöntem 1: HTTP API (Cloudflare bypass)
----------------------------------------------------------------------
🔄 [Yöntem 1] HTTP API approach (Cloudflare bypass)...
  📡 Sayfaya GET: https://www.piccolo.com.tr/hot-wheels-premium
  ✅ Toplam 25 unique ürün bulundu
  🌐 API çağrısı: 25 ürün için...
  ✅ API'den 25 ürün çekildi

✅ BAŞARILI! 25 ürün bulundu

İlk 5 ürün:
  1. Hot Wheels Hot Wheels Premium - HW001 - 45.99 TL
  2. Hot Wheels Collector Series - HW002 - 52.50 TL
  ...

💾 Veritabanı kaydedildi
======================================================================
```

## 🔧 Troubleshooting

### Problem 1: "Bağlantı hatası" veya "Timeout"
```
❌ HTTP hatası: Connection timeout
```

**Çözüm:**
1. GCP firewall kuralını kontrol et
2. Proxy kullan:
   ```python
   session.proxies = {
       'http': 'http://proxy.company.com:8080',
       'https': 'http://proxy.company.com:8080'
   }
   ```

### Problem 2: "HTML'de ID bulunamadı"
```
⚠️ HTML'den ID bulunamadı
```

**Çözüm:**
1. Debug dosyasını kontrol et: `piccolo_debug.html`
2. Piccolo HTML yapısı değişmiş olabilir
3. Örnek:
   ```bash
   head -50 piccolo_debug.html | grep -i hot
   ```

### Problem 3: "Selenium timeout"
```
⚠️ Document ready timeout, devam ediliyor...
```

**Çözüm:**
1. Normal (API başarılı ise Selenium'a ihtiyaç yok)
2. Network yavaşsa timeout'u artır:
   ```python
   WebDriverWait(driver, 30)  # 20'den 30'a
   time.sleep(10)             # Bekleme süresini artır
   ```

### Problem 4: "Chrome/ChromeDriver bulunamadı"
```
❌ Error: chromedriver not found
```

**Çözüm:**
```bash
# Otomatik olarak indirilmeli (webdriver-manager)
# Manuel indirme:
sudo apt install chromium-chromedriver

# Veya Google tarafından:
# https://chromedriver.chromium.org/downloads
# Sürümü uyumlu olduğundan emin ol:
chromium-browser --version
```

## 📊 Performance Tuning

### Daha Hızlı (HTTP API'yi tercih et)
```python
# multi_site_monitor.py'de
products, error = scrape_piccolo_sync(monitor, method="api")  # ⚡ 7-10s
if error:
    # Fallback
    products, error = scrape_piccolo_sync(monitor, method="selenium")
```

### Daha Güvenilir (Selenium)
```python
# Eğer API sık başarısız olursa
products, error = scrape_piccolo_sync(monitor, method="selenium")
```

### Hybrid (Önerilen)
```python
# Otomatik fallback (default)
products, error = scrape_piccolo_sync(monitor)  # method="auto"
```

## 🔍 Headers Özelleştirme

Eğer Cloudflare hala block ediyorsa headers'ı değiştir:

```python
# api_monitor.py -> get_cloudflare_headers()

def get_cloudflare_headers():
    return {
        # Mobile user-agent dene
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1...',
        'Accept-Language': 'en-US,en;q=0.9',  # İngilizce dene
        'Referer': 'https://www.google.com/',  # Referrer değiştir
        # ...
    }
```

## 📈 Monitoring

### Logları Kontrol Et
```bash
# Çalışan monitor'ı kontrol et
tail -f /path/to/logs

# API başarı oranı
grep "API'den.*ürün çekildi" /path/to/logs | wc -l
```

### Response Time Ölçme
```python
import time

start = time.time()
products, error = monitor.scrape_piccolo_api_direct()
elapsed = time.time() - start

print(f"API Response Time: {elapsed:.2f}s")
```

## 🆘 Yardım & Destek

### Debug Dosyaları
```bash
# HTTP başarısız olunca oluşur
cat piccolo_debug.html | head -100

# Selenium başarısız olunca oluşur
cat piccolo_selenium_debug.html | head -100
```

### Logging Seviyeleri
```python
import logging

# Debug mode (çok verbose)
logging.basicConfig(level=logging.DEBUG)

# Info mode (önerilen)
logging.basicConfig(level=logging.INFO)

# Error mode (sadece hatalar)
logging.basicConfig(level=logging.ERROR)
```

### Tambel Çözümler

**Eğer hiçbir şey çalışmazsa:**
```python
# 1. Basit requests dene
response = requests.get('https://www.piccolo.com.tr/', timeout=10)
print(f"Status: {response.status_code}")

# 2. Proxy kullan
session.proxies = {'https': 'https://proxy:8080'}

# 3. VPN / Farklı IP'den dene

# 4. Piccolo destek ekibine ulaş (User-Agent gizli mi?)
```

## 📝 Kontrol Listesi

- [ ] Python 3.8+ kurulu
- [ ] `pip install -r requirements.txt` çalıştırıldı
- [ ] `python3 api_monitor.py` test edildi
- [ ] Ürünler başarıyla çekildi
- [ ] `config.py` Telegram token'ı var
- [ ] `python3 multi_site_monitor.py` çalışıyor
- [ ] Telegram'da ilk notification alındı ✅

## 🎯 İleri Seviye

### Proxy Rotation (Premium)
```python
# Eğer IP block olursa
proxies = [
    'http://proxy1:8080',
    'http://proxy2:8080',
    'http://proxy3:8080',
]

import random
session.proxies = {'http': random.choice(proxies)}
```

### Request Throttling
```python
import time

def scrape_with_delay(monitor):
    products, _ = monitor.scrape_piccolo_api_direct()
    time.sleep(5)  # 5 saniye bekle (rate limit avoid)
    return products
```

### Caching
```python
import json
from datetime import datetime, timedelta

CACHE_FILE = "piccolo_cache.json"
CACHE_EXPIRE = timedelta(hours=1)

def get_with_cache(monitor):
    if os.path.exists(CACHE_FILE):
        data = json.load(open(CACHE_FILE))
        if datetime.now() - datetime.fromisoformat(data['timestamp']) < CACHE_EXPIRE:
            return data['products']
    
    products, _ = monitor.scrape_piccolo_api_direct()
    json.dump({
        'products': products,
        'timestamp': datetime.now().isoformat()
    }, open(CACHE_FILE, 'w'))
    return products
```

---

**Başarıyla kurulum yapıldı! 🎉**

Sorularınız varsa debug dosyaları kontrol etmeyi unutmayın!

