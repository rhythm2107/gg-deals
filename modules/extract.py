from bs4 import BeautifulSoup
from modules.config import BASE_URL

# Helper Functions
def extract_drm_from_listing(listing_html):
    """Extract DRM from the listing HTML."""
    soup = BeautifulSoup(listing_html, 'html.parser')
    drm_tag = soup.find("div", class_="tag-drm")
    if drm_tag:
        svg_tag = drm_tag.find("svg")
        if svg_tag and "title" in svg_tag.attrs:
            return svg_tag["title"].replace("Activates on ", "").strip()
    return None


def extract_listing_details(listing_html):
    """Extract additional details (game name, URL, price) from a listing."""
    soup = BeautifulSoup(listing_html, 'html.parser')

    # Full game name and URL
    link_tag = soup.find("a", class_="full-link")
    if link_tag:
        game_name = link_tag.get("aria-label", "").replace("Go to: ", "").strip()
        listing_url = BASE_URL + link_tag.get("href", "")
    else:
        game_name = "Unknown Game"
        listing_url = None

    # Current price
    price = soup.find("div", class_="hoverable-box").get("data-deal-value", None)

    return game_name, listing_url, float(price) if price else None