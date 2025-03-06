from trafilatura import fetch_url, extract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def get_side_bar_text():
    driver = webdriver.Chrome()
    try:
        driver.get("https://developer-docs.amazon.com/sp-api/docs/welcome")

        # Wait for the sidebar to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#hub-sidebar"))
        )

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
                        href = "https://developer-docs.amazon.com" + href
                    sidebar_links.append(href)
            except Exception as e:
                print(f"Skipping element due to: {str(e)}")
                continue

        return list(set(sidebar_links))
    except Exception as e:
        print(f"Error in get_side_bar_text: {str(e)}")
        return []
    finally:
        driver.quit()

def scrape_page(url):
    try:
        downloaded = fetch_url(url)
        if not downloaded:
            print(f"Failed to download content from {url}")
            return None
            
        content = extract(downloaded)
        if not content:
            print(f"Failed to extract content from {url}")
            return None
            
        return content
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None
    
def test_scrape_first_five():
    # Get sidebar links
    links = get_side_bar_text()
    
    # Take first 5 links
    test_links = links[:5]
    
    # Scrape each link and write to separate files
    for i, link in enumerate(test_links):
        content = scrape_page(link)
        if content:
            filename = f'amazon_docs_summary_{i+1}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Content written to {filename}")
        else:
            print(f"Could not extract content from {link}")
                
    print("Content from first 5 links written to separate files")
    return True



def test_sidebar_links():
    # Get sidebar links
    links = get_side_bar_text()
        
    # Write first few links to a test file
    with open('test_links.txt', 'w') as f:
        # Write first 5 links as a sample
        for i, link in enumerate(links[:5]):
            f.write(f"{i+1}. {link}\n")
        
    print(f"Total links found: {len(links)}")
    print("First 5 links written to test_links.txt")
    return len(links) > 0

if __name__ == "__main__":
    # test_sidebar_links()
    test_scrape_first_five()


    


