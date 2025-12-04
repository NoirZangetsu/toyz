#!/usr/bin/env python3
"""
Multi-Site Ürün Monitor
Piccolo ve DiecastTurkey sitelerini aynı anda izler.
"""

import os
import time
import threading
import json
from datetime import datetime
from typing import Dict, Set, List, Tuple, Optional

# Piccolo monitor
from api_monitor import (
    get_piccolo_monitor,
    scrape_piccolo_sync,
    setup_piccolo_driver,
    HOT_WHEELS_URL
)

# Telegram yapılandırması
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
except ImportError:
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
    TELEGRAM_ENABLED = False

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

# ToyzzShop monitor
try:
    from toyzzshop_monitor import (
        get_toyzzshop_monitor,
        scrape_toyzzshop_sync
    )
    TOYZZSHOP_AVAILABLE = True
except ImportError:
    TOYZZSHOP_AVAILABLE = False
    print("⚠️  ToyzzShop monitor yüklenemedi.")


def send_telegram_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Telegram bot üzerinden mesaj gönderir.

    Returns:
        (başarı durumu, hata mesajı)
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


class MultiSiteMonitor:
    """
    Birden fazla siteyi aynı anda izleyen monitor sınıfı.
    """

    def __init__(self, interval: int = 180):
        self.interval = interval
        self.running = False
        self.previous_products: Dict[str, Set] = self.load_previous_products()
        self.driver = None  # DiecastTurkey için
        self.piccolo_driver = None  # Piccolo için

    def load_previous_products(self) -> Dict[str, Set]:
        """Önceki ürünleri yükler."""
        try:
            if os.path.exists("previous_products.json"):
                with open("previous_products.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Set'leri yeniden oluştur
                    return {k: set(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def save_previous_products(self):
        """Önceki ürünleri kaydeder."""
        try:
            # Set'leri listeye çevirerek JSON'a uygun hale getir
            data = {k: list(v) for k, v in self.previous_products.items()}
            with open("previous_products.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️  Önceki ürünler kaydedilemedi: {e}")

    def load_telegram_offset(self) -> Optional[int]:
        """Telegram offset'ini yükler."""
        try:
            if os.path.exists("telegram_offset.json"):
                with open("telegram_offset.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("offset")
        except Exception:
            pass
        return None

    def save_telegram_offset(self):
        """Telegram offset'ini kaydeder."""
        try:
            if self.telegram_offset is not None:
                data = {"offset": self.telegram_offset}
                with open("telegram_offset.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️  Telegram offset kaydedilemedi: {e}")
        
    def monitor_piccolo(self) -> None:
        """
        Piccolo Hot Wheels Premium sayfasını izler.
        """
        site_id = "piccolo_hw_premium"

        try:
            # Piccolo için driver kontrolü - yoksa veya kapandıysa yeniden oluştur
            if not self.piccolo_driver:
                print("  🌐 Piccolo Chrome WebDriver başlatılıyor...")
                self.piccolo_driver = setup_piccolo_driver(headless=True)  # Headless mod - arka planda çalışır
                time.sleep(2)  # Driver'ın hazır olmasını bekle
            else:
                # Driver'ın hala açık olduğunu kontrol et
                try:
                    self.piccolo_driver.current_url
                except:
                    print("  🔄 Piccolo Chrome WebDriver yeniden başlatılıyor...")
                    self.piccolo_driver = setup_piccolo_driver(headless=True)
                    time.sleep(2)

            monitor = get_piccolo_monitor()
            products, error = scrape_piccolo_sync(monitor, self.piccolo_driver)

            if error:
                print(f"  ❌ Piccolo: {error}")
                return

            in_stock_products = [p for p in products if p.get("in_stock")]
            print(f"  ✅ Piccolo: {len(products)} ürün bulundu ({len(in_stock_products)} stokta)")

            current_product_ids = {p["id"] for p in products if p.get("id")}

            # İlk çalıştırma kontrolü
            if site_id not in self.previous_products:
                print(f"  ℹ️  Piccolo: İlk çalıştırma - mevcut ürünler kaydedildi")
                self.previous_products[site_id] = current_product_ids

                # İlk çalıştırmada mevcut durumu bildir
                if TELEGRAM_ENABLED:
                    self.send_initial_stock_summary(site_id, "Piccolo Hot Wheels Premium", products, in_stock_products, HOT_WHEELS_URL)
            else:
                # Yeni ürünleri bul
                new_product_ids = current_product_ids - self.previous_products[site_id]

                if new_product_ids:
                    new_products = [p for p in products if p.get("id") in new_product_ids]
                    print(f"  🚨 Piccolo: {len(new_products)} yeni ürün!")

                    # Bildirim mesajı
                    lines = [
                        "🚨 <b>YENİ ÜRÜN BULUNDU!</b>",
                        "",
                        f"📍 <b>Site:</b> Piccolo Hot Wheels Premium",
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
                            quantity = product.get('quantity', 0)
                            if quantity > 0:
                                lines.append(f"   ✅ Stokta ({quantity} adet)")
                            else:
                                lines.append(f"   ✅ Stokta")
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
                    print(f"  ℹ️  Piccolo: Yeni ürün yok")

            # Veritabanını kaydet
            monitor.save_db()
            self.save_previous_products()

        except Exception as e:
            print(f"  ❌ Piccolo hata: {str(e)[:100]}")

    def send_initial_stock_summary(self, site_id: str, site_name: str, products: List[Dict], in_stock_products: List[Dict], site_url: str):
        """
        İlk çalıştırmada mevcut stok özetini gönderir.
        """
        try:
            # Başlangıç mesajı
            lines = [
                f"📊 <b>{site_name}</b> izleme başladı!",
                "",
                f"📦 Toplam ürün: {len(products)}",
                f"✅ Stokta olan: {len(in_stock_products)}",
                ""
            ]

            if in_stock_products:
                lines.append("📋 <b>Mevcut Stok:</b>")
                lines.append("")

                for i, product in enumerate(in_stock_products[:10], 1):
                    name = product.get('name', 'İsimsiz Ürün')
                    if len(name) > 50:
                        name = name[:47] + "..."

                    code = product.get('code', '')
                    price = product.get('price', 'Fiyat yok')
                    quantity = product.get('quantity', 0)

                    lines.append(f"{i}. <b>{name}</b>")
                    if code:
                        lines.append(f"   🏷️ {code}")
                    lines.append(f"   💰 {price}")
                    if quantity > 0:
                        lines.append(f"   📦 {quantity} adet")
                    lines.append("")

                if len(in_stock_products) > 10:
                    lines.append(f"... ve {len(in_stock_products) - 10} ürün daha")

                lines.append("🎯 Sistem hazır! Yeni ürünler eklendiğinde bildirim alacaksınız.")
            else:
                lines.append("⚠️ Şu anda stokta ürün bulunmuyor.")
                lines.append("🔄 Sistem çalışmaya devam ediyor...")
                lines.append("🎯 Yeni ürünler eklendiğinde otomatik bildirim alacaksınız.")

            lines.append("")
            lines.append(f"🔗 <a href='{site_url}'>Mağazaya Git</a>")

            message = "\n".join(lines)
            success, error = send_telegram_message(message)
            if success:
                print(f"  📤 {site_name} başlangıç özeti gönderildi")
            else:
                print(f"  ❌ {site_name} başlangıç özeti gönderilemedi: {error}")

        except Exception as e:
            print(f"  ❌ Başlangıç özeti hatası: {str(e)[:100]}")

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

                    # İlk çalıştırmada mevcut durumu bildir
                    if TELEGRAM_ENABLED:
                        self.send_initial_stock_summary(site_id, site_name, products, in_stock_products, site_url)
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

                self.save_previous_products()

        except Exception as e:
            print(f"  ❌ DiecastTurkey hata: {str(e)[:100]}")

    def monitor_toyzzshop(self) -> None:
        """
        ToyzzShop sitesini izler.
        """
        if not TOYZZSHOP_AVAILABLE:
            return

        site_id = "toyzzshop"

        try:
            monitor = get_toyzzshop_monitor()
            products, error = scrape_toyzzshop_sync(monitor)

            if error:
                print(f"  ❌ ToyzzShop: {error}")
                return

            in_stock_products = [p for p in products if p.get("in_stock")]
            print(f"  ✅ ToyzzShop: {len(products)} ürün bulundu ({len(in_stock_products)} stokta)")

            current_product_ids = {p["id"] for p in products if p.get("id")}

            # İlk çalıştırma kontrolü
            if site_id not in self.previous_products:
                print(f"  ℹ️  ToyzzShop: İlk çalıştırma - mevcut ürünler kaydedildi")
                self.previous_products[site_id] = current_product_ids

                # İlk çalıştırmada mevcut durumu bildir
                if TELEGRAM_ENABLED:
                    self.send_initial_stock_summary(site_id, "ToyzzShop Hot Wheels", products, in_stock_products, "https://www.toyzzshop.com/oyuncak-araba?q=brands/3657/exclusive/true/order/ovd")
            else:
                # Yeni ürünleri bul
                new_product_ids = current_product_ids - self.previous_products[site_id]

                if new_product_ids:
                    new_products = [p for p in products if p.get("id") in new_product_ids]
                    print(f"  🚨 ToyzzShop: {len(new_products)} yeni ürün!")

                    # Bildirim mesajı
                    lines = [
                        "🚨 <b>YENİ ÜRÜN BULUNDU!</b>",
                        "",
                        f"📍 <b>Site:</b> ToyzzShop Hot Wheels",
                        f"✨ <b>Yeni ürün sayısı:</b> {len(new_products)}",
                        "",
                    ]

                    for idx, product in enumerate(new_products[:5], 1):  # İlk 5 ürün
                        lines.append(f"{idx}. <b>{product['name']}</b>")

                        if product.get('price'):
                            lines.append(f"   💰 {product['price']}")

                        if product.get('in_stock'):
                            lines.append(f"   ✅ Stokta")
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
                    print(f"  ℹ️  ToyzzShop: Yeni ürün yok")

            # Veritabanını kaydet
            monitor.save_db()
            self.save_previous_products()

        except Exception as e:
            print(f"  ❌ ToyzzShop hata: {str(e)[:100]}")


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

        if TOYZZSHOP_AVAILABLE:
            print("📍 ToyzzShop")
            self.monitor_toyzzshop()
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
        if TOYZZSHOP_AVAILABLE:
            print("   • ToyzzShop (Hot Wheels)")
        print(f"\n⏱️  Kontrol aralığı: {self.interval} saniye")
        if TELEGRAM_ENABLED:
            print("📱 Telegram bildirimleri: AKTİF")
        else:
            print("📱 Telegram bildirimleri: KAPALI")
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
                print("✅ DiecastTurkey Chrome WebDriver kapatıldı.")
            if self.piccolo_driver:
                self.piccolo_driver.quit()
                print("✅ Piccolo Chrome WebDriver kapatıldı.")


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

