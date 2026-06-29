import feedparser
from curl_cffi import requests


def check_feed(url):
    print(f"\n--- Checking {url} ---")
    session = requests.Session(impersonate="chrome120")
    resp = session.get(url, timeout=15)
    parsed = feedparser.parse(resp.content)

    if not parsed.entries:
        print("No entries.")
        return

    entry = parsed.entries[0]

    content_html = getattr(entry, 'content', [{'value': ''}])[0]['value'] if hasattr(entry, 'content') else getattr(entry, 'summary', '')

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content_html, 'html.parser')
    imgs = soup.find_all('img')
    print(f"Found {len(imgs)} img tags in HTML.")
    for img in imgs:
        print("IMG:", img.attrs)

check_feed("https://www.macrumors.com/macrumors.xml")
