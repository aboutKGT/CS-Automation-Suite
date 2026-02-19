import asyncio
from playwright.async_api import async_playwright

class GlowmCrawler:
    """
    이커머스 플랫폼의 리뷰 데이터를 수집하는 최적화된 크롤링 엔진입니다.
    네트워크 지연, 동적 로딩, 데이터 중복 및 안티 크롤링 우회를 고려하여 설계되었습니다.
    """
    def __init__(self):
        # AI 분석의 품질을 높이기 위해 노이즈(광고, 짧은 글)를 제거하는 필터링 상수를 정의함
        self.text_selector = "p.alp-body15" 
        self.min_length = 5
        self.blacklist_keywords = ["의료기기", "개인차", "제공받아"]

    def is_valid_review(self, text):
        """
        수집 단계에서 데이터 클렌징을 수행하여 LLM API 비용을 절감하고 분석 정확도를 높임.
        """
        for keyword in self.blacklist_keywords:
            if keyword in text: return False
        if len(text.strip()) < self.min_length: return False
        return True

    async def fetch_reviews(self, url, product_id, max_pages=100, storage=None):
        """
        비동기 브라우저 제어를 통한 리뷰 수집 메인 파이프라인.
        증분 수집(Incremental Crawling) 방식을 채택하여 리소스를 최적화함.
        """
        async with async_playwright() as p:
            # 서버 리소스 점유를 최소화하기 위해 Headless 모드를 기본으로 사용함
            browser = await p.chromium.launch(headless=True) 
            # 실제 사용자와 유사한 Viewport 설정을 통해 봇 감지 알고리즘을 우회함
            context = await browser.new_context(viewport={"width": 1280, "height": 1080})
            page = await context.new_page()
            
            print(f"🌐 접속 중: {url}")
            await page.goto(url)
            # SPA(Single Page Application) 특유의 무거운 렌더링을 고려한 충분한 초기 로딩 대기
            print("   ⏳ 페이지 로딩 대기 중 (5초)...")
            await page.wait_for_timeout(5000)
            
            new_reviews_collected = []
            stop_crawling = False
            
            for current_page in range(1, max_pages + 1):
                if stop_crawling: break

                print(f"📄 [Page {current_page}] 수집 시작...")
                
                # [Anti-Crawling 대응] 마우스 휠 스크롤을 시뮬레이션하여 
                # 지연 로딩(Lazy Loading)된 리뷰 위젯의 렌더링을 강제로 트리거함
                review_found = False
                for _ in range(5):
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(1) # 네트워크 응답 시간을 고려한 짧은 폴링(Polling) 대기
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
                    
                    # 리뷰의 컨텍스트를 풍부하게 확보하기 위해 부모 요소를 포함한 전체 텍스트 수집
                    try:
                        full_context = await element.evaluate("el => el.parentElement.parentElement.innerText")
                    except:
                        full_context = content
                    
                    # [데이터 무결성 관리] MD5 해시 기반 고유 ID를 생성하여 중복 수집을 기술적으로 차단
                    if storage:
                        unique_source = f"{product_id}_{full_context}"
                        review_id = storage.generate_id(unique_source)
                        
                        # 이미 수집된 기록이 있다면 즉시 중단하여 네트워크 부하를 줄임 (증분 수집 전략)
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

                # [페이지 네이션 안정성 강화]
                try:
                    pagination_bar = page.locator("review-number-pagination .pagination-layout--desktop")
                    if await pagination_bar.count() > 0:
                        icon_buttons = pagination_bar.locator("button:has(svg)")
                        if await icon_buttons.count() > 0:
                            next_btn = icon_buttons.last
                            
                            # 비활성화된 버튼을 체크하여 파이프라인의 정상 종료 시점을 판별함
                            if await next_btn.is_disabled():
                                print("   ✅ 마지막 페이지입니다 (버튼 비활성).")
                                break
                            
                            class_attr = await next_btn.get_attribute("class")
                            if class_attr and "disabled" in class_attr:
                                print("   ✅ 마지막 페이지입니다 (클래스 체크).")
                                break

                            # [Stuck 감지 로직] 버튼을 눌렀음에도 데이터가 갱신되지 않는 현상을 방어함
                            async def get_first_valid_text():
                                elements = await page.query_selector_all(self.text_selector)
                                for el in elements:
                                    text = (await el.inner_text()).strip()
                                    if self.is_valid_review(text):
                                        return text
                                return None 

                            # 1. 클릭 전 데이터 스냅샷 저장
                            current_valid_text = await get_first_valid_text()

                            # 2. 다음 페이지 이동 시뮬레이션
                            await next_btn.click()
                            
                            print("   ⏳ 다음 페이지 로딩 대기 (5초)...")
                            await page.wait_for_timeout(5000)
                            
                            # 3. 이동 후 데이터 비교를 통해 실질적 렌더링 완료 여부 검증
                            new_valid_text = await get_first_valid_text()

                            if current_valid_text and new_valid_text:
                                if current_valid_text == new_valid_text:
                                    # 네트워크 지연으로 데이터가 늦게 올 경우를 대비한 방어적 추가 대기
                                    print(f"      ⚠️ [Stuck 감지] 데이터 미갱신. 추가 대기 수행...")
                                    await page.wait_for_timeout(3000)
                            
                        else:
                            break
                    else:
                        break
                except Exception as e:
                    # 페이지 이동 중 발생하는 예외를 개별 처리하여 안정성 확보
                    print(f"   ⚠️ 페이지 이동 중 오류: {e}")
                    break
            
            # 브라우저 리소스 해제를 보장하여 시스템 부하 방지
            await browser.close()
            return new_reviews_collected