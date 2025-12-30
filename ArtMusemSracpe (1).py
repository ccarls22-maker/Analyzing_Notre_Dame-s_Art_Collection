
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://marble.nd.edu/search?campuslocation[0]=Raclin%20Murphy%20Museum%20of%20Art&images[0]=true"

def scrape_artwork_details(driver, artwork_url):
    """Scrape detailed information from an individual artwork page"""
    try:
        driver.get(artwork_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(7)
        
        details = {}
        
        # Try to find metadata sections - these might be in different formats
        # Look for key-value pairs in metadata sections
        metadata_sections = driver.find_elements(By.CSS_SELECTOR, ".metadata, .details, .artwork-details, [class*='meta']")
        
        for section in metadata_sections:
            try:
                # Look for dt/dd pairs (definition lists)
                dt_elements = section.find_elements(By.CSS_SELECTOR, "dt")
                dd_elements = section.find_elements(By.CSS_SELECTOR, "dd")
                
                for dt, dd in zip(dt_elements, dd_elements):
                    key = dt.text.strip().lower().replace(":", "")
                    value = dd.text.strip()
                    if key and value:
                        details[key] = value
                        
                # Look for labeled paragraphs or divs
                labeled_items = section.find_elements(By.CSS_SELECTOR, "[class*='label'], [class*='field']")
                for item in labeled_items:
                    text = item.text.strip()
                    if ":" in text:
                        key, value = text.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key and value:
                            details[key] = value
            except Exception:
                continue
                
        # Extract specific fields we're looking for
        return {
            "classification": details.get("classification", details.get("type", details.get("object type", ""))),
            "related_location": details.get("related location", details.get("location", details.get("provenance", ""))),
            "medium": details.get("medium", details.get("materials", details.get("technique", ""))),
            "dimensions": details.get("dimensions", details.get("size", details.get("measurements", ""))),
            "credit_line": details.get("credit line", details.get("credit", details.get("acquisition", ""))),
            "copyright_status": details.get("copyright status", details.get("copyright", details.get("rights", "")))
        }
    except Exception as e:
        print(f"Error scraping details from {artwork_url}: {e}")
        return {
            "classification": "",
            "related_location": "",
            "medium": "",
            "dimensions": "",
            "credit_line": "",
            "copyright_status": ""
        }

options = Options()
# Comment out headless mode for debugging
# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(BASE_URL)
print("Browser opened. Please check if artwork cards are visible in the window.")
time.sleep(15)  # Wait longer for manual observation and dynamic content

# Phase 1: Collect all basic artwork info from all pages
print("Phase 1: Collecting all artwork links from search results...")
basic_records = []
page = 1
while True:
    print(f"Scraping search results page {page}...")
    cards = driver.find_elements(By.CSS_SELECTOR, ".card.css-1b7lok9")
    if not cards:
        print("No cards found on this page. Printing page source for debugging...")
        with open(f"debug_page_source_page{page}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        break

    # Store the first card's title to detect page change
    first_card_title = ""
    if cards:
        try:
            first_card_title = cards[0].find_element(By.CSS_SELECTOR, "h2.css-1m7l3d1").text.strip()
        except Exception:
            first_card_title = ""

    for card in cards:
        try:
            a_tag = card.find_element(By.CSS_SELECTOR, "a.css-1g0qgzq")
            link = a_tag.get_attribute("href")
            if link and link.startswith("/"):
                link = f"https://marble.nd.edu{link}"
            title = card.find_element(By.CSS_SELECTOR, "h2.css-1m7l3d1").text.strip()
            p_tags = card.find_elements(By.CSS_SELECTOR, "p.css-1jho06n")
            artist = p_tags[0].text.strip() if len(p_tags) > 0 else ""
            year = p_tags[1].text.strip() if len(p_tags) > 1 else ""
        except Exception:
            title = ""
            link = ""
            artist = ""
            year = ""
        
        basic_records.append({"title": title, "link": link, "artist": artist, "year": year})

    # Try to click the next page button
    try:
        # Find the Next button using the correct selector
        next_btn = driver.find_element(By.CSS_SELECTOR, "div.sk-toggle-option.sk-toggle__item[data-key='next']")
        # Check if the button is visible and clickable
        if not next_btn.is_displayed():
            print("Next button not visible. Stopping.")
            break
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
        time.sleep(0.5)
        # Use JavaScript click for reliability
        driver.execute_script("arguments[0].click();", next_btn)
        page += 1
        # Wait for the first card's title to change (indicating new page loaded)
        def title_changed(driver):
            try:
                new_cards = driver.find_elements(By.CSS_SELECTOR, ".card.css-1b7lok9")
                if not new_cards:
                    return False
                new_title = new_cards[0].find_element(By.CSS_SELECTOR, "h2.css-1m7l3d1").text.strip()
                return new_title != first_card_title
            except Exception:
                return False
        WebDriverWait(driver, 15).until(title_changed)
        time.sleep(1)
    except Exception as e:
        print(f"No more pages or error clicking next: {e}")
        break

print(f"Total basic records collected: {len(basic_records)}")

# Phase 2: Visit each artwork page to get detailed information
print("\nPhase 2: Collecting detailed information from individual artwork pages...")
detailed_records = []

for i, basic_record in enumerate(basic_records):
    print(f"Scraping details for artwork {i+1}/{len(basic_records)}: {basic_record['title'][:50]}...")
    
    # Create detailed record starting with basic info
    detailed_record = basic_record.copy()
    
    # If we have a valid link, scrape detailed information
    if basic_record['link']:
        details = scrape_artwork_details(driver, basic_record['link'])
        detailed_record.update(details)
    else:
        # Add empty detail fields if no link
        detailed_record.update({
            "classification": "",
            "related_location": "",
            "medium": "",
            "dimensions": "",
            "credit_line": "",
            "copyright_status": ""
        })
    
    detailed_records.append(detailed_record)

    time.sleep(0.5)

driver.quit()

print(f"Total artworks with detailed information: {len(detailed_records)}")

with open("raclin_murphy_artworks_detailed.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "link", "artist", "year", "classification", "related_location", "medium", "dimensions", "credit_line", "copyright_status"])
    writer.writeheader()
    writer.writerows(detailed_records)

print("Saved raclin_murphy_artworks_detailed.csv")
