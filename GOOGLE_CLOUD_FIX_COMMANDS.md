# 🔧 Google Cloud'da Piccolo Fix - Komutlar

## 🚀 Tek Komut (Copy & Paste)

```bash
# Google Cloud VM'de çalıştır:
cd ~/toyz && source venv/bin/activate && python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from api_monitor import get_piccolo_monitor, setup_piccolo_driver
monitor = get_piccolo_monitor()
driver = setup_piccolo_driver()
try:
    products, error = monitor.scrape_piccolo_products(driver)
    if error:
        print(f'❌ Hata: {error}')
    else:
        print(f'✅ {len(products)} ürün bulundu!')
finally:
    driver.quit()
"
```

---

## 📋 Adım Adım Komutlar

### 1. SSH'ye Bağlan

```bash
gcloud compute ssh instance-name --zone=us-central1-a

# Veya:
ssh -i ~/.ssh/google_compute_engine bugrauluirmak2@your-instance-ip
```

### 2. Projeye Git

```bash
cd ~/toyz
```

### 3. venv Aktivate Et

```bash
source venv/bin/activate
```

### 4. Güncellenmiş Kodu Çek (Git)

```bash
# Eğer git repo'dan çektiyse:
git pull origin main

# Veya manuel güncelle (local'den scp ile)
# Local terminal'den:
gcloud compute scp api_monitor.py instance-name:~/toyz/ --zone=us-central1-a
```

### 5. DEBUG Mode'de Test Et (Headless'i Kapat)

```bash
# Debug script oluştur
cat > ~/toyz/test_debug.py << 'EOF'
#!/usr/bin/env python3
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.DEBUG)

chrome_options = Options()
# HEADLESS'İ KAPATTIK - Debug için
# chrome_options.add_argument("--headless=new")

chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print("🌐 Sayfaya gidiyor...")
    driver.get("https://www.piccolo.com.tr/hot-wheels-premium")
    
    print("⏳ 5 saniye bekleniyor...")
    time.sleep(5)
    
    print("📊 JavaScript çalıştırılıyor...")
    result = driver.execute_script("""
    let ids = [];
    const seen = new Set();
    
    // data-id
    document.querySelectorAll('[data-id]').forEach(el => {
        const id = el.getAttribute('data-id');
        if (id && !seen.has(id)) {
            seen.add(id);
            ids.push(id);
        }
    });
    
    return {
        ids: ids,
        data_id_count: document.querySelectorAll('[data-id]').length,
        page_title: document.title,
        html_length: document.documentElement.outerHTML.length
    };
    """)
    
    print(f"✅ Bulundu: {len(result['ids'])} ID")
    print(f"📊 data-id elements: {result['data_id_count']}")
    print(f"📄 Page title: {result['page_title']}")
    print(f"📏 HTML size: {result['html_length']} bytes")
    
    # HTML'i kaydet
    with open("google_cloud_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    
    print("💾 google_cloud_page.html kaydedildi")
    
finally:
    print("\n⏳ 10 saniye daha açık kalacak...")
    time.sleep(10)
    driver.quit()
EOF

python test_debug.py
```

### 6. Normal Mode'de Çalıştır

```bash
# Test et
python api_monitor.py

# Çıktı başarılı ise, Monitor'u başlat
screen -S piccolo
python multi_site_monitor.py 180

# Detach: Ctrl+A, D
```

---

## 🔍 Debug İçin Log'ları Kontrol Et

### Google Cloud'da

```bash
# Real-time log görmek
tail -f piccolo_debug.html

# Hata araması
grep "bulunamadı\|error\|❌" monitor.log

# ID sayısı kontrol
grep "ID'si bulundu" monitor.log

# Son 50 satırı görmek
tail -50 monitor.log
```

### Local'e Log'ları İndir

```bash
# Local terminal'den:
gcloud compute scp instance-name:~/toyz/monitor.log . --zone=us-central1-a
gcloud compute scp instance-name:~/toyz/google_cloud_page.html . --zone=us-central1-a
gcloud compute scp instance-name:~/toyz/piccolo_debug.html . --zone=us-central1-a

# Daha sonra local'de aç
cat monitor.log
```

---

## 📜 Full Setup + Fix Script

Hepsini birden çalıştırmak için:

```bash
cat > ~/toyz/setup_and_fix.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "📦 Setup başlıyor..."

# 1. Proje dizinine git
cd ~/toyz
echo "✅ Proje dizinine gidildi"

# 2. venv oluştur/aktivate et
if [ ! -d "venv" ]; then
    echo "🐍 venv oluşturuluyor..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✅ venv aktivate edildi"

# 3. Paketleri yükle
echo "📚 Paketler yükleniyor..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
playwright install -q
echo "✅ Paketler yüklendi"

# 4. Git'ten güncellemeleri çek
echo "📥 Git güncellemeleri çekiliyor..."
git pull origin main || echo "⚠️  Git pull başarısız, devam ediliyor..."

# 5. Config kontrol et
if [ -f "config.py" ]; then
    echo "✅ config.py bulundu"
else
    echo "❌ config.py bulunamadı!"
    exit 1
fi

# 6. Test et
echo "🧪 Test çalıştırılıyor..."
export PYTHONIOENCODING=utf-8
python api_monitor.py

echo ""
echo "✅ Setup tamamlandı!"
echo "📍 Monitor'u başlatmak için:"
echo "   screen -S piccolo"
echo "   python multi_site_monitor.py 180"
SCRIPT

chmod +x setup_and_fix.sh
./setup_and_fix.sh
```

---

## 🎯 Hızlı Referans

```bash
# Google Cloud'da şu sırayla çalıştır:

# 1. Bağlan
gcloud compute ssh instance-name --zone=us-central1-a

# 2. Setup + Fix
cd ~/toyz && bash setup_and_fix.sh

# 3. Monitor başlat (background)
screen -S piccolo
source venv/bin/activate
export PYTHONIOENCODING=utf-8
python multi_site_monitor.py 180
# Detach: Ctrl+A, D

# 4. Status kontrol
screen -ls

# 5. Log görmek
tail -f monitor.log

# 6. Session'a geri dön
screen -r piccolo
```

---

## 🆘 Hala Sorun Varsa

### Hata: "0 ID bulundu"

```bash
# Debug mode'de çalıştır
python test_debug.py

# google_cloud_page.html'i kontrol et
cat google_cloud_page.html | head -100

# ID sayısını say
grep -o 'data-id="[^"]*"' google_cloud_page.html | wc -l
```

### Hata: "Chrome bulunamadı"

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

### Hata: "Playwright browser bulunamadı"

```bash
source venv/bin/activate
playwright install
```

---

## ✅ Başarılı Çıktı Örneği

```
✅ 10 ürün ID'si bulundu
🌐 API çağrısı: 10 ürün için...
✅ API'den 10 ürün çekildi
✅ BAŞARILI! 10 ürün bulundu
```

---

**Hangi adımda sorun yaşıyorsun? Sor!** 🚀

