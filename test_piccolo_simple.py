#!/usr/bin/env python3
"""
Google Cloud'da Piccolo Cloudflare test (Headless only)
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_piccolo_headless():
    """Headless mode'da Piccolo'yu test et"""
    
    logger.info("\n" + "="*70)
    logger.info("🧪 PICCOLO CLOUDFLARE TEST - Headless Mode")
    logger.info("="*70 + "\n")
    
    chrome_options = Options()
    
    # Headless (Google Cloud'da zorunlu)
    chrome_options.add_argument("--headless=new")
    logger.info("  🔧 Headless mode açık")
    
    # Google Cloud optimizations
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User-Agent (Cloudflare bypass)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"user-agent={user_agents[0]}")
    
    # Automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
    })
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # CDP - webdriver gizle
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    try:
        url = "https://www.piccolo.com.tr/hot-wheels-premium"
        logger.info(f"  🌐 Sayfaya gidiyor: {url}")
        driver.get(url)
        
        # Cloudflare challenge
        logger.info(f"  ⏳ Cloudflare challenge çözülüyor (15s - enhanced)...")
        time.sleep(15)  # 15 saniye bekleme
        
        # Scroll + JavaScript
        logger.info(f"  📜 Agresif scroll yapılıyor...")
        for i in range(8):
            driver.execute_script("window.scrollBy(0, window.innerHeight * 2)")
            time.sleep(1.5)
        
        # JavaScript - Enhanced version
        logger.info(f"  🔍 JavaScript çalıştırılıyor...")
        
        js_code = """
        let ids = [];
        const seen = new Set();
        
        // Method 1: data-id
        try {
            document.querySelectorAll('[data-id]').forEach(el => {
                const id = el.getAttribute('data-id');
                if (id && !seen.has(id) && /^\\d+$/.test(id)) {
                    seen.add(id);
                    ids.push(id);
                }
            });
        } catch(e) {}
        
        // Method 2: data-product-id
        if (ids.length === 0) {
            try {
                document.querySelectorAll('[data-product-id]').forEach(el => {
                    const id = el.getAttribute('data-product-id');
                    if (id && !seen.has(id) && /^\\d+$/.test(id)) {
                        seen.add(id);
                        ids.push(id);
                    }
                });
            } catch(e) {}
        }
        
        // Method 3: class selector
        if (ids.length === 0) {
            try {
                document.querySelectorAll('[class*="item"], [class*="product"]').forEach(el => {
                    const id = el.getAttribute('data-id') || el.id;
                    if (id && !seen.has(id) && /^\\d+$/.test(id)) {
                        seen.add(id);
                        ids.push(id);
                    }
                });
            } catch(e) {}
        }
        
        return {
            ids: ids,
            page_title: document.title,
            url: window.location.href,
            data_id_elements: document.querySelectorAll('[data-id]').length,
            total_elements: document.querySelectorAll('*').length,
            html_size: document.documentElement.outerHTML.length,
            body_html_size: document.body ? document.body.innerHTML.length : 0
        };
        """
        
        result = driver.execute_script(js_code)
        
        logger.info(f"\n✅ SONUÇLAR:")
        logger.info(f"   IDs bulundu: {len(result['ids'])}")
        logger.info(f"   data-id elements: {result['data_id_elements']}")
        logger.info(f"   Total elements: {result['total_elements']}")
        logger.info(f"   Page title: {result['page_title']}")
        logger.info(f"   HTML size: {result['html_size']} bytes")
        logger.info(f"   Body HTML size: {result['body_html_size']} bytes")
        
        if len(result['ids']) > 0:
            logger.info(f"   Sample IDs: {result['ids'][:10]}")
        
        # HTML kaydet
        with open("piccolo_test_headless.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info(f"\n   💾 piccolo_test_headless.html kaydedildi")
        
        # Başarı kontrolü
        success = len(result['ids']) > 0
        return success
        
    except Exception as e:
        logger.error(f"  ❌ Hata: {e}")
        return False
    
    finally:
        driver.quit()

if __name__ == "__main__":
    success = test_piccolo_headless()
    
    logger.info("\n" + "="*70)
    logger.info("SONUÇ")
    logger.info("="*70)
    
    if success:
        logger.info("  ✅ TEST BAŞARILI - Monitor'u başlatabilirsin!")
        logger.info("     python multi_site_monitor.py 180")
    else:
        logger.info("  ❌ TEST BAŞARILI DEĞİL - Debug HTML'i kontrol et:")
        logger.info("     cat piccolo_test_headless.html | head -200")
        logger.info("     grep 'data-id' piccolo_test_headless.html | wc -l")
    
    logger.info("="*70)

