#!/bin/bash
# Google Cloud'da Piccolo Monitor Setup Script
# Lokalde ve Cloud'da optimize edilmiş versiyon

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
pip install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt
echo "✅ Paketler yüklendi"

# 4. Chrome kur (eğer yoksa)
if ! command -v google-chrome &> /dev/null; then
    echo "🌐 Google Chrome kuruluyor..."
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list'
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo apt update -qq
    sudo apt install -y google-chrome-stable -qq
    echo "✅ Google Chrome kuruldu"
fi

# 5. ChromeDriver cache temizle (version mismatch'i önlemek için)
rm -rf ~/.wdm/ 2>/dev/null || true
echo "✅ WebDriver cache temizlendi"

# 6. Playwright browser'larını kur
echo "📦 Playwright browser'ları kuruluyor..."
playwright install chromium 2>/dev/null || true
echo "✅ Playwright hazır"

# 7. Git'ten güncellemeleri çek
echo "📥 Git güncellemeleri çekiliyor..."
git pull origin main 2>/dev/null || echo "⚠️  Git pull başarısız, devam ediliyor..."

# 8. Config kontrol et
if [ ! -f "config.py" ]; then
    echo "❌ config.py bulunamadı!"
    echo "Lütfen config.py'yi düzenle ve TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID ekle"
    exit 1
fi

if grep -q "YOUR_TOKEN\|YOUR_CHAT_ID" config.py; then
    echo "❌ config.py'de placeholder values var!"
    echo "Lütfen config.py'yi düzenle: nano config.py"
    exit 1
fi

echo "✅ config.py kontrol edildi"

# 9. Test et
echo ""
echo "🧪 Test çalıştırılıyor..."
export PYTHONIOENCODING=utf-8
export DISPLAY=""  # Headless mode

python api_monitor.py

echo ""
echo "✅ Setup tamamlandı!"
echo ""
echo "📍 Monitor'u başlatmak için çalışt:"
echo "   screen -S piccolo"
echo "   source venv/bin/activate"
echo "   export PYTHONIOENCODING=utf-8"
echo "   python multi_site_monitor.py 180"
echo ""
echo "💡 Detach etmek için: Ctrl+A, D"
echo "   Geri dönmek için: screen -r piccolo"

