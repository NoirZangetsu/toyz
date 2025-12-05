#!/usr/bin/env python3
"""
Piccolo Ürün Monitor
Selenium kullanarak Piccolo'dan Hot Wheels ürünlerini takip eder.
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException
from webdriver_manager.chrome import ChromeDriverManager

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

# Piccolo URL
HOT_WHEELS_URL = "https://www.piccolo.com.tr/hot-wheels-premium"

# API endpoint
API_URL = "https://www.piccolo.com.tr/api/Product/GetProductCategoryHierarchy"
API_BASE_PARAMS = {
    "c": "trtry0000"
}

# Piccolo scraping için database dosyası
PICCOLO_DB_FILE = "piccolo_stock_db.json"


def setup_piccolo_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Piccolo için Chrome WebDriver'ı yapılandırır.
    Google Cloud için optimize edilmiş ayarlar içerir.
    Cloudflare bypass için özel ayarlar eklenmiştir.
    """
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")

    # Google Cloud için gerekli ayarlar
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Cloudflare bypass için daha gerçekçi user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Cloudflare bypass için ek ayarlar
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--lang=tr-TR,tr")
    chrome_options.add_argument("--accept-lang=tr-TR,tr;q=0.9,en;q=0.8")
    
    # Page load strategy - sayfa tam yüklenene kadar bekle
    chrome_options.page_load_strategy = 'normal'  # 'normal', 'eager', 'none'

    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'intl.accept_languages': 'tr-TR,tr;q=0.9,en;q=0.8'
    })
    
    # Bot detection'ı önlemek için
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # WebDriver Manager ile ChromeDriver'ı otomatik olarak yönet
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Bot detection script'lerini devre dışı bırak - Cloudflare bypass için geliştirilmiş
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['tr-TR', 'tr', 'en-US', 'en']
            });
            window.navigator.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
        '''
    })
    
    return driver


class PiccoloMonitor:
    """
    Piccolo sitesi için ürün stok monitor sınıfı.
    """

    def __init__(self):
        self.seen_products = self.load_db()

    def load_db(self) -> Dict:
        """Veritabanını yükler."""
        if os.path.exists(PICCOLO_DB_FILE):
            try:
                with open(PICCOLO_DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️  Piccolo veritabanı bozuk, yeniden oluşturulacak.")
                return {}
        return {}

    def save_db(self):
        """Veritabanını kaydeder."""
        with open(PICCOLO_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.seen_products, f, ensure_ascii=False, indent=4)

    def scrape_piccolo_products(self, driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
        """
        Piccolo Hot Wheels Premium sayfasından ürünleri çeker (DiecastTurkey gibi).

        Returns:
            (ürün listesi, hata mesajı)
        """
        products = []

        try:
            print(f"  🌐 Sayfa yükleniyor: {HOT_WHEELS_URL}")
            driver.get(HOT_WHEELS_URL)

            # Sayfanın tam yüklenmesini bekle - Google Cloud için daha uzun timeout
            print("  ⏳ Sayfa yüklenmesi bekleniyor...")
            try:
                # Document ready state kontrolü
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print("  ✅ Document ready state: complete")
            except TimeoutException:
                print("  ⚠️  Document ready state timeout, devam ediliyor...")
            
            # Cloudflare challenge kontrolü
            current_url = driver.current_url
            if "cloudflare.com" in current_url or "challenge" in current_url.lower():
                print("  ⚠️  Cloudflare challenge tespit edildi, bekleniyor...")
                # Cloudflare challenge'ı geçmek için bekle
                max_wait = 30  # Maksimum 30 saniye bekle
                wait_time = 0
                while wait_time < max_wait:
                    time.sleep(2)
                    wait_time += 2
                    current_url = driver.current_url
                    if "piccolo.com.tr" in current_url and "cloudflare.com" not in current_url:
                        print(f"  ✅ Cloudflare challenge geçildi ({wait_time}s sonra)")
                        break
                    print(f"  ⏳ Cloudflare challenge bekleniyor... ({wait_time}s/{max_wait}s)")
                
                if "cloudflare.com" in driver.current_url:
                    print("  ❌ Cloudflare challenge geçilemedi, sayfa yeniden yükleniyor...")
                    time.sleep(5)
                    driver.get(HOT_WHEELS_URL)
                    time.sleep(10)  # Cloudflare için ek bekleme
            
            # Ek bekleme - JavaScript'in çalışması için (Cloud için daha uzun)
            time.sleep(5)
            
            # Sayfada içerik yüklenene kadar bekle - Cloudflare sonrası kontrol
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # URL kontrolü - hala Cloudflare'de miyiz?
                    current_url = driver.current_url
                    if "cloudflare.com" in current_url:
                        print(f"  ⚠️  Hala Cloudflare sayfasında (deneme {retry_count + 1}/{max_retries})")
                        time.sleep(5)
                        driver.get(HOT_WHEELS_URL)
                        time.sleep(10)
                        retry_count += 1
                        continue
                    
                    # Link sayısı kontrolü
                    link_count = len(driver.find_elements(By.TAG_NAME, "a"))
                    if link_count > 10:
                        print(f"  ✅ Sayfada {link_count} link bulundu")
                        break
                    else:
                        print(f"  ⚠️  Sayfada sadece {link_count} link var (deneme {retry_count + 1}/{max_retries})")
                        if retry_count < max_retries - 1:
                            time.sleep(5)
                            # Sayfayı yeniden yükle
                            driver.get(HOT_WHEELS_URL)
                            time.sleep(10)
                        retry_count += 1
                except Exception as e:
                    print(f"  ⚠️  Kontrol hatası: {str(e)[:50]}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(5)
                        driver.get(HOT_WHEELS_URL)
                        time.sleep(10)
            
            # Final kontrol
            final_link_count = len(driver.find_elements(By.TAG_NAME, "a"))
            final_url = driver.current_url
            if "cloudflare.com" in final_url:
                return [], "Cloudflare challenge geçilemedi"
            if final_link_count < 10:
                print(f"  ⚠️  Final kontrol: Sadece {final_link_count} link bulundu, devam ediliyor...")

            # Document ready state tekrar kontrol et (Cloudflare sonrası)
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                print("  ✅ Document ready state (Cloudflare sonrası): complete")
            except TimeoutException:
                print("  ⚠️  Document ready state timeout (Cloudflare sonrası), devam ediliyor...")
            
            # Ek bekleme - sayfa içeriğinin yüklenmesi için
            time.sleep(3)
            
            # Cookie banner'ı kapat (varsa)
            try:
                cookie_accept = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kabul') or contains(text(), 'Accept') or contains(@class, 'cookie')]"))
                )
                cookie_accept.click()
                time.sleep(1)
                print("  ✅ Cookie banner kapatıldı")
            except (TimeoutException, NoSuchElementException):
                pass

            # Lazy loading için scroll yap - Google Cloud için daha agresif
            print("  📜 Sayfa scroll ediliyor (lazy loading için)...")
            
            # Önce sayfanın başına scroll yap
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(2)
            
            # Kademeli scroll yap - her seferinde biraz daha aşağı
            scroll_position = 0
            scroll_step = 500
            max_scrolls = 20
            
            for i in range(max_scrolls):
                scroll_position += scroll_step
                driver.execute_script(f"window.scrollTo(0, {scroll_position})")
                time.sleep(2)  # Her scroll sonrası bekle
                
                # Sayfa yüksekliğini kontrol et
                page_height = driver.execute_script("return document.body.scrollHeight")
                if scroll_position >= page_height:
                    break
            
            # Sonra sayfanın sonuna scroll yap
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 20  # Google Cloud için daha fazla deneme
            
            while scroll_attempts < max_scroll_attempts:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(4)  # Google Cloud için daha uzun bekleme
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # Daha fazla içerik yüklenmedi, biraz daha bekle
                    time.sleep(4)  # Google Cloud için daha uzun bekleme
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        print(f"  ✅ Scroll tamamlandı (deneme: {scroll_attempts + 1})")
                        break  # Artık yeni içerik yok
                
                last_height = new_height
                scroll_attempts += 1
                print(f"  📜 Scroll {scroll_attempts}/{max_scroll_attempts} - Yükseklik: {new_height}")
            
            # Son bir kez daha scroll ve bekle
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)  # Google Cloud için daha uzun bekleme
            
            # Sayfanın tam yüklenmesini tekrar kontrol et
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                pass
            
            # Link sayısını kontrol et
            link_count = len(driver.find_elements(By.TAG_NAME, "a"))
            print(f"  ✅ Final sayfa yüksekliği: {driver.execute_script('return document.body.scrollHeight')}")
            print(f"  ✅ Final link sayısı: {link_count}")
            
            # Eğer hala çok az link varsa, ek bekleme
            if link_count < 10:
                print(f"  ⚠️  Az link bulundu ({link_count}), ek bekleme yapılıyor...")
                time.sleep(10)
                link_count = len(driver.find_elements(By.TAG_NAME, "a"))
                print(f"  ✅ Yeni link sayısı: {link_count}")

            # JavaScript ile sayfadaki ürün ID'lerini çıkar ve API'ye çağrı yap (Ana yöntem)
            try:
                print("  🔍 JavaScript ile ürün ID'leri çıkarılıyor...")
                
                # JavaScript ile sayfadaki ürün ID'lerini çıkar
                product_ids_script = """
                let productIds = [];
                const seenIds = new Set();
                
                // Tüm linkleri kontrol et
                const allLinks = document.querySelectorAll('a[href]');
                allLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href) return;
                    
                    let fullUrl = href;
                    if (href.startsWith('/')) {
                        fullUrl = 'https://www.piccolo.com.tr' + href;
                    } else if (!href.startsWith('http')) {
                        fullUrl = 'https://www.piccolo.com.tr/' + href;
                    }
                    
                    // hot-wheels-premium içeren linkleri bul
                    if (fullUrl.includes('hot-wheels-premium')) {
                        const idMatch = fullUrl.match(/hot-wheels-premium[\\/\\\\](\\d+)/);
                        if (idMatch && idMatch[1] && !seenIds.has(idMatch[1])) {
                            seenIds.add(idMatch[1]);
                            productIds.push(idMatch[1]);
                        }
                    }
                });
                
                // Alternatif: data-product-id attribute'larını kontrol et
                if (productIds.length === 0) {
                    const elements = document.querySelectorAll('[data-product-id], [data-id], [data-product]');
                    elements.forEach(el => {
                        const id = el.getAttribute('data-product-id') || el.getAttribute('data-id') || el.getAttribute('data-product');
                        if (id && !seenIds.has(id)) {
                            seenIds.add(id);
                            productIds.push(id);
                        }
                    });
                }
                
                return productIds;
                """
                
                product_ids = driver.execute_script(product_ids_script)
                
                if not product_ids or len(product_ids) == 0:
                    # Debug: Sayfadaki link sayısını ve örnek linkleri kontrol et
                    try:
                        link_count = driver.execute_script("return document.querySelectorAll('a[href]').length;")
                        print(f"  🔍 Debug: Sayfada {link_count} link bulundu")
                        
                        # İlk birkaç linki göster
                        sample_links = driver.execute_script("""
                            const links = Array.from(document.querySelectorAll('a[href]')).slice(0, 10);
                            return links.map(l => l.getAttribute('href'));
                        """)
                        print(f"  🔍 Debug: Örnek linkler: {sample_links[:5]}")
                        
                        # hot-wheels-premium içeren linkleri say
                        hw_links = driver.execute_script("""
                            const links = Array.from(document.querySelectorAll('a[href]'));
                            return links.filter(l => {
                                const href = l.getAttribute('href') || '';
                                return href.includes('hot-wheels-premium');
                            }).length;
                        """)
                        print(f"  🔍 Debug: hot-wheels-premium içeren linkler: {hw_links}")
                        
                        # Eğer çok az link varsa, tekrar bekle ve scroll yap
                        if link_count < 50:
                            print(f"  ⚠️  Az link bulundu, tekrar scroll yapılıyor...")
                            for i in range(5):
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                                time.sleep(3)
                            time.sleep(5)
                            
                            # Tekrar dene
                            product_ids = driver.execute_script(product_ids_script)
                            if product_ids and len(product_ids) > 0:
                                print(f"  ✅ İkinci denemede {len(product_ids)} ürün ID'si bulundu")
                            else:
                                return [], f"Sayfada ürün ID'si bulunamadı (Toplam {link_count} link, {hw_links} hot-wheels linki)"
                        else:
                            return [], f"Sayfada ürün ID'si bulunamadı (Toplam {link_count} link)"
                    except Exception as debug_error:
                        print(f"  ⚠️  Debug hatası: {str(debug_error)[:50]}")
                        return [], "Sayfada ürün ID'si bulunamadı"
                
                print(f"  ✅ {len(product_ids)} ürün ID'si bulundu, API çağrısı yapılıyor...")
                
                # API'ye çağrı yap
                product_ids_str = ','.join(product_ids)
                api_url = f"{API_URL}?c={API_BASE_PARAMS['c']}&productIds={product_ids_str}"
                
                try:
                    response = requests.get(api_url, timeout=15)
                    response.raise_for_status()
                    api_data = response.json()
                    
                    if api_data and "productCategoryTreeList" in api_data:
                        tree_list = api_data["productCategoryTreeList"]
                        
                        for item in tree_list:
                            if isinstance(item, dict) and "productId" in item:
                                product_id = str(item["productId"])
                                
                                # Debug: İlk ürünün tüm alanlarını göster
                                if len(products) == 0:
                                    print(f"  🔍 Debug: API yanıtı örneği - Anahtarlar: {list(item.keys())[:10]}")
                                
                                # Ürün adı - API'deki gerçek alan adını kullan
                                product_name = item.get("productName", "")
                                if not product_name:
                                    product_name = item.get("name", "")
                                if not product_name:
                                    product_name = item.get("title", "")
                                if not product_name:
                                    product_name = "İsimsiz Ürün"
                                
                                # Ürün kodu
                                product_code = item.get("productCode", "")
                                if not product_code:
                                    product_code = item.get("code", "")
                                if not product_code:
                                    product_code = item.get("sku", "")
                                
                                # Stok kontrolü - API'deki gerçek alan adını kullan
                                is_in_stock = True
                                if "inStock" in item:
                                    is_in_stock = bool(item.get("inStock", False))
                                elif "stockQuantity" in item:
                                    stock_qty = item.get("stockQuantity", 0)
                                    is_in_stock = int(stock_qty) > 0 if stock_qty else False
                                elif "quantity" in item:
                                    stock_qty = item.get("quantity", 0)
                                    is_in_stock = int(stock_qty) > 0 if stock_qty else False
                                
                                stock_quantity = 0
                                if "stockQuantity" in item:
                                    stock_quantity = int(item.get("stockQuantity", 0))
                                elif "quantity" in item:
                                    stock_quantity = int(item.get("quantity", 0))
                                
                                # Fiyat bilgisi - API'deki gerçek alan adını kullan
                                price = "Fiyat yok"
                                if "price" in item:
                                    price_value = item.get("price")
                                    if price_value:
                                        if isinstance(price_value, (int, float)):
                                            price = f"{price_value} TL"
                                        elif isinstance(price_value, str):
                                            price = price_value if ("TL" in price_value or "₺" in price_value) else f"{price_value} TL"
                                elif "salePrice" in item:
                                    price_value = item.get("salePrice")
                                    if price_value:
                                        price = f"{price_value} TL" if isinstance(price_value, (int, float)) else str(price_value)
                                elif "totalSalePrice" in item:
                                    price_value = item.get("totalSalePrice")
                                    if price_value:
                                        price = f"{price_value} TL" if isinstance(price_value, (int, float)) else str(price_value)
                                
                                product = {
                                    "id": product_id,
                                    "name": product_name,
                                    "code": product_code,
                                    "supplier_code": item.get("supplierCode", ""),
                                    "price": price,
                                    "url": f"https://www.piccolo.com.tr/hot-wheels-premium/{product_id}/",
                                    "image": item.get("image", "") or item.get("imageUrl", ""),
                                    "brand": item.get("brand", "") or item.get("brandName", ""),
                                    "category": item.get("category", "") or item.get("categoryName", ""),
                                    "quantity": stock_quantity,
                                    "in_stock": is_in_stock
                                }
                                
                                products.append(product)
                        
                        if len(products) > 0:
                            print(f"  ✅ API ile {len(products)} ürün alındı")
                            return products, None
                        else:
                            return [], "API'den ürün bilgisi alınamadı"
                    else:
                        return [], "API yanıtında productCategoryTreeList bulunamadı"
                        
                except requests.exceptions.Timeout:
                    return [], "API çağrısı zaman aşımına uğradı"
                except requests.exceptions.ConnectionError:
                    return [], "API'ye bağlanılamadı"
                except requests.exceptions.HTTPError as e:
                    return [], f"API HTTP hatası: {e.response.status_code}"
                except json.JSONDecodeError as e:
                    return [], f"API JSON parse hatası: {str(e)}"
                except Exception as api_error:
                    return [], f"API çağrısı hatası: {str(api_error)}"
                
            except JavascriptException as e:
                return [], f"JavaScript hatası: {str(e)[:100]}"

        except Exception as e:
            return [], f"Scraping hatası: {str(e)[:100]}"


def scrape_piccolo_sync(monitor: PiccoloMonitor, driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
    """
    Senkron wrapper fonksiyon - Selenium driver ile çalıştırır (DiecastTurkey gibi).

    Args:
        monitor: PiccoloMonitor instance
        driver: Selenium WebDriver instance

    Returns:
        (ürün listesi, hata mesajı) tuple'ı
    """
    return monitor.scrape_piccolo_products(driver)


# Global monitor instance
_piccolo_monitor = None

def get_piccolo_monitor():
    """Global Piccolo monitor instance'ını döndürür."""
    global _piccolo_monitor
    if _piccolo_monitor is None:
        _piccolo_monitor = PiccoloMonitor()
    return _piccolo_monitor

