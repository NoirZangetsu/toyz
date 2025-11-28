#!/usr/bin/env python3
"""
DiecastTurkey Ürün Monitor
Selenium kullanarak DiecastTurkey'den Hot Wheels ürünlerini takip eder.
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException

# Telegram yapılandırması
try:
    from config import (
        TELEGRAM_BOT_TOKEN as CONFIG_TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID as CONFIG_TELEGRAM_CHAT_ID,
    )
    TELEGRAM_BOT_TOKEN = CONFIG_TELEGRAM_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = CONFIG_TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "")
except ImportError:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# DiecastTurkey URL'leri
DIECASTTURKEY_URLS = [
    {
        "name": "DiecastTurkey Hot Wheels",
        "url": "https://www.diecastturkey.com/hot-wheels-12",
        "site_id": "diecastturkey_hw"
    }
]


def send_telegram_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Telegram bot üzerinden mesaj gönderir.
    """
    if not TELEGRAM_ENABLED:
        return False, "Telegram yapılandırması eksik."
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Chrome WebDriver'ı yapılandırır.
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def scrape_diecastturkey_products(url: str, driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
    """
    DiecastTurkey'den ürünleri çeker.
    
    Returns:
        (ürün listesi, hata mesajı)
    """
    products = []
    
    try:
        print(f"  🌐 Sayfa yükleniyor: {url}")
        driver.get(url)
        
        # Sayfanın yüklenmesini bekle
        time.sleep(3)
        
        # Cookie banner'ı kapat (varsa)
        try:
            cookie_accept = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kabul') or contains(text(), 'Accept') or contains(@class, 'cookie')]"))
            )
            cookie_accept.click()
            time.sleep(1)
        except (TimeoutException, NoSuchElementException):
            pass
        
        # PRODUCT_DATA JavaScript array'ini oku
        try:
            # JavaScript'ten PRODUCT_DATA'yı al
            product_data_script = """
            if (typeof PRODUCT_DATA !== 'undefined' && Array.isArray(PRODUCT_DATA)) {
                return PRODUCT_DATA;
            }
            return [];
            """
            
            product_data = driver.execute_script(product_data_script)
            
            if not product_data:
                return [], "PRODUCT_DATA bulunamadı veya boş"
            
            print(f"  ✅ {len(product_data)} ürün bulundu (PRODUCT_DATA)")
            
            # Her ürünü formatla
            for item in product_data:
                try:
                    # Stok kontrolü - quantity 0'dan büyükse stokta var
                    in_stock = int(item.get("quantity", 0)) > 0
                    
                    # Sadece stokta olan ürünleri al (isteğe bağlı)
                    # if not in_stock:
                    #     continue
                    
                    product = {
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "code": item.get("code", ""),
                        "supplier_code": item.get("supplier_code", ""),
                        "price": f"{item.get('total_sale_price', 0)} {item.get('currency', 'TL')}",
                        "url": f"https://www.diecastturkey.com/{item.get('url', '')}",
                        "image": item.get("image", ""),
                        "brand": item.get("brand", ""),
                        "category": item.get("category", ""),
                        "quantity": item.get("quantity", 0),
                        "in_stock": in_stock
                    }
                    
                    products.append(product)
                    
                except Exception as e:
                    print(f"  ⚠️  Ürün parse edilemedi: {str(e)[:50]}")
                    continue
            
            return products, None
            
        except JavascriptException as e:
            return [], f"JavaScript hatası: {str(e)[:100]}"
        
    except Exception as e:
        return [], f"Scraping hatası: {str(e)[:100]}"


def notify_new_products(site_name: str, new_products: List[Dict]) -> None:
    """
    Yeni ürünler için Telegram bildirimi gönderir.
    """
    if not new_products:
        return
    
    print(f"  🚨 {len(new_products)} yeni ürün bulundu!")
    
    # Mesaj oluştur
    lines = [
        f"🚨 <b>YENİ ÜRÜN BULUNDU!</b>",
        f"",
        f"📍 <b>Site:</b> {site_name}",
        f"✨ <b>Yeni ürün sayısı:</b> {len(new_products)}",
        f"",
    ]
    
    for idx, product in enumerate(new_products[:10], 1):  # İlk 10 ürün
        lines.append(f"{idx}. <b>{product['name']}</b>")
        
        if product.get('code'):
            lines.append(f"   🏷️ Kod: {product['code']}")
        
        if product.get('price'):
            lines.append(f"   💰 {product['price']}")
        
        # Stok durumu
        if product.get('in_stock'):
            lines.append(f"   ✅ Stokta var (Miktar: {product.get('quantity', 0)})")
        else:
            lines.append(f"   ⚠️ Stokta yok")
        
        if product.get('url'):
            lines.append(f"   🔗 <a href='{product['url']}'>Ürüne Git</a>")
        
        lines.append("")
    
    if len(new_products) > 10:
        lines.append(f"... ve {len(new_products) - 10} ürün daha")
    
    message = "\n".join(lines)
    
    # Telegram'a gönder
    if TELEGRAM_ENABLED:
        success, error = send_telegram_message(message)
        if success:
            print("  📱 Telegram bildirimi gönderildi.")
        else:
            print(f"  ❌ Telegram hatası: {error}")
    else:
        print("  ℹ️  Telegram yapılandırması eksik.")


def monitor_diecastturkey(interval: int = 300, continuous: bool = True):
    """
    DiecastTurkey ürünlerini periyodik olarak kontrol eder.
    
    Args:
        interval: Kontrol aralığı (saniye)
        continuous: Sürekli kontrol modu
    """
    print("=" * 70)
    print("🔍 DiecastTurkey Ürün Monitor")
    print("=" * 70)
    print(f"⏱️  Kontrol aralığı: {interval} saniye")
    print(f"📍 İzlenen URL sayısı: {len(DIECASTTURKEY_URLS)}")
    print("=" * 70)
    print()
    
    # Her site için önceki ürün listesi
    previous_products: Dict[str, Set[str]] = {}
    check_count = 0
    
    # WebDriver'ı başlat
    driver = None
    
    try:
        driver = setup_driver(headless=True)
        print("✅ Chrome WebDriver başlatıldı\n")
        
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n{'='*70}")
            print(f"[{timestamp}] Kontrol #{check_count}")
            print(f"{'='*70}\n")
            
            for site_config in DIECASTTURKEY_URLS:
                site_id = site_config["site_id"]
                site_name = site_config["name"]
                site_url = site_config["url"]
                
                print(f"📍 {site_name}")
                print(f"   URL: {site_url}")
                
                # Ürünleri çek
                products, error = scrape_diecastturkey_products(site_url, driver)
                
                if error:
                    print(f"  ❌ {error}")
                    continue
                
                print(f"  ✅ {len(products)} ürün bulundu")
                
                # Stokta olan ürünler
                in_stock_products = [p for p in products if p.get("in_stock")]
                print(f"  📦 Stokta: {len(in_stock_products)} ürün")
                
                # Ürün ID setini oluştur
                current_product_ids = {p["id"] for p in products if p.get("id")}
                
                # İlk çalıştırma kontrolü
                if site_id not in previous_products:
                    print(f"  ℹ️  İlk çalıştırma - mevcut ürünler kaydedildi")
                    previous_products[site_id] = current_product_ids
                    
                    # İlk özeti gönder
                    if TELEGRAM_ENABLED and products:
                        summary = [
                            f"📊 <b>{site_name}</b> izleme başladı.",
                            f"",
                            f"📦 Toplam ürün sayısı: {len(products)}",
                            f"✅ Stokta olan ürün sayısı: {len(in_stock_products)}",
                            f"🔗 <a href='{site_url}'>Sayfaya Git</a>"
                        ]
                        send_telegram_message("\n".join(summary))
                else:
                    # Yeni ürünleri bul
                    new_product_ids = current_product_ids - previous_products[site_id]
                    
                    if new_product_ids:
                        new_products = [p for p in products if p.get("id") in new_product_ids]
                        notify_new_products(site_name, new_products)
                        previous_products[site_id] = current_product_ids
                    else:
                        print(f"  ℹ️  Yeni ürün yok")
                
                print()
            
            if not continuous:
                break
            
            print(f"⏳ {interval} saniye sonra tekrar kontrol edilecek...\n")
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n🛑 İzleme durduruldu.")
    
    finally:
        if driver:
            driver.quit()
            print("✅ Chrome WebDriver kapatıldı.")


if __name__ == "__main__":
    import sys
    
    interval = 300  # Varsayılan 5 dakika
    continuous = True
    
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Geçersiz aralık: {sys.argv[1]}. Varsayılan 300 saniye kullanılıyor.")
    
    if len(sys.argv) > 2 and sys.argv[2].lower() == "once":
        continuous = False
    
    monitor_diecastturkey(interval=interval, continuous=continuous)

