#!/usr/bin/env python3
"""
Telegram Chat ID Alma Aracı
Bu scripti çalıştırarak Chat ID'nizi öğrenebilirsiniz.
"""

import requests
import json

# config.py'den token'ı oku
try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    print("❌ config.py dosyası bulunamadı!")
    exit(1)

if not TELEGRAM_BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN config.py dosyasında tanımlı değil!")
    exit(1)

print("=" * 60)
print("📱 Telegram Chat ID Alma Aracı")
print("=" * 60)
print()
print("1. Telegram'da botunuza (@NoirsToyzbot) gidin")
print("2. /start komutunu gönderin")
print("3. Bu scripti çalıştırın ve Chat ID'nizi alın")
print()
input("Botunuza /start gönderdikten sonra Enter'a basın...")

try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    
    if not data.get("ok"):
        print(f"❌ Hata: {data.get('description', 'Bilinmeyen hata')}")
        exit(1)
    
    updates = data.get("result", [])
    
    if not updates:
        print("❌ Henüz mesaj bulunamadı. Botunuza /start gönderdiğinizden emin olun.")
        exit(1)
    
    # En son mesajı al
    last_update = updates[-1]
    message = last_update.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_username = chat.get("username", "N/A")
    chat_first_name = chat.get("first_name", "N/A")
    
    if chat_id:
        print()
        print("=" * 60)
        print("✅ Chat ID Bulundu!")
        print("=" * 60)
        print(f"👤 İsim: {chat_first_name}")
        print(f"📱 Kullanıcı Adı: @{chat_username}")
        print(f"🆔 Chat ID: {chat_id}")
        print()
        print("Bu Chat ID'yi config.py dosyasındaki TELEGRAM_CHAT_ID alanına yapıştırın:")
        print()
        print(f'TELEGRAM_CHAT_ID = "{chat_id}"')
        print()
    else:
        print("❌ Chat ID bulunamadı!")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Bağlantı hatası: {e}")
except Exception as e:
    print(f"❌ Hata: {e}")

