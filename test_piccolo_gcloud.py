#!/usr/bin/env python3
"""
Google Cloud'da Piccolo test
Lokalde çalışan kodun cloud'da neden çalışmadığını debug eder
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_with_headless(headless_mode):
    """Test et - headless mode ile veya olmadan"""
    
    mode_name = "HEADLESS" if headless_mode else "GUI (No Headless)"
    logger.info(f"\n{'='*70}")
    logger.info(f"TEST: {mode_name}")
    logger.info(f"{'='*70}\n")
    
    chrome_options = Options()
    
    if headless_mode:
        chrome_options.add_argument("--headless=new")
        logger.info("  🔧 Headless mode açık")
    else:
        logger.info("  🔧 GUI mode açık (Cloudflare bypass için)")
    
    # Google Cloud optimizations
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # CDP
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    try:
        url = "https://www.piccolo.com.tr/hot-wheels-premium"
        logger.info(f"  🌐 Sayfaya gidiyor: {url}")
        driver.get(url)
        
        logger.info(f"  ⏳ Cloudflare challenge çözülüyor (10s)...")
        time.sleep(10)
        
        # Scroll
        logger.info(f"  📜 Agresif scroll yapılıyor...")
        for i in range(10):
            driver.execute_script("window.scrollBy(0, window.innerHeight * 2)")
            time.sleep(1)
        
        # Test JavaScript
        logger.info(f"  🔍 JavaScript çalıştırılıyor...")
        js_code = """
        let ids = [];
        const seen = new Set();
        
        // Method 1
        document.querySelectorAll('[data-id]').forEach(el => {
            const id = el.getAttribute('data-id');
            if (id && !seen.has(id) && /^\\d+$/.test(id)) {
                seen.add(id);
                ids.push(id);
            }
        });
        
        return {
            ids: ids,
            data_id_count: document.querySelectorAll('[data-id]').length,
            total_elements: document.querySelectorAll('*').length,
            page_title: document.title,
            html_size: document.documentElement.outerHTML.length
        };
        """
        
        result = driver.execute_script(js_code)
        
        logger.info(f"\n✅ SONUÇLAR:")
        logger.info(f"   IDs bulundu: {len(result['ids'])}")
        logger.info(f"   data-id elements: {result['data_id_count']}")
        logger.info(f"   Total elements: {result['total_elements']}")
        logger.info(f"   Page title: {result['page_title']}")
        logger.info(f"   HTML size: {result['html_size']} bytes")
        logger.info(f"   IDs: {result['ids'][:5]}{'...' if len(result['ids']) > 5 else ''}")
        
        # HTML kaydet
        filename = f"piccolo_test_{mode_name.replace(' ', '_').lower()}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info(f"   💾 {filename} kaydedildi")
        
        return len(result['ids']) > 0
        
    except Exception as e:
        logger.error(f"  ❌ Hata: {e}")
        return False
    
    finally:
        driver.quit()
        logger.info(f"\n")

if __name__ == "__main__":
    logger.info("\n🧪 PICCOLO CLOUDFLARE TEST")
    logger.info("   Lokal vs Google Cloud mode karşılaştırması")
    
    # Test 1: Headless
    result_headless = test_with_headless(True)
    
    # Test 2: GUI
    result_gui = test_with_headless(False)
    
    # Sonuç
    logger.info("\n" + "="*70)
    logger.info("ÖZET")
    logger.info("="*70)
    logger.info(f"  Headless Mode: {'✅ BAŞARILI' if result_headless else '❌ BAŞARILI DEĞİL'}")
    logger.info(f"  GUI Mode:      {'✅ BAŞARILI' if result_gui else '❌ BAŞARILI DEĞİL'}")
    
    if result_gui and not result_headless:
        logger.info("\n💡 Sonuç: GUI Mode'u kullanmalısın!")
        logger.info("   setup_piccolo_driver(headless=False) ile çalıştır")
    elif result_headless and not result_gui:
        logger.info("\n💡 Sonuç: Headless Mode çalışıyor")
    elif not result_headless and not result_gui:
        logger.info("\n❌ Her iki mode'da da başarısız - debug HTML'lerini kontrol et")
    else:
        logger.info("\n✅ Her iki mode'da da çalışıyor!")
    
    logger.info("="*70)

