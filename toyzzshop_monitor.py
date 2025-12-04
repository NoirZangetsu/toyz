#!/usr/bin/env python3
"""
ToyzzShop Ürün Monitor
ToyzzShop sitesi için Playwright kullanarak ürün stoklarını izler.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright

# Telegram yapılandırması
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    from api_monitor import send_telegram_message
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
except ImportError:
    TELEGRAM_ENABLED = False

# ToyzzShop URL
TOYZZSHOP_URL = "https://www.toyzzshop.com/oyuncak-araba?q=brands/3657/exclusive/true/order/ovd"
TOYZZSHOP_DB_FILE = "toyzzshop_stock_db.json"


class ToyzzShopMonitor:
    """
    ToyzzShop sitesi için ürün stok monitor sınıfı.
    """

    def __init__(self):
        self.seen_products = self.load_db()

    def load_db(self) -> Dict:
        """Veritabanını yükler."""
        if os.path.exists(TOYZZSHOP_DB_FILE):
            try:
                with open(TOYZZSHOP_DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️  ToyzzShop veritabanı bozuk, yeniden oluşturulacak.")
                return {}
        return {}

    def save_db(self):
        """Veritabanını kaydeder."""
        with open(TOYZZSHOP_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.seen_products, f, ensure_ascii=False, indent=4)

    async def scrape_toyzzshop_products(self) -> Tuple[List[Dict], Optional[str]]:
        """
        ToyzzShop sitesinden ürünleri çeker.

        Returns:
            (ürün listesi, hata mesajı) tuple'ı
        """
        products = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                await page.goto(TOYZZSHOP_URL, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)

                # Sayfa yüklenmesini tetikle
                for i in range(5):
                    await page.evaluate(f"window.scrollTo(0, {i * 500})")
                    await page.wait_for_timeout(1000)

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)

                # Ürün seçicileri
                selectors_to_try = [
                    "._product_container_18mk3_111",
                    "._products_wrapper_18mk3_108 ._product_container_18mk3_111",
                    ".product-box",
                    ".product-item",
                    ".product-card",
                    ".product",
                    "[data-product]",
                    ".item",
                    ".card"
                ]

                used_selector = None
                product_elements = []

                for selector in selectors_to_try:
                    product_elements = await page.query_selector_all(selector)
                    if len(product_elements) > 0:
                        used_selector = selector
                        break

                if len(product_elements) == 0:
                    await browser.close()
                    return [], "Hiçbir ürün seçici çalışmadı"

                for i, item in enumerate(product_elements):
                    try:
                        # Ürün bilgilerini çıkar
                        container_text = await item.inner_text()
                        lines = [line.strip() for line in container_text.split('\n') if line.strip()]

                        # Ürün ID oluştur
                        product_id = f"toyzz_{i}"

                        # Ürün ismini çıkar
                        name = "İsimsiz Ürün"
                        team_name = ""
                        base_name = ""

                        if len(lines) >= 3:
                            full_name = lines[2]
                            if "(" in full_name and ")" in full_name:
                                base_name = full_name.split("(")[0].strip()
                                team_name = full_name.split("(")[1].split(")")[0].strip()
                                if " – " in team_name:
                                    team_name = team_name.split(" – ")[-1]

                        # Fiyatı çıkar
                        price = "0 TL"
                        for line in lines:
                            if ("TL" in line or "₺" in line) and any(c.isdigit() for c in line):
                                price = line
                                break

                        # Ürün adı için gösterilecek metni belirle
                        display_name = team_name if team_name else base_name
                        if not display_name or display_name in ["Yeni", "İsimsiz Ürün"]:
                            for line in lines:
                                if line not in ["Yeni", "Sadece Toyzz Shop'ta"] and len(line) > 5:
                                    if "(" in line and ")" in line:
                                        display_name = line
                                        break
                            if not display_name or display_name in ["Yeni", "İsimsiz Ürün"]:
                                display_name = "Bilinmeyen Ürün"

                        # Stok kontrolü
                        is_in_stock = False
                        if "Sepete Ekle" in container_text:
                            is_in_stock = True
                        elif any(phrase in container_text for phrase in ["Stokta Yok", "Tükendi", "Haber Ver", "Bitti"]):
                            is_in_stock = False
                        else:
                            is_in_stock = True

                        # Ürün URL'i
                        url = TOYZZSHOP_URL

                        product = {
                            "id": product_id,
                            "name": display_name,
                            "price": price,
                            "url": url,
                            "in_stock": is_in_stock
                        }

                        products.append(product)

                    except Exception as e:
                        print(f"Ürün ayrıştırılırken hata: {e}")
                        continue

                await browser.close()

        except Exception as e:
            return [], f"ToyzzShop scraping hatası: {str(e)}"

        return products, None


def setup_toyzzshop_monitor():
    """
    ToyzzShop monitor örneği oluşturur.
    """
    return ToyzzShopMonitor()


def scrape_toyzzshop_sync(monitor: ToyzzShopMonitor) -> Tuple[List[Dict], Optional[str]]:
    """
    Senkron wrapper fonksiyon - asyncio event loop ile çalıştırır.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Eğer zaten çalışan bir loop varsa, yeni bir thread'de çalıştır
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, monitor.scrape_toyzzshop_products())
                return future.result()
        else:
            return loop.run_until_complete(monitor.scrape_toyzzshop_products())
    except RuntimeError:
        # Event loop bulunamadıysa yeni oluştur
        return asyncio.run(monitor.scrape_toyzzshop_products())


# Global monitor instance
_toyzzshop_monitor = None

def get_toyzzshop_monitor():
    """Global ToyzzShop monitor instance'ını döndürür."""
    global _toyzzshop_monitor
    if _toyzzshop_monitor is None:
        _toyzzshop_monitor = ToyzzShopMonitor()
    return _toyzzshop_monitor
