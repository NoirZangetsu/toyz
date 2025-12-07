#!/bin/bash
# Google Cloud'da Piccolo test'i çalıştır

echo "==============================================="
echo "🚀 Google Cloud Piccolo Test"
echo "==============================================="
echo ""

cd ~/toyz

# venv check
if [ ! -d "venv" ]; then
    echo "❌ venv bulunamadı!"
    echo "Setup: python3 -m venv venv"
    exit 1
fi

# Aktivate
source venv/bin/activate

echo "✅ venv aktivate edildi"
echo ""

# Export
export PYTHONIOENCODING=utf-8

echo "🧪 Test başlıyor..."
echo ""

# Test et
python test_piccolo_simple.py

echo ""
echo "==============================================="

