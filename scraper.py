import time
import random
import os
from playwright.sync_api import sync_playwright
from datetime import datetime


class ErpInventoryScraper:
    def __init__(self, url, user_id, password):
        self.url = url
        self.user_id = user_id
        self.password = password

    def _random_sleep(self, min_seconds, max_seconds):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _human_type(self, page, selector, text):
        try:
            page.click(selector, timeout=3000)
        except:
            pass

        for char in text:
            page.keyboard.type(char, delay=random.randint(50, 150))
        self._random_sleep(0.5, 1.0)

    def download_excel(self, download_dir):
        os.makedirs(download_dir, exist_ok=True)
        print("🚀 프로세스 시작")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                accept_downloads=True,
            )

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            page = context.new_page()

            print(f"▶ 1. 접속: {self.url}")
            page.goto(self.url)
            page.wait_for_load_state("networkidle")

            print("▶ 2. 로그인")
            self._human_type(page, "#f_id-inputEl", self.user_id)
            self._human_type(page, "#f_pwd-inputEl", self.password)
            page.click("#image-1009")
            page.wait_for_load_state("networkidle")
            self._random_sleep(3.0, 4.0)

            print("▶ 3.1. 재고 메뉴")
            try:
                page.locator('xpath=//*[@id="treeview-1041-record-25"]/tbody/tr/td').click()
            except Exception as e:
                print(f"  ⚠️ ID 선택자 실패: {e}")
            self._random_sleep(1.0, 2.0)

            print("▶ 3.2. 재고조회")
            try:
                page.get_by_text("재고조회", exact=True).click()
            except:
                print("  ⚠️ 텍스트 클릭 실패")
            self._random_sleep(1.0, 2.0)

            print("▶ 3.3. 재고현황")
            try:
                page.locator('xpath=//*[@id="treeview-1041-record-32"]/tbody/tr/td/div/span').click()
            except:
                print("  ⚠️ ID 선택자 실패, 텍스트로 재시도")
                page.get_by_text("재고현황", exact=True).click()

            print("  ⏳ 데이터 로딩 대기 (5초)")
            time.sleep(5)

            print("▶ 4.1. iframe 전환 및 검색")
            main_frame = page.frame_locator("#main_tab_1_iframe")
            search_input = main_frame.locator('input[name="ITEM_CD"]')

            try:
                search_input.wait_for(state="visible", timeout=10000)
                search_input.click()
                search_input.press("Enter")
                print("  ⏳ 검색 결과 대기 (5초)")
                time.sleep(5)
            except Exception as e:
                print(f"❌ 검색창 조작 실패: {e}")
                page.screenshot(path="error_iframe_search.png")
                browser.close()
                return None

            print("▶ 4.2. 엑셀 다운로드")
            save_path = None
            try:
                main_frame.locator("#allStockButton1").click()
                self._random_sleep(0.5, 1.0)

                download_menu = main_frame.get_by_text("전체 데이터 다운로드")
                if not download_menu.is_visible():
                    download_menu = page.get_by_text("전체 데이터 다운로드")

                with page.expect_download(timeout=30000) as download_info:
                    download_menu.click()

                download = download_info.value
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(download_dir, f"inventory_{timestamp}.xlsx")
                download.save_as(save_path)
                print(f"✅ 다운로드 완료: {save_path}")

            except Exception as e:
                print(f"❌ 다운로드 실패: {e}")

            time.sleep(3)
            browser.close()
            return save_path

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    scraper = ErpInventoryScraper(
        url=os.getenv("ERP_URL"),
        user_id=os.getenv("ERP_ID"),
        password=os.getenv("ERP_PASSWORD"),
    )
    result = scraper.download_excel(download_dir="./downloads")
    print(f"저장 경로: {result}")
