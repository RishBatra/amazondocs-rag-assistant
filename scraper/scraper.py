from trafilatura import fetch_url, extract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import URL_PATHS
import time
import requests
from bs4 import BeautifulSoup

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

def scrape_page(url, use_bs=False):
    if not use_bs:
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
    else:
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                print(f"Failed to fetch {url} with status {resp.status_code}")
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove the value of the 'dehydrated' attribute from all elements
            for tag in soup.find_all(attrs={'dehydrated': True}):
                tag['dehydrated'] = ''
            # Only extract from <article class="rm-Article ">
            main = soup.find('article')
            if not main:
                print("Main article container not found.")
                return None
            lines = []
            table_signatures = set()  # Track unique tables
            for tag in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table', 'pre', 'code', 'ul', 'ol', 'li'], recursive=True):
                if tag.name == 'h1':
                    lines.append(f"# {tag.get_text(strip=True)}\n")
                elif tag.name == 'h2':
                    lines.append(f"## {tag.get_text(strip=True)}\n")
                elif tag.name == 'h3':
                    lines.append(f"### {tag.get_text(strip=True)}\n")
                elif tag.name == 'h4':
                    lines.append(f"#### {tag.get_text(strip=True)}\n")
                elif tag.name == 'h5':
                    lines.append(f"##### {tag.get_text(strip=True)}\n")
                elif tag.name == 'h6':
                    lines.append(f"###### {tag.get_text(strip=True)}\n")
                elif tag.name == 'p':
                    lines.append(tag.get_text(strip=True) + '\n')
                elif tag.name == 'ul':
                    for li in tag.find_all('li', recursive=False):
                        lines.append(f"- {li.get_text(strip=True)}\n")
                elif tag.name == 'ol':
                    for idx, li in enumerate(tag.find_all('li', recursive=False), 1):
                        lines.append(f"{idx}. {li.get_text(strip=True)}\n")
                elif tag.name == 'table':
                    # Improved deduplication: normalize cell text, ignore empty rows
                    rows = tag.find_all('tr')
                    table_signature = []
                    for row in rows:
                        cols = [col.get_text(strip=True).lower() for col in row.find_all(['th', 'td'])]
                        if cols:  # Ignore empty rows
                            table_signature.append('|'.join(cols))
                    signature_str = '\n'.join(table_signature)
                    if signature_str in table_signatures:
                        continue  # Skip duplicate table
                    table_signatures.add(signature_str)

                    md_table = []
                    for i, row in enumerate(rows):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        md_table.append('| ' + ' | '.join(cols) + ' |')
                        if i == 0:
                            md_table.append('|' + '|'.join(['---'] * len(cols)) + '|')
                    lines.append('\n'.join(md_table) + '\n')
                elif tag.name in ['pre', 'code']:
                    # Only process if not already handled as data-lang="json"
                    if tag.has_attr('data-lang') and tag['data-lang'] == 'json':
                        continue
                    code_text = tag.get_text('\n')
                    code_text_stripped = code_text.strip()
                    if code_text_stripped.startswith('{') and code_text_stripped.endswith('}'):
                        lines.append(f"```\n{code_text}\n```\n")
                    elif tag.name == 'pre':
                        lines.append(f"CODE:\n{code_text}:CODE\n")
            return '\n'.join(lines)
        except Exception as e:
            print(f"Error scraping with BeautifulSoup {url}: {str(e)}")
            return None
