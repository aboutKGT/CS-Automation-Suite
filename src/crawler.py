import asyncio
from playwright.async_api import async_playwright

class GlowmCrawler:
    def __init__(self):
        # 리뷰 텍스트 선택자
        self.text_selector = "p.alp-body15" 
        self.min_length = 5
        self.blacklist_keywords = ["의료기기", "개인차", "제공받아"]

    def is_valid_review(self, text):
        """리뷰 유효성 검사"""
        for keyword in self.blacklist_keywords:
            if keyword in text: return False
        if len(text.strip()) < self.min_length: return False
        return True

    async def fetch_reviews(self, url, max_pages=100, storage=None):
        async with async_playwright() as p:
            # 실전에서는 headless=True (창 안 띄움) 추천
            # 눈으로 보고 싶으면 False로 바꾸세요.
            browser = await p.chromium.launch(headless=True) 
            context = await browser.new_context(viewport={"width": 1280, "height": 1080})
            page = await context.new_page()
            
            print(f"🌐 접속 중: {url}")
            await page.goto(url)
            
            new_reviews_collected = []
            stop_crawling = False  # 중복 발견 시 멈추기 위한 신호
            
            for current_page in range(1, max_pages + 1):
                if stop_crawling:
                    break

                print(f"📄 [Page {current_page}] 수집 시작...")
                
                # 1. 사람처럼 천천히 스크롤 (로딩 유도)
                review_found = False
                for _ in range(5):
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(1)
                    if await page.locator(self.text_selector).count() > 0:
                        review_found = True
                        break
                
                if not review_found:
                    print("   ⛔ 리뷰 위젯을 못 찾았습니다 (로딩 실패/리뷰 없음).")
                    break

                # 2. 리뷰 수집 및 중복 검사
                reviews = await page.query_selector_all(self.text_selector)
                page_new_count = 0
                
                for review in reviews:
                    content = await review.inner_text()
                    content = content.strip()
                    
                    if not self.is_valid_review(content):
                        continue
                        
                    # [핵심 로직] DB 중복 체크
                    if storage:
                        review_id = storage.generate_id(content)
                        if storage.is_review_exist(review_id):
                            print(f"   🛑 이미 처리한 리뷰 발견! (여기서 수집 종료)")
                            stop_crawling = True
                            break 

                    new_reviews_collected.append(content)
                    page_new_count += 1
                
                print(f"   -> {page_new_count}개의 신규 리뷰 확보")
                
                if stop_crawling:
                    break

                # 3. 다음 페이지 이동
                try:
                    pagination_bar = page.locator("review-number-pagination .pagination-layout--desktop")
                    if await pagination_bar.count() > 0:
                        icon_buttons = pagination_bar.locator("button:has(svg)")
                        if await icon_buttons.count() > 0:
                            next_btn = icon_buttons.last
                            
                            # 마지막 페이지 체크
                            if await next_btn.is_disabled():
                                print("   ✅ 마지막 페이지입니다.")
                                break
                            
                            class_attr = await next_btn.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                print("   ✅ 마지막 페이지입니다.")
                                break

                            await next_btn.click()
                            await page.wait_for_timeout(3000)
                        else:
                            break
                    else:
                        break
                except Exception:
                    break
            
            await browser.close()
            return new_reviews_collected