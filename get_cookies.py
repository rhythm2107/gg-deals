from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

chromedriver_path = r"C:\Users\Rhythm\Desktop\chromedriver-win64\chromedriver.exe"

def get_gg_deals_session():
    # Set up Selenium WebDriver
    print(f"Using ChromeDriver Path: {chromedriver_path}")
    service = Service(chromedriver_path)
    options = webdriver.ChromeOptions()
    # Disable headless for debugging
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open GGDeals page
        driver.get("https://gg.deals/deals/new-deals/")
        print("Browser launched successfully!")

        # Retrieve cookies
        cookies = driver.get_cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        gg_session = cookie_dict.get('gg-session')
        gg_csrf = cookie_dict.get('gg_csrf')

        # Extract CSRF token from HTML
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']

        return gg_session, gg_csrf, csrf_token
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Quitting driver")
        driver.quit()

# Test the function
if __name__ == "__main__":
    cookies = get_gg_deals_session()
    print(cookies)
    print('gg-session:', cookies[0])
    print('gg_csrf', cookies[1])
    print('session_csrf_token:', cookies[2])
