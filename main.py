import asyncio
from src.crawler import GlowmCrawler
from src.processor import ReviewProcessor
from src.notifier import SlackNotifier

async def main():
    # 1. 각 모듈 초기화
    crawler = GlowmCrawler()
    processor = ReviewProcessor()
    notifier = SlackNotifier()

    # 2. 분석할 대상 제품 URL 리스트
    product_urls = [
        "https://theglowm.com/product/%EA%B8%80%EB%A1%9C%EC%9A%B0%EC%97%A0-%ED%94%84%EB%A6%AC%EB%AF%B8%EC%97%84-%ED%95%98%EB%93%9C-%EC%BC%80%EC%9D%B4%EC%8A%A4/46/category/42/display/1/",
        # 추가 제품이 있다면 여기에 URL을 더 넣으면 됩니다.
    ]

    print("🚀 CS 자동화 파이프라인 가동 시작...")

    for url in product_urls:
        # 3. [Step 1] 크롤링: 리뷰 데이터 수집
        reviews = await crawler.fetch_reviews(url)
        
        if not reviews:
            print(f"⏩ {url}: 수집된 유효 리뷰가 없습니다.")
            continue

        print(f"📦 총 {len(reviews)}개의 리뷰에 대한 분석을 시작합니다.")

        for raw_text in reviews:
            # 4. [Step 2] 분석: LLM을 통한 카테고리/긴급도 분류
            print(f"🧠 리뷰 분석 중: {raw_text[:20]}...")
            analysis_result = processor.analyze_review(raw_text)
            
            if analysis_result:
                # 알림 메시지에 원본 텍스트를 포함시키기 위해 추가
                analysis_result['raw_text'] = raw_text
                
                # 5. [Step 3] 알림: 슬랙으로 전송
                notifier.send_notification(analysis_result)
            
    print("🏁 모든 작업이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(main())