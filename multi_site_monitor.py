#!/usr/bin/env python3
"""
Multi-Site Ürün Monitor
Piccolo ve DiecastTurkey sitelerini aynı anda izler.
"""

import os
import time
import threading
from datetime import datetime
from typing import Dict, Set, List, Tuple, Optional

# Piccolo monitor
from api_monitor import (
    make_api_request,
    extract_products,
    send_telegram_message,
    build_notification_message,
    API_URL,
    API_PARAMS,
    HOT_WHEELS_URL,
    TELEGRAM_ENABLED
)

# DiecastTurkey monitor
try:
    from diecastturkey_monitor import (
        setup_driver,
        scrape_diecastturkey_products,
        DIECASTTURKEY_URLS
    )
    DIECASTTURKEY_AVAILABLE = True
except ImportError:
    DIECASTTURKEY_AVAILABLE = False
    print("⚠️  DiecastTurkey monitor yüklenemedi.")


class MultiSiteMonitor:
    """
    Birden fazla siteyi aynı anda izleyen monitor sınıfı.
    """
    
    def __init__(self, interval: int = 300):
        self.interval = interval
        self.running = False
        self.previous_products: Dict[str, Set] = {}
        self.driver = None
        
    def monitor_piccolo(self) -> None:
        """
        Piccolo API'sini izler.
        """
        site_id = "piccolo_hw_premium"
        
        try:
            response, error = make_api_request()
            
            if error:
                print(f"  ❌ Piccolo: {error}")
                return
            
            if not response:
                print(f"  ⚠️  Piccolo: Yanıt alınamadı")
                return
            
            product_count, product_ids = extract_products(response)
            current_product_set = set(product_ids)
            
            print(f"  ✅ Piccolo: {product_count} ürün bulundu")
            
            # İlk çalıştırma kontrolü
            if site_id not in self.previous_products:
                print(f"  ℹ️  Piccolo: İlk çalıştırma - mevcut ürünler kaydedildi")
                self.previous_products[site_id] = current_product_set
                
                # İlk özet
                if TELEGRAM_ENABLED:
                    summary = [
                        "📊 <b>Piccolo Hot Wheels Premium</b> izleme başladı.",
                        "",
                        f"📦 Mevcut ürün sayısı: {product_count}",
                        f"🆔 Ürün ID'leri: {', '.join(map(str, sorted(product_ids)))}",
                        "",
                        f"🔗 <a href='{HOT_WHEELS_URL}'>Sayfaya Git</a>"
                    ]
                    send_telegram_message("\n".join(summary))
            else:
                # Yeni ürünleri bul
                new_product_ids = sorted(current_product_set - self.previous_products[site_id])
                
                if new_product_ids:
                    print(f"  🚨 Piccolo: {len(new_product_ids)} yeni ürün!")
                    
                    # Bildirim gönder
                    message = [
                        "🚨 <b>YENİ ÜRÜN BULUNDU!</b>",
                        "",
                        "📍 <b>Site:</b> Piccolo Hot Wheels Premium",
                        f"✨ <b>Yeni ürün ID'leri:</b> {', '.join(map(str, new_product_ids))}",
                        f"📦 <b>Toplam ürün sayısı:</b> {product_count}",
                        "",
                        f"🔗 <a href='{HOT_WHEELS_URL}'>Sayfaya Git</a>"
                    ]
                    
                    if TELEGRAM_ENABLED:
                        send_telegram_message("\n".join(message))
                    
                    self.previous_products[site_id] = current_product_set
                else:
                    print(f"  ℹ️  Piccolo: Yeni ürün yok")
        
        except Exception as e:
            print(f"  ❌ Piccolo hata: {str(e)[:100]}")
    
    def monitor_diecastturkey(self) -> None:
        """
        DiecastTurkey sitesini izler.
        """
        if not DIECASTTURKEY_AVAILABLE:
            return
        
        try:
            # Driver kontrolü - yoksa veya kapandıysa yeniden oluştur
            if not self.driver:
                print("  🌐 Chrome WebDriver başlatılıyor...")
                self.driver = setup_driver(headless=True)  # Headless mod - arka planda çalışır
                time.sleep(2)  # Driver'ın hazır olmasını bekle
            else:
                # Driver'ın hala açık olduğunu kontrol et
                try:
                    self.driver.current_url
                except:
                    print("  🔄 Chrome WebDriver yeniden başlatılıyor...")
                    self.driver = setup_driver(headless=True)
                    time.sleep(2)
            
            for site_config in DIECASTTURKEY_URLS:
                site_id = site_config["site_id"]
                site_name = site_config["name"]
                site_url = site_config["url"]
                
                print(f"  🌐 DiecastTurkey: {site_name}")
                
                products, error = scrape_diecastturkey_products(site_url, self.driver)
                
                if error:
                    print(f"    ❌ {error}")
                    continue
                
                in_stock_products = [p for p in products if p.get("in_stock")]
                print(f"    ✅ {len(products)} ürün bulundu ({len(in_stock_products)} stokta)")
                
                current_product_ids = {p["id"] for p in products if p.get("id")}
                
                # İlk çalıştırma kontrolü
                if site_id not in self.previous_products:
                    print(f"    ℹ️  İlk çalıştırma - mevcut ürünler kaydedildi")
                    self.previous_products[site_id] = current_product_ids
                    
                    # İlk özet
                    if TELEGRAM_ENABLED and products:
                        summary = [
                            f"📊 <b>{site_name}</b> izleme başladı.",
                            f"",
                            f"📦 Toplam ürün sayısı: {len(products)}",
                            f"✅ Stokta olan: {len(in_stock_products)}",
                            f"🔗 <a href='{site_url}'>Sayfaya Git</a>"
                        ]
                        send_telegram_message("\n".join(summary))
                else:
                    # Yeni ürünleri bul
                    new_product_ids = current_product_ids - self.previous_products[site_id]
                    
                    if new_product_ids:
                        new_products = [p for p in products if p.get("id") in new_product_ids]
                        print(f"    🚨 {len(new_products)} yeni ürün!")
                        
                        # Bildirim mesajı
                        lines = [
                            "🚨 <b>YENİ ÜRÜN BULUNDU!</b>",
                            "",
                            f"📍 <b>Site:</b> {site_name}",
                            f"✨ <b>Yeni ürün sayısı:</b> {len(new_products)}",
                            "",
                        ]
                        
                        for idx, product in enumerate(new_products[:5], 1):  # İlk 5 ürün
                            lines.append(f"{idx}. <b>{product['name']}</b>")
                            
                            if product.get('code'):
                                lines.append(f"   🏷️ {product['code']}")
                            
                            if product.get('price'):
                                lines.append(f"   💰 {product['price']}")
                            
                            if product.get('in_stock'):
                                lines.append(f"   ✅ Stokta ({product.get('quantity', 0)} adet)")
                            else:
                                lines.append(f"   ⚠️ Stokta yok")
                            
                            if product.get('url'):
                                lines.append(f"   🔗 <a href='{product['url']}'>Ürüne Git</a>")
                            
                            lines.append("")
                        
                        if len(new_products) > 5:
                            lines.append(f"... ve {len(new_products) - 5} ürün daha")
                        
                        if TELEGRAM_ENABLED:
                            send_telegram_message("\n".join(lines))
                        
                        self.previous_products[site_id] = current_product_ids
                    else:
                        print(f"    ℹ️  Yeni ürün yok")
        
        except Exception as e:
            print(f"  ❌ DiecastTurkey hata: {str(e)[:100]}")
    
    def run_check(self) -> None:
        """
        Tüm siteleri tek seferde kontrol eder.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{'='*70}")
        print(f"[{timestamp}] Kontrol Başlıyor")
        print(f"{'='*70}\n")
        
        print("📍 Piccolo")
        self.monitor_piccolo()
        print()
        
        if DIECASTTURKEY_AVAILABLE:
            print("📍 DiecastTurkey")
            self.monitor_diecastturkey()
            print()
    
    def start(self, continuous: bool = True) -> None:
        """
        İzlemeyi başlatır.
        
        Args:
            continuous: Sürekli izleme modu
        """
        print("=" * 70)
        print("🔍 Multi-Site Ürün Monitor")
        print("=" * 70)
        print("📍 İzlenen siteler:")
        print("   • Piccolo (Hot Wheels Premium)")
        if DIECASTTURKEY_AVAILABLE:
            print(f"   • DiecastTurkey ({len(DIECASTTURKEY_URLS)} URL)")
        print(f"\n⏱️  Kontrol aralığı: {self.interval} saniye")
        print("=" * 70)
        print()
        
        self.running = True
        
        try:
            while self.running:
                self.run_check()
                
                if not continuous:
                    break
                
                print(f"⏳ {self.interval} saniye sonra tekrar kontrol edilecek...\n")
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n\n🛑 İzleme durduruldu.")
        
        finally:
            if self.driver:
                self.driver.quit()
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
    
    monitor = MultiSiteMonitor(interval=interval)
    monitor.start(continuous=continuous)

