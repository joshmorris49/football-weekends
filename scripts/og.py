"""Render scripts/og.html to og.png (1200x630), the image shown when the site link is shared."""
import pathlib
from playwright.sync_api import sync_playwright

src = pathlib.Path(__file__).with_name("og.html").resolve()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto(src.as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(src.parent.parent / "og.png"))
    b.close()
print("wrote og.png")
