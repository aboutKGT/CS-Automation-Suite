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
# 🎛️ [운영 설정] 시스템 가동 모드 정의
# ==========================================
# FIRST_RUN_MODE가 True일 경우, 전체 상품에 대해 알림 없이 DB 동기화만 수행함.
# 이는 시스템 초기 구축 시 발생할 수 있는 '알림 폭탄'을 방어하기 위한 설계임
FIRST_RUN_MODE = False

with open("config/settings.yaml", "r", encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 실무 부서의 대응 속도와 서버 리소스 부하를 고려한 체크 주기 설정
CHECK_INTERVAL_MINUTES = 30
PRODUCTS = config.get('products', [])

def job():
    """
    정기적으로 실행되는 메인 파이프라인.
    수집(Crawler) -> 저장(Storage) -> 분석(Processor) -> 알림(Notifier)의 전 과정을 제어함.
    """
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n⏰ [스케줄러] 리뷰 수집 사이클 시작 ({current_time})")
    
    # 각 모듈의 독립성을 유지하기 위해 매 사이클마다 인스턴스를 초기화하여 
    # 이전 사이클의 상태가 다음 사이클에 영향을 주지 않도록 격리(Isolation)함
    crawler = GlowmCrawler()
    processor = ReviewProcessor()
    notifier = SlackNotifier()
    storage = ReviewStorage()
    
    # [Smart Mute 로직] 현재 데이터베이스에 등록된 상품 목록을 조회하여 신규 상품 여부 판별
    existing_products = storage.get_existing_product_ids()
    
    for product in PRODUCTS:
        p_id = product['id']
        p_name = product['name']
        p_url = product['url']
        
        # [의사결정 로직]
        # 신규 상품 등록 시 수백 건의 과거 리뷰가 한꺼번에 유입되므로,
        # 초기 구축(Initial Build) 시에만 자동으로 알림을 차단하는 지능형 뮤트 기능 적용
        is_new_product_entry = p_id not in existing_products
        should_mute = FIRST_RUN_MODE or is_new_product_entry
        
        print(f"\n   📦 상품 점검: {p_name} ({p_id})")
        if is_new_product_entry:
            print("      ✨ [New] 신규 등록된 상품 감지! 초기 DB 구축 모드로 가동합니다 (알림 OFF).")
        
        # 무한 루프나 과도한 페이지 탐색을 방지하기 위한 안전 장치(Safety Limit) 설정
        MAX_SAFETY_PAGES = 100 

        try:
            # 비동기 크롤러 실행을 동기 스케줄러 내에서 안전하게 래핑하여 실행
            new_reviews_data = asyncio.run(
                crawler.fetch_reviews(p_url, p_id, max_pages=MAX_SAFETY_PAGES, storage=storage)
            )
        except Exception as e:
            # 개별 상품의 오류가 전체 스케줄러 중단으로 번지지 않도록 예외 전파 차단
            print(f"   ❌ {p_name} 크롤링 도중 예외 발생: {e}")
            continue

        if not new_reviews_data:
            print(f"   💤 업데이트된 신규 리뷰가 없습니다.")
            continue

        print(f"   🚀 {len(new_reviews_data)}건의 신규 데이터 발견! 전처리 및 분석 시작...")

        batch_input = []
        raw_text_map = {} 
        
        for item in new_reviews_data:
            r_id = item['id']
            text = item['content']
            # 데이터 무결성을 보장하기 위해 분석 전 원본 데이터를 선행 저장
            storage.save_raw_review(p_id, r_id, text)
            batch_input.append({'id': r_id, 'text': text})
            raw_text_map[r_id] = text

        # [비용 최적화] API 호출 횟수를 줄이기 위해 10건 단위의 배치(Batch) 처리 수행
        CHUNK_SIZE = 10
        total_processed = 0
        
        for i in range(0, len(batch_input), CHUNK_SIZE):
            current_batch = batch_input[i : i + CHUNK_SIZE]
            print(f"   🧠 Gemini AI 분석 중 (Batch {i//CHUNK_SIZE + 1}: {len(current_batch)}건)...")
            
            # 지수 백오프 로직이 내장된 프로세서를 통해 안정적인 분석 결과 확보
            analysis_results = processor.analyze_reviews_batch(current_batch)

            if analysis_results:
                for result in analysis_results:
                    r_id = result.get('id')
                    if not r_id or r_id not in raw_text_map: continue
                    
                    # 수집된 원본 텍스트와 매칭하여 최종 데이터 완성
                    result['product_name'] = p_name
                    result['raw_text'] = raw_text_map[r_id]
                    
                    # DB 내 분석 결과 업데이트 및 상태 플래그 변경
                    storage.update_analysis_result(r_id, result)
                    
                    # [Smart Mute 적용] 실시간 모드일 때만 비개발 조직(CS팀)으로 알림 전송
                    if not should_mute:
                        notifier.send_notification(result)
                        # 슬랙 API의 Rate Limit을 고려한 짧은 스로틀링(Throttling)
                        time.sleep(1)
                    
                    total_processed += 1
            else:
                print("      ⚠️ 해당 Batch AI 분석 결과 수신 실패.")
            
            # 서버 부하 분산을 위한 배치 간 대기 시간 설정
            time.sleep(2)

        print(f"   ✅ {p_name} 처리 완료: 총 {total_processed}건 반영됨")
        time.sleep(3)

    print(f"\n🏁 전체 모니터링 사이클 완료! 다음 스케줄 대기 중...")

if __name__ == "__main__":
    print(f"🚀 [GLOW.M] 지능형 리뷰 자동화 모니터링 시스템 가동")
    print(f"   - 타겟 상품: {len(PRODUCTS)}개 리스트 로드 완료")
    print(f"   - 체크 주기: {CHECK_INTERVAL_MINUTES}분 간격")
    
    # 서버 재시작 시 데이터 공백을 막기 위해 즉시 1회 실행 후 스케줄 진입
    job()
    
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 시스템을 정상적으로 종료합니다.")
            break
        except Exception as e:
            # 예상치 못한 시스템 런타임 에러 발생 시 자동 복구 로직
            print(f"❌ 런타임 에러 발생: {e}. 1분 후 자동 재시도합니다.")
            time.sleep(60)