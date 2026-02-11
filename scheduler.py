import schedule
import time
import asyncio
import os
import random

# 우리가 만든 모듈들 가져오기
from src.crawler import GlowmCrawler
from src.processor import ReviewProcessor
from src.notifier import SlackNotifier
from src.storage import ReviewStorage

# --- [설정 구간] ---
CHECK_INTERVAL_MINUTES = 30 
TARGET_URL = "https://theglowm.com/product/%EA%B8%80%EB%A1%9C%EC%9A%B0%EC%97%A0-%ED%94%84%EB%A6%AC%EB%AF%B8%EC%97%84-%ED%95%98%EB%93%9C-%EC%BC%80%EC%9D%B4%EC%8A%A4/46/category/42/display/1/"

def job():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n⏰ [스케줄러] 리뷰 검토 시작 ({current_time})...")
    
    crawler = GlowmCrawler()
    processor = ReviewProcessor()
    notifier = SlackNotifier()
    storage = ReviewStorage()

    is_first_run = not os.path.exists("data/reviews_db.csv")
    max_pages = 20 if is_first_run else 100

    print(f"   👉 전략: {'최초 구축 모드' if is_first_run else '모니터링 모드'}")

    try:
        # 1. 신규 리뷰 수집
        new_reviews = asyncio.run(
            crawler.fetch_reviews(TARGET_URL, max_pages=max_pages, storage=storage)
        )
    except Exception as e:
        print(f"❌ 크롤링 중 치명적 오류 발생: {e}")
        return

    if not new_reviews:
        print(f"💤 새로 등록된 리뷰가 없습니다.")
        return

    print(f"🚀 {len(new_reviews)}개의 신규 리뷰 발견! Batch 분석을 준비합니다.")

    # 2. Batch 분석을 위한 데이터 포맷팅
    # 분석에 필요한 ID와 텍스트 쌍을 만듭니다.
    batch_input = []
    raw_text_map = {} # 나중에 원본 텍스트를 다시 찾기 위한 매핑용
    
    for text in new_reviews:
        r_id = storage.generate_id(text)
        batch_input.append({'id': r_id, 'text': text})
        raw_text_map[r_id] = text

    # 3. AI Batch 분석 실행 (한 번에 묶어서 전송!)
    print(f"🧠 Gemini Batch 분석 중... (리뷰 {len(batch_input)}개)")
    analysis_results = processor.analyze_reviews_batch(batch_input)

    # 4. 분석 결과 처리 및 알림
    success_count = 0
    if analysis_results:
        for result in analysis_results:
            r_id = result.get('id')
            if not r_id or r_id not in raw_text_map:
                continue
                
            # 원본 텍스트와 결과 합치기
            result['raw_text'] = raw_text_map[r_id]
            
            # DB 저장
            storage.save_review(result)
            
            # 슬랙 전송 (최초 구축 모드가 아닐 때만 발송하거나 필터링 가능)
            notifier.send_notification(result)
            success_count += 1
            
            # 슬랙 메시지 간격 유지 (슬랙 API 가이드 준수)
            time.sleep(1) 
    else:
        print("⚠️ Batch 분석 결과가 비어 있습니다.")

    print(f"🏁 작업 완료! 총 {success_count}건의 신규 리뷰를 처리했습니다.")

# --- [서버 가동 루프] ---
schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)

print(f"🚀 [GLOW.M] CS 자동화 서버 가동 시작 (Batch 모드)")
print(f"   - 주기: {CHECK_INTERVAL_MINUTES}분")
print(f"   - 타겟: {TARGET_URL}")

# 즉시 실행
job()

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 서버를 종료합니다.")
        break
    except Exception as e:
        print(f"\n❌ 스케줄러 루프 에러: {e}")
        time.sleep(60)