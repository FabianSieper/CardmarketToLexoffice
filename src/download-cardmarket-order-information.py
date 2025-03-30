# This file is not currently used, as the excel file is currently downloaded manually

import os
import time

from playwright.sync_api import sync_playwright

cardMarketUsername = os.getenv("CARDMARKET_USERNAME")
cardMarketPassword = os.getenv("CARDMARKET_PASSWORD")

def extract_cardmarket_info() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.cardmarket.com/en")
        page.get_by_role("textbox", name="Username").click()
        page.get_by_role("textbox", name="Username").fill(cardMarketUsername)
        page.get_by_role("textbox", name="Password").click()
        page.get_by_role("textbox", name="Password").fill(cardMarketPassword)
        page.get_by_role("button", name="Log in").click()
        page.locator("a#account-dropdown").click()
        page.get_by_role("link", name=" Account").click()
        page.get_by_role("link", name=" Statistics").click()
        # TODO: select month where 1 is January and 12 is December
        page.get_by_label("Month").first.select_option("2")
        page.get_by_role("button", name="Export (.csv)").first.click()
        page.get_by_role("link", name=" Downloads").click()
        # TODO: download latest file

        time.sleep(10)
        # ---------------------
        context.close()
        browser.close()


if __name__ == "__main__":
    extract_cardmarket_info()
