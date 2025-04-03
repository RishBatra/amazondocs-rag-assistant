from trafilatura import fetch_url, extract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import URL_PATHS
import time

def get_side_bar_links():
    driver = webdriver.Chrome()
    try:
        driver.get(URL_PATHS["base_url"] + URL_PATHS["api_docs_url"])

        # Wait for the sidebar to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#hub-sidebar"))
        )
        time.sleep(2)

        # Get all sidebar links in one go
        sidebar_links = []
        sections = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[class*='Sidebar-link']"))
        )
        
        for section in sections:
            try:
                href = section.get_attribute('href')
                if href:
                    if not href.startswith("http"):
                        href = URL_PATHS["base_url"] + href
                    sidebar_links.append(href)
            except Exception as e:
                print(f"Skipping element due to: {str(e)}")
                continue

        return list(set(sidebar_links))
    except Exception as e:
        print(f"Error in get_side_bar_links: {str(e)}")
        return []
    finally:
        driver.quit()

def scrape_page(url):
    try:
        downloaded = fetch_url(url)
        if not downloaded:
            print(f"Failed to download content from {url}")
            return None
            
        content = extract(
            downloaded,
            output_format = "markdown"
            )
        if not content:
            print(f"Failed to extract content from {url}")
            return None
            
        return content
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None
