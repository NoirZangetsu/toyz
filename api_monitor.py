#!/usr/bin/env python3
"""
Piccolo Ürün Kategori Hiyerarşisi Monitor
GetProductCategoryHierarchy endpoint'ini kontrol edip ürün sayısı ve ürün listesini gösterir.
"""

import os
import json
import time
import ssl
import smtplib
import re
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, Any, Optional, List, Tuple, Set

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException
from webdriver_manager.chrome import ChromeDriverManager

# API endpoint ve parametreleri
API_URL = "https://www.piccolo.com.tr/api/Product/GetProductCategoryHierarchy"
API_PARAMS = {
    "c": "trtry0000",
    "productIds": "682,1053,1093,1094,1114,1115,1116,1125,1136,1165,1167,1168,1169,1172,1173,1174"
}

# İzlenecek kategori sayfası
HOT_WHEELS_URL = "https://www.piccolo.com.tr/hot-wheels-premium"

# Piccolo scraping için database dosyası
PICCOLO_DB_FILE = "piccolo_stock_db.json"

# Telegram ve E-posta yapılandırması (config.py dosyasından veya ortam değişkenlerinden okunur)
try:
    from config import (
        TELEGRAM_BOT_TOKEN as CONFIG_TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID as CONFIG_TELEGRAM_CHAT_ID,
        SMTP_SERVER as CONFIG_SMTP_SERVER,
        SMTP_PORT as CONFIG_SMTP_PORT,
        SMTP_USERNAME as CONFIG_SMTP_USERNAME,
        SMTP_PASSWORD as CONFIG_SMTP_PASSWORD,
        EMAIL_FROM as CONFIG_EMAIL_FROM,
        EMAIL_TO as CONFIG_EMAIL_TO,
        SMTP_USE_TLS as CONFIG_SMTP_USE_TLS,
    )
    # Telegram config
    TELEGRAM_BOT_TOKEN = CONFIG_TELEGRAM_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = CONFIG_TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "")
    # E-posta config
    SMTP_SERVER = CONFIG_SMTP_SERVER or os.getenv("SMTP_SERVER")
    SMTP_PORT = CONFIG_SMTP_PORT if CONFIG_SMTP_PORT else int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = CONFIG_SMTP_USERNAME or os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = CONFIG_SMTP_PASSWORD or os.getenv("SMTP_PASSWORD")
    EMAIL_FROM = CONFIG_EMAIL_FROM or os.getenv("EMAIL_FROM", CONFIG_SMTP_USERNAME or "")
    EMAIL_TO = CONFIG_EMAIL_TO or os.getenv("EMAIL_TO", "")
    SMTP_USE_TLS = CONFIG_SMTP_USE_TLS if isinstance(CONFIG_SMTP_USE_TLS, bool) else (os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true")
except ImportError:
    # Config dosyası yoksa ortam değişkenlerinden oku
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME or "")
    EMAIL_TO = os.getenv("EMAIL_TO", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"

# Bildirim durumları
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
EMAIL_RECIPIENTS = [addr.strip() for addr in EMAIL_TO.split(",") if addr.strip()]
EMAIL_ENABLED = all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_RECIPIENTS])


def setup_piccolo_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Piccolo için Chrome WebDriver'ı yapılandırır.
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

    # WebDriver Manager ile ChromeDriver'ı otomatik olarak yönet
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
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
        Piccolo Hot Wheels Premium sayfasından ürünleri çeker.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            (ürün listesi, hata mesajı) tuple'ı
        """
        products = []

        try:
            print(f"  🌐 Piccolo sayfası yükleniyor: {HOT_WHEELS_URL}")
            driver.get(HOT_WHEELS_URL)

            # Sayfanın yüklenmesini bekle
            time.sleep(5)

            # Cookie banner'ı kapat (varsa)
            try:
                cookie_accept = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kabul') or contains(text(), 'Accept') or contains(@class, 'cookie')]"))
                )
                cookie_accept.click()
                time.sleep(1)
            except (TimeoutException, NoSuchElementException):
                pass

            # Sayfa yüklenmesini tetikle - scroll yap
            for i in range(3):
                driver.execute_script(f"window.scrollTo(0, {i * 1000})")
                time.sleep(1)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)

            # Ürün kartlarını bul - farklı seçiciler dene
            selectors_to_try = [
                ".product-item",
                ".product-card",
                ".product-box",
                ".item",
                "[data-product-id]",
                ".product",
                ".product-container",
                ".card",
                ".grid-item"
            ]

            product_elements = []

            for selector in selectors_to_try:
                try:
                    product_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(product_elements) > 0:
                        print(f"  ✅ Piccolo seçici bulundu: {selector} ({len(product_elements)} ürün)")
                        break
                except Exception:
                    continue

            if len(product_elements) == 0:
                # Alternatif yöntem - ürün linklerini ara
                try:
                    product_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/hot-wheels-premium"]')
                    print(f"  ℹ️  Ürün linkleri bulundu: {len(product_elements)}")
                except Exception:
                    return [], "Hiçbir ürün elementi bulunamadı"

            # İlk 50 ürünü işle
            for i, item in enumerate(product_elements[:50]):
                try:
                    # Ürün linkini al
                    href = item.get_attribute("href")
                    if not href:
                        # Eğer item link değilse, içindeki linki ara
                        try:
                            link_element = item.find_element(By.TAG_NAME, "a")
                            href = link_element.get_attribute("href")
                        except NoSuchElementException:
                            continue

                    if not href:
                        continue

                    # Tam URL oluştur
                    if href.startswith('/'):
                        product_url = f"https://www.piccolo.com.tr{href}"
                    elif href.startswith('http'):
                        product_url = href
                    else:
                        continue

                    # Ürün ID'sini URL'den çıkar
                    product_id_match = re.search(r'/(\d+)/', product_url)
                    if product_id_match:
                        product_id = product_id_match.group(1)
                    else:
                        product_id = f"piccolo_{i}"

                    # Ürün bilgilerini çıkar
                    container_text = item.text
                    lines = [line.strip() for line in container_text.split('\n') if line.strip()]

                    # Ürün adını çıkar
                    name = "İsimsiz Ürün"
                    for line in lines:
                        if len(line) > 10 and not any(char.isdigit() for char in line[:20]):
                            name = line
                            break

                    # Fiyatı çıkar
                    price = "0 TL"
                    for line in lines:
                        if ("TL" in line or "₺" in line) and any(c.isdigit() for c in line):
                            price = line
                            break

                    # Stok durumunu kontrol et - çeşitli yöntemler
                    is_in_stock = False
                    stock_quantity = 0

                    # Yöntem 1: "Sepete Ekle" butonu ara
                    try:
                        add_to_cart_buttons = item.find_elements(By.CSS_SELECTOR, 'button, input[type="submit"], a')
                        for button in add_to_cart_buttons:
                            button_text = button.text.lower()
                            if "sepete ekle" in button_text or "satın al" in button_text or "add to cart" in button_text:
                                is_in_stock = True
                                stock_quantity = 1  # Piccolo'da adet bilgisi göstermiyor
                                break
                    except NoSuchElementException:
                        pass

                    # Yöntem 2: Stok bilgisi ara
                    container_lower = container_text.lower()
                    if "stok" in container_lower or "tükendi" in container_lower:
                        if "tükendi" in container_lower or "stokta yok" in container_lower or "out of stock" in container_lower:
                            is_in_stock = False
                        else:
                            is_in_stock = True
                    # Yöntem 3: Varsayılan olarak stokta kabul et (tükendi belirtilmemişse)
                    elif not any(keyword in container_lower for keyword in ["tükendi", "stokta yok", "haber ver", "out of stock", "notify me"]):
                        is_in_stock = True

                    # Kod bilgisi çıkar (varsa)
                    code = ""
                    for line in lines:
                        if len(line) <= 15 and any(c.isdigit() for c in line) and any(c.isalpha() for c in line):
                            code = line
                            break

                    product = {
                        "id": product_id,
                        "name": name.strip(),
                        "code": code.strip(),
                        "price": price.strip(),
                        "url": product_url,
                        "in_stock": is_in_stock,
                        "quantity": stock_quantity
                    }

                    products.append(product)

                except Exception as e:
                    print(f"  ⚠️  Ürün parse edilemedi: {str(e)[:50]}")
                    continue

            print(f"  ✅ {len(products)} ürün işlendi")

        except Exception as e:
            return [], f"Piccolo scraping hatası: {str(e)}"

        return products, None


def scrape_piccolo_sync(monitor: PiccoloMonitor, driver: webdriver.Chrome) -> Tuple[List[Dict], Optional[str]]:
    """
    Senkron wrapper fonksiyon - Selenium driver ile çalıştırır.

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

# Kontrol aralığı (saniye cinsinden)
CHECK_INTERVAL = 30  # Varsayılan 30 saniye


def make_api_request() -> Tuple[Optional[Dict[Any, Any]], Optional[str]]:
    """
    API'ye istek atar ve sonucu döndürür.
    
    Returns:
        (API yanıtı (dict), hata mesajı) tuple'ı
    """
    try:
        response = requests.get(API_URL, params=API_PARAMS, timeout=10)
        response.raise_for_status()  # HTTP hatalarını kontrol et
        
        # JSON yanıt kontrolü
        try:
            return response.json(), None
        except json.JSONDecodeError as e:
            return None, f"❌ JSON parse hatası: {str(e)}"
            
    except requests.exceptions.Timeout:
        return None, f"⏱️  Timeout hatası"
    except requests.exceptions.ConnectionError:
        return None, f"🔌 Bağlantı hatası"
    except requests.exceptions.HTTPError as e:
        return None, f"❌ HTTP {e.response.status_code} hatası"
    except requests.exceptions.RequestException as e:
        return None, f"❌ İstek hatası: {str(e)[:100]}"
    except Exception as e:
        return None, f"❌ Beklenmeyen hata: {str(e)[:100]}"


def send_email(subject: str, body: str) -> Tuple[bool, Optional[str]]:
    """
    Yeni ürünler bulunduğunda e-posta gönderir.
    
    Returns:
        (başarı durumu, hata mesajı)
    """
    if not EMAIL_ENABLED:
        return False, "SMTP yapılandırması eksik."
    
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = ", ".join(EMAIL_RECIPIENTS)
    message.set_content(body)
    
    try:
        if SMTP_USE_TLS and SMTP_PORT == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                if SMTP_USE_TLS:
                    server.starttls(context=ssl.create_default_context())
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
        return True, None
    except Exception as e:
        return False, str(e)


def build_notification_message(new_product_ids: List[int], product_count: int, product_ids: List[int]) -> str:
    """
    Bildirim mesajını hazırlar (Telegram ve E-posta için).
    """
    lines = [
        "🚨 YENİ ÜRÜN BULUNDU!",
        "",
        "Piccolo Hot Wheels Premium kategorisine yeni ürünler eklendi.",
        "",
        f"📦 Toplam ürün sayısı: {product_count}",
        f"✨ Yeni eklenen ürün ID'leri: {', '.join(map(str, new_product_ids))}",
        "",
        f"🔗 Detaylar için siteye git: {HOT_WHEELS_URL}",
    ]
    return "\n".join(lines)


def build_email_body(new_product_ids: List[int], product_count: int, product_ids: List[int]) -> str:
    """
    E-posta içeriğini hazırlar.
    """
    lines = [
        "Merhaba,",
        "",
        "Piccolo Hot Wheels Premium kategorisine yeni ürünler eklendi.",
        "",
        f"Toplam ürün sayısı: {product_count}",
        f"Yeni eklenen ürün ID'leri: {', '.join(map(str, new_product_ids))}",
        "",
        "Güncel ürün listesi:",
        f"{', '.join(map(str, product_ids))}",
        "",
        f"Detaylar için siteye git: {HOT_WHEELS_URL}",
        "",
        "Bu e-posta Piccolo Ürün Kategori Hiyerarşisi Monitor tarafından otomatik gönderildi.",
    ]
    return "\n".join(lines)


def send_telegram_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Telegram bot üzerinden mesaj gönderir.
    
    Returns:
        (başarı durumu, hata mesajı)
    """
    if not TELEGRAM_ENABLED:
        return False, "Telegram yapılandırması eksik."
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.exceptions.RequestException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def send_initial_summary(product_count: int, product_ids: List[int]) -> None:
    """
    İzleme başladığında mevcut ürünlerin özetini Telegram üzerinden gönderir.
    """
    if not TELEGRAM_ENABLED:
        print("ℹ️  Telegram bildirimi yapılandırılmamış. İlk özet gönderilmedi.")
        return

    lines = [
        "📊 Piccolo Hot Wheels Premium izleme başladı.",
        "",
        f"📦 Mevcut ürün sayısı: {product_count}",
        f"🆔 Ürün ID'leri: {', '.join(map(str, product_ids))}" if product_ids else "⚠️ Mevcut ürün bulunamadı.",
        "",
        f"🔗 Kategori bağlantısı: {HOT_WHEELS_URL}",
    ]
    message = "\n".join(lines)

    success, error = send_telegram_message(message)
    if success:
        print("📱 Başlangıç özeti Telegram ile gönderildi.")
    else:
        print(f"❌ Başlangıç özeti gönderilemedi: {error}")


def notify_new_products(new_product_ids: List[int], product_count: int, product_ids: List[int]) -> None:
    """
    Yeni ürünler bulunduğunda loglar ve bildirim gönderir (Telegram ve/veya E-posta).
    """
    print(f"🚨 Yeni ürün bulundu! Yeni ürün ID'leri: {', '.join(map(str, new_product_ids))}")
    
    message = build_notification_message(new_product_ids, product_count, product_ids)
    notification_sent = False
    
    # Telegram bildirimi
    if TELEGRAM_ENABLED:
        success, error = send_telegram_message(message)
        if success:
            print("📱 Yeni ürün bildirimi Telegram ile gönderildi.")
            notification_sent = True
        else:
            print(f"❌ Telegram mesajı gönderilemedi: {error}")
    else:
        print("ℹ️  Telegram bildirimi yapılandırılmamış. config.py dosyasına TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ekleyin.")
    
    # E-posta bildirimi
    if EMAIL_ENABLED:
        subject = f"[Piccolo] {len(new_product_ids)} yeni ürün bulundu"
        body = build_email_body(new_product_ids, product_count, product_ids)
        success, error = send_email(subject, body)
        if success:
            print("✉️  Yeni ürün bildirimi e-posta ile gönderildi.")
            notification_sent = True
        else:
            print(f"❌ E-posta gönderilemedi: {error}")
    else:
        print("ℹ️  E-posta bildirimi yapılandırılmamış.")
    
    if not notification_sent:
        print("⚠️  Hiçbir bildirim yöntemi yapılandırılmamış. Lütfen config.py dosyasını düzenleyin.")


def compare_responses(old: Optional[Dict], new: Dict) -> bool:
    """
    İki yanıtı karşılaştırır ve değişiklik olup olmadığını döndürür.
    
    Args:
        old: Önceki yanıt
        new: Yeni yanıt
        
    Returns:
        True eğer değişiklik varsa
    """
    if old is None:
        return True
    return old != new


def monitor_api(interval: int = CHECK_INTERVAL, continuous: bool = True):
    """
    GetProductCategoryHierarchy API'sini periyodik olarak kontrol eder.
    
    Args:
        interval: Kontrol aralığı (saniye)
        continuous: Sürekli kontrol modu (True) veya tek seferlik (False)
    """
    print("=" * 70)
    print("🔍 Piccolo Ürün Kategori Hiyerarşisi Monitor")
    print("=" * 70)
    print(f"📡 API URL: {API_URL}")
    print(f"📋 Parametreler: {API_PARAMS}")
    print(f"⏱️  Kontrol aralığı: {interval} saniye")
    print("=" * 70)
    print()
    
    previous_response = None
    previous_product_ids: Set[int] = set()
    check_count = 0
    
    try:
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n{'='*70}")
            print(f"[{timestamp}] Kontrol #{check_count}")
            print(f"{'='*70}\n")
            
            # API isteği
            response, error = make_api_request()
            
            if error:
                print(f"❌ {error}\n")
                if not continuous:
                    break
                if continuous:
                    print(f"⏳ {interval} saniye sonra tekrar kontrol edilecek...\n")
                    time.sleep(interval)
                continue
            
            if response:
                # Değişiklik kontrolü
                has_changed = compare_responses(previous_response, response)
                product_count, product_ids = extract_products(response)
                current_product_set = set(product_ids)
                
                if has_changed:
                    if previous_response is None:
                        print("✅ İlk yanıt alındı")
                    else:
                        print("🔄 Değişiklik tespit edildi!")
                    
                    # Ürün analizi
                    analyze_products(response, product_count, product_ids)
                    
                    if previous_response is None:
                        send_initial_summary(product_count, product_ids)
                    
                    if previous_product_ids:
                        new_product_ids = sorted(current_product_set - previous_product_ids)
                        if new_product_ids:
                            notify_new_products(new_product_ids, product_count, product_ids)
                        else:
                            print("ℹ️  Yeni ürün bulunmadı (muhtemelen ürün silindi veya güncellendi).")
                    else:
                        print("ℹ️  Başlangıç karşılaştırması için ürün listesi kaydedildi.")
                    
                    previous_response = response.copy() if isinstance(response, dict) else response
                    previous_product_ids = current_product_set
                else:
                    print("ℹ️  Değişiklik yok (aynı yanıt)")
                    if product_count > 0:
                        print(f"📊 Özet: {product_count} ürün bulundu")
                    else:
                        print("⚠️  Ürün bulunamadı")
            else:
                print("⚠️  Yanıt alınamadı")
            
            if not continuous:
                break
            
            # Bekleme
            if continuous:
                print(f"\n⏳ {interval} saniye sonra tekrar kontrol edilecek...\n")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n🛑 İzleme durduruldu.")


def extract_products(data: Dict[Any, Any]) -> Tuple[int, List[int]]:
    """
    API yanıtından ürün ID'lerini çıkarır.
    
    Args:
        data: API yanıtı
        
    Returns:
        (ürün sayısı, ürün ID listesi) tuple'ı
    """
    product_ids = []
    
    if isinstance(data, dict) and "productCategoryTreeList" in data:
        tree_list = data["productCategoryTreeList"]
        if isinstance(tree_list, list):
            for item in tree_list:
                if isinstance(item, dict) and "productId" in item:
                    product_ids.append(item["productId"])
    
    return len(product_ids), product_ids


def analyze_products(data: Dict[Any, Any], product_count: int, product_ids: List[int]) -> None:
    """
    API yanıtından ürün bilgilerini analiz eder ve gösterir.
    
    Args:
        data: API yanıtı
        product_count: Toplam ürün sayısı
        product_ids: Ürün ID listesi
    """
    print("\n📊 Ürün Analizi:")
    print("-" * 70)
    
    # Hata kontrolü
    if isinstance(data, dict):
        if "isError" in data and data["isError"]:
            print(f"❌ Hata durumu: Var")
            if data.get("errorMessage"):
                print(f"   Hata mesajı: {data['errorMessage']}")
            return
        
        print(f"✅ Toplam Ürün Sayısı: {product_count}")
        
        if product_count > 0:
            print(f"\n📦 Var Olan Ürünler:")
            print(f"   Ürün ID'leri: {', '.join(map(str, product_ids))}")
            
            # Kategori bilgileri
            if "productCategoryTreeList" in data:
                tree_list = data["productCategoryTreeList"]
                if isinstance(tree_list, list) and tree_list:
                    print(f"\n🏷️  Kategori Bilgileri:")
                    first_item = tree_list[0]
                    if "categoryHierarchy" in first_item:
                        categories = first_item["categoryHierarchy"]
                        if isinstance(categories, list):
                            print(f"   Kategori seviyesi: {len(categories)}")
                            print(f"   Kategoriler:")
                            for cat in categories:
                                if isinstance(cat, dict) and "tanim" in cat:
                                    print(f"      • {cat['tanim']} (ID: {cat.get('id', 'N/A')})")
        else:
            print("⚠️  Hiç ürün bulunamadı!")
    else:
        print("⚠️  Geçersiz yanıt formatı")


if __name__ == "__main__":
    import sys
    
    # Komut satırı argümanları
    interval = CHECK_INTERVAL
    continuous = True
    
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Geçersiz aralık değeri: {sys.argv[1]}. Varsayılan {CHECK_INTERVAL} saniye kullanılıyor.")
    
    if len(sys.argv) > 2 and sys.argv[2].lower() == "once":
        continuous = False
    
    monitor_api(interval=interval, continuous=continuous)

