import asyncio
from playwright.async_api import async_playwright

class GlowmCrawler:
    def __init__(self):
        self.text_selector = "p.alp-body15" 
        self.min_length = 5
        self.blacklist_keywords = ["의료기기", "개인차", "제공받아"]

    def is_valid_review(self, text):
        for keyword in self.blacklist_keywords:
            if keyword in text: return False
        if len(text.strip()) < self.min_length: return False
        return True

    async def fetch_reviews(self, url, product_id, max_pages=100, storage=None):
        async with async_playwright() as p:
            # 실전 운영 시 headless=True 권장
            browser = await p.chromium.launch(headless=True) 
            context = await browser.new_context(viewport={"width": 1280, "height": 1080})
            page = await context.new_page()
            
            print(f"🌐 접속 중: {url}")
            await page.goto(url)
            print("   ⏳ 페이지 로딩 대기 중 (5초)...")
            await page.wait_for_timeout(5000)
            
            new_reviews_collected = []
            stop_crawling = False
            
            for current_page in range(1, max_pages + 1):
                if stop_crawling: break

                print(f"📄 [Page {current_page}] 수집 시작...")
                
                # 스크롤 로직
                review_found = False
                for _ in range(5):
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(1)
                    if await page.locator(self.text_selector).count() > 0:
                        review_found = True
                        break
                
                if not review_found:
                    print("   ⛔ 리뷰 위젯을 못 찾았습니다.")
                    break

                review_elements = await page.query_selector_all(self.text_selector)
                page_new_count = 0
                
                for element in review_elements:
                    content = await element.inner_text()
                    content = content.strip()
                    
                    if not self.is_valid_review(content):
                        continue
                    
                    try:
                        full_context = await element.evaluate("el => el.parentElement.parentElement.innerText")
                    except:
                        full_context = content
                    
                    if storage:
                        unique_source = f"{product_id}_{full_context}"
                        review_id = storage.generate_id(unique_source)
                        
                        if storage.is_review_exist(review_id):
                            print(f"   🛑 이미 처리한 리뷰 발견! (여기서 수집 종료)")
                            stop_crawling = True
                            break 

                        new_reviews_collected.append({
                            'content': content,
                            'id': review_id
                        })
                        page_new_count += 1
                
                print(f"   -> {page_new_count}개의 신규 리뷰 확보")
                
                if stop_crawling: break

                # [페이지 이동 및 검증 로직 개선]
                try:
                    pagination_bar = page.locator("review-number-pagination .pagination-layout--desktop")
                    if await pagination_bar.count() > 0:
                        icon_buttons = pagination_bar.locator("button:has(svg)")
                        if await icon_buttons.count() > 0:
                            next_btn = icon_buttons.last
                            
                            if await next_btn.is_disabled():
                                print("   ✅ 마지막 페이지입니다 (버튼 비활성).")
                                break
                            
                            class_attr = await next_btn.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                print("   ✅ 마지막 페이지입니다 (클래스 체크).")
                                break

                            # [헬퍼 함수] 유효한 첫 번째 리뷰 텍스트 찾기 (공지사항 건너뛰기)
                            async def get_first_valid_text():
                                elements = await page.query_selector_all(self.text_selector)
                                for el in elements:
                                    text = (await el.inner_text()).strip()
                                    # 공지사항(의료기기 등)이 아니면 바로 반환
                                    if self.is_valid_review(text):
                                        return text
                                return None # 유효한 리뷰가 하나도 없는 경우

                            # 1. 이동 전 '진짜' 첫 리뷰 기억
                            current_valid_text = await get_first_valid_text()

                            # 2. 다음 버튼 클릭
                            await next_btn.click()
                            
                            print("   ⏳ 다음 페이지 로딩 대기 (5초)...")
                            await page.wait_for_timeout(5000)
                            
                            # 3. 이동 후 '진짜' 첫 리뷰 확인
                            new_valid_text = await get_first_valid_text()

                            # 4. 비교 (둘 다 유효한 리뷰가 있을 때만)
                            if current_valid_text and new_valid_text:
                                if current_valid_text == new_valid_text:
                                    print(f"      ⚠️ [Stuck 감지] 이전: '{current_valid_text[:10]}...' vs 현재: '{new_valid_text[:10]}...'")
                                    print("      ⚠️ 데이터가 갱신되지 않아 3초 추가 대기합니다...")
                                    await page.wait_for_timeout(3000)
                            
                        else:
                            break
                    else:
                        break
                except Exception as e:
                    print(f"   ⚠️ 페이지 이동 중 오류: {e}")
                    break
            
            await browser.close()
            return new_reviews_collected