import schedule
import time
import asyncio
import os
import yaml
import sys

from src.crawler import GlowmCrawler
from src.processor import ReviewProcessor
from src.notifier import SlackNotifier
from src.storage import ReviewStorage

# ==========================================
# 🎛️ [설정] 글로벌 최초 실행 모드
# ==========================================
# True: 아예 전체 시스템이 알림을 끄고 1회만 돔
# False: 기본적으로 알림을 켬 (단, 신규 추가된 상품은 알아서 끔)
FIRST_RUN_MODE = False

with open("config/settings.yaml", "r", encoding='utf-8') as f:
    config = yaml.safe_load(f)

CHECK_INTERVAL_MINUTES = 30
PRODUCTS = config.get('products', [])

def job():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n⏰ [스케줄러] 리뷰 수집 시작 ({current_time})")
    
    crawler = GlowmCrawler()
    processor = ReviewProcessor()
    notifier = SlackNotifier()
    storage = ReviewStorage()
    
    # [핵심] 현재 DB에 존재하는 상품 ID 목록 가져오기
    existing_products = storage.get_existing_product_ids()
    
    for product in PRODUCTS:
        p_id = product['id']
        p_name = product['name']
        p_url = product['url']
        
        # [판단 로직]
        # 1. 글로벌 설정이 FIRST_RUN_MODE이면 -> 무조건 알림 OFF
        # 2. 이 상품 ID가 DB에 없으면(신규 상품) -> 이번만 알림 OFF (초기 구축)
        is_new_product_entry = p_id not in existing_products
        
        should_mute = FIRST_RUN_MODE or is_new_product_entry
        
        print(f"\n   📦 상품 점검: {p_name} ({p_id})")
        if is_new_product_entry:
            print("      ✨ [New] 신규 등록된 상품입니다! 초기 데이터 구축을 진행합니다 (알림 OFF).")
        
        MAX_SAFETY_PAGES = 100 

        try:
            new_reviews_data = asyncio.run(
                crawler.fetch_reviews(p_url, p_id, max_pages=MAX_SAFETY_PAGES, storage=storage)
            )
        except Exception as e:
            print(f"   ❌ {p_name} 크롤링 실패: {e}")
            continue

        if not new_reviews_data:
            print(f"   💤 신규 리뷰 없음.")
            continue

        print(f"   🚀 {len(new_reviews_data)}건 발견! 데이터 저장 및 분석 준비...")

        batch_input = []
        raw_text_map = {} 
        
        for item in new_reviews_data:
            r_id = item['id']
            text = item['content']
            storage.save_raw_review(p_id, r_id, text)
            batch_input.append({'id': r_id, 'text': text})
            raw_text_map[r_id] = text

        CHUNK_SIZE = 10
        total_processed = 0
        
        for i in range(0, len(batch_input), CHUNK_SIZE):
            current_batch = batch_input[i : i + CHUNK_SIZE]
            print(f"   🧠 Gemini 분석 요청 중 (Batch {i//CHUNK_SIZE + 1}: {len(current_batch)}건)...")
            
            analysis_results = processor.analyze_reviews_batch(current_batch)

            if analysis_results:
                for result in analysis_results:
                    r_id = result.get('id')
                    if not r_id or r_id not in raw_text_map: continue
                    
                    result['product_name'] = p_name
                    result['raw_text'] = raw_text_map[r_id]
                    
                    storage.update_analysis_result(r_id, result)
                    
                    # [핵심] should_mute가 False일 때만 보냄
                    if not should_mute:
                        notifier.send_notification(result)
                        time.sleep(1)
                    else:
                        # 로그만 남기고 알림은 스킵
                        pass
                    
                    total_processed += 1
            else:
                print("      ⚠️ 해당 Batch 분석 실패.")
            time.sleep(2)

        print(f"   ✅ {p_name} 처리 완료: 총 {total_processed}건 {'(알림 생략됨)' if should_mute else ''}")
        time.sleep(3)

    print(f"\n🏁 전체 사이클 완료!")

if __name__ == "__main__":
    print(f"🚀 [GLOW.M] 스마트 리뷰 모니터링 서버 가동")
    print(f"   - 타겟 상품 수: {len(PRODUCTS)}개")
    print(f"   - 주기: {CHECK_INTERVAL_MINUTES}분")
    
    # 서버 시작 시 1회 즉시 실행
    job()
    
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 에러: {e}")
            time.sleep(60)