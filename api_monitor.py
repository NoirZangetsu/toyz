#!/usr/bin/env python3
"""
Piccolo Ürün Monitor - Simplified
Selenium + Cloudflare bypass ana yöntem
"""

import os
import time
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram yapılandırması
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
except ImportError:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Piccolo URLs
HOT_WHEELS_URL = "https://www.piccolo.com.tr/hot-wheels-premium"
API_URL = "https://www.piccolo.com.tr/api/Product/GetProductCategoryHierarchy"
PICCOLO_DB_FILE = "piccolo_stock_db.json"


def setup_piccolo_driver(headless: bool = True) -> webdriver.Chrome:
    """Chrome WebDriver - Cloudflare & Google Cloud optimized"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Google Cloud optimizations
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    
    # Bot detection evasion
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Page load strategy
    chrome_options.page_load_strategy = 'normal'
    
    # Disable notifications
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2
    })
    
    # Automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # WebDriver Manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Hide webdriver property via CDP
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    return driver


class PiccoloMonitor:
    """Piccolo monitor - Selenium-based"""
    
    def __init__(self):
        self.seen_products = self.load_db()
        logger.info("✅ PiccoloMonitor başlatıldı")
    
    def load_db(self) -> Dict:
        """Veritabanı yükle"""
        if os.path.exists(PICCOLO_DB_FILE):
            try:
                with open(PICCOLO_DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("⚠️  Database corrupted, yeni oluşturuluyor...")
                return {}
        return {}
    
    def save_db(self):
        """Veritabanı kaydet"""
        try:
            with open(PICCOLO_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.seen_products, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"❌ Database kaydetme hatası: {e}")
    
    def scrape_piccolo_products(self, driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
        """
        Selenium ile Piccolo'dan ürünleri çek
        1. Sayfayı yükle (Cloudflare bypass)
        2. JavaScript ile ürün ID'lerini çıkart
        3. API'den ürün detaylarını al
        """
        logger.info("🔄 Selenium yöntemi başlıyor...")
        
        try:
            # Sayfayı yükle
            logger.info(f"  🌐 Sayfaya gidiyor: {HOT_WHEELS_URL}")
            driver.get(HOT_WHEELS_URL)
            
            # Cloudflare challenge çözülmesini bekle
            logger.info("  ⏳ Cloudflare challenge çözülüyor (5s)...")
            time.sleep(5)
            
            # Document ready
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                logger.info("  ✅ Document ready")
            except TimeoutException:
                logger.warning("  ⚠️  Document ready timeout, devam ediliyor...")
            
            time.sleep(2)
            
            # Cookie banner
            try:
                cookie_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kabul')]"))
                )
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            # JavaScript ile ürün ID'lerini çıkart
            logger.info("  🔍 JavaScript ile ürün ID'leri çıkarılıyor...")
            
            js_code = """
            let ids = [];
            const seen = new Set();
            
            // Method 1: data-id attribute (ana yöntem)
            try {
                document.querySelectorAll('[data-id]').forEach(el => {
                    const id = el.getAttribute('data-id');
                    if (id && !seen.has(id)) {
                        seen.add(id);
                        ids.push(id);
                    }
                });
            } catch(e) {}
            
            // Method 2: data-product-id attribute
            if (ids.length === 0) {
                try {
                    document.querySelectorAll('[data-product-id]').forEach(el => {
                        const id = el.getAttribute('data-product-id');
                        if (id && !seen.has(id)) {
                            seen.add(id);
                            ids.push(id);
                        }
                    });
                } catch(e) {}
            }
            
            // Method 3: URL'den ID çıkart (fallback)
            if (ids.length === 0) {
                try {
                    document.querySelectorAll('a[href*="hot-wheels-premium"]').forEach(a => {
                        const href = a.href;
                        const match = href.match(/(\\d+)[^\\d]*$/);
                        if (match && match[1]) {
                            if (!seen.has(match[1])) {
                                seen.add(match[1]);
                                ids.push(match[1]);
                            }
                        }
                    });
                } catch(e) {}
            }
            
            return ids;
            """
            
            product_ids = driver.execute_script(js_code)
            logger.info(f"  ✅ {len(product_ids)} ürün ID'si bulundu")
            
            if not product_ids:
                # Scroll dene
                logger.warning("  ⚠️  ID bulunamadı, scroll yapılıyor...")
                for i in range(5):
                    driver.execute_script("window.scrollBy(0, window.innerHeight)")
                    time.sleep(1)
                
                product_ids = driver.execute_script(js_code)
                logger.info(f"  ↻ Scroll sonrası: {len(product_ids)} ID")
            
            if not product_ids:
                return [], "Selenium'den ürün ID'si bulunamadı"
            
            # API'den ürün detaylarını al
            return self._fetch_products_from_api(product_ids)
            
        except Exception as e:
            logger.error(f"  ❌ Selenium hatası: {str(e)[:100]}")
            return [], str(e)[:100]
    
    def _fetch_products_from_api(self, product_ids: List[str]) -> Tuple[List[Dict], Optional[str]]:
        """API'den ürün detaylarını çek"""
        if not product_ids:
            return [], "Ürün ID'si yok"
        
        logger.info(f"  🌐 API çağrısı: {len(product_ids)} ürün için...")
        
        try:
            # Headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'tr-TR',
                'Referer': 'https://www.piccolo.com.tr/hot-wheels-premium'
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            all_products = []
            batch_size = 100
            
            for i in range(0, len(product_ids), batch_size):
                batch = product_ids[i:i + batch_size]
                product_ids_str = ','.join(str(pid) for pid in batch)
                api_url = f"{API_URL}?c=trtry0000&productIds={product_ids_str}"
                
                logger.debug(f"    Batch {i // batch_size + 1}: {len(batch)} ürün")
                
                try:
                    response = session.get(api_url, timeout=20)
                    response.raise_for_status()
                    api_data = response.json()
                    
                    if not api_data or "productCategoryTreeList" not in api_data:
                        logger.warning(f"    ⚠️  Batch {i // batch_size + 1}: Yanıt eksik")
                        continue
                    
                    for item in api_data["productCategoryTreeList"]:
                        if not isinstance(item, dict):
                            continue
                        
                        product_id = str(item.get("productId", ""))
                        if not product_id:
                            continue
                        
                        product = {
                            "id": product_id,
                            "name": f"Hot Wheels Ürün #{product_id}",  # Basit name
                            "code": "",
                            "price": "Bilgi alınamadı",
                            "url": f"https://www.piccolo.com.tr/hot-wheels-premium/{product_id}/",
                            "image": "",
                            "brand": "Hot Wheels",
                            "in_stock": True,
                            "quantity": 0
                        }
                        
                        all_products.append(product)
                
                except Exception as e:
                    logger.warning(f"    ⚠️  Batch hatası: {str(e)[:50]}")
                    continue
            
            logger.info(f"  ✅ API'den {len(all_products)} ürün çekildi")
            return all_products, None
        
        except Exception as e:
            return [], f"API hatası: {str(e)[:50]}"


def scrape_piccolo_sync(monitor: 'PiccoloMonitor', driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
    """Wrapper - Selenium driver ile çalıştırır"""
    return monitor.scrape_piccolo_products(driver)


# Global singleton
_piccolo_monitor = None

def get_piccolo_monitor():
    """Global Piccolo monitor instance'ını döndürür"""
    global _piccolo_monitor
    if _piccolo_monitor is None:
        _piccolo_monitor = PiccoloMonitor()
    return _piccolo_monitor


# ==================== TEST ====================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 Piccolo Monitor Test (Selenium Only)")
    print("=" * 70 + "\n")
    
    monitor = get_piccolo_monitor()
    driver = setup_piccolo_driver()
    
    try:
        products, error = scrape_piccolo_sync(monitor, driver)
        
        if error:
            print(f"❌ Hata: {error}\n")
        else:
            print(f"✅ BAŞARILI! {len(products)} ürün bulundu\n")
            
            if products:
                print("İlk 5 ürün:")
                for i, p in enumerate(products[:5], 1):
                    print(f"  {i}. {p['name']} - {p['code']} - {p['price']}")
            
            # Kaydet
            monitor.seen_products = {p['id']: p for p in products}
            monitor.save_db()
            print(f"\n💾 Veritabanı kaydedildi")
        
    finally:
        driver.quit()
    
    print("\n" + "=" * 70)
