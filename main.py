import os
from playwright.sync_api import sync_playwright
import logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.page = None

    def get_profile_data(self, profile_url: str) -> dict:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            self.page = browser.new_page()

            try:
                self._login()
                self._navigate_to_profile(profile_url)
                profile_data = self._scrape_profile_data()
                self._navigate_to_recent_posts(profile_url)
                profile_data["posts"] = self._scrape_recent_posts()
                return profile_data
            except Exception as e:
                logger.error(f"Error scraping profile: {str(e)}")
                return None
            finally:
                browser.close()

    def _login(self):
        self.page.goto("https://www.linkedin.com/login")
        self.page.fill("#username", self.username)
        self.page.fill("#password", self.password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle")

        # After login LindkedIn redirects to /feed page
        if "feed" not in self.page.url:
            logger.error("Login failed")
            raise Exception("Login failed")

        logger.info("Login successful, going to profile page")

    def _navigate_to_profile(self, profile_url):
        self.page.goto(profile_url)
        self.page.wait_for_load_state("networkidle")

    def _scrape_profile_data(self):
        name = self.page.text_content(".text-heading-xlarge")
        headline = self.page.text_content(".text-body-medium")

        if not name or not headline:
            raise Exception("Failed to fetch name or headline from profile.")

        logger.info(f"Scraped profile: {name} - {headline}")
        return {
            "name": name.strip(),
            "headline": headline.strip(),
        }

    def _navigate_to_recent_posts(self, profile_url):
        feeds_url = f"{profile_url}/recent-activity/all/"
        self.page.goto(feeds_url)
        self.page.wait_for_load_state("networkidle")

    def _scrape_recent_posts(self):
        posts = []
        self.page.wait_for_selector(".feed-shared-update-v2", timeout=10000)
        post_elements = self.page.query_selector_all(".feed-shared-update-v2")

        if not len(post_elements):
            logger.warning("No posts found")
        else:
            for post in post_elements[:5]:
                try:
                    post_content_element = post.query_selector(
                        ".update-components-text"
                    )
                    if post_content_element:
                        post_text = post_content_element.text_content()
                        posts.append(post_text.strip())
                except Exception as e:
                    logger.error(f"Error getting post text {str(e)}, skipping")
                    continue

        logger.info(f"Scraped {len(posts)} posts")
        return posts


if __name__ == "__main__":
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    profile_url = "https://www.linkedin.com/in/aniket-bajpai"

    scraper = LinkedInScraper(username, password)
    data = scraper.get_profile_data(profile_url)
    print(data)
