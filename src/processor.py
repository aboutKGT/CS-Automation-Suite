from google import genai
import yaml
import json
import time

class ReviewProcessor:
    """
    수집된 리뷰 데이터를 LLM(Gemini)을 통해 의미론적으로 분석하는 엔진입니다.
    Batch 처리를 통한 비용 최적화와 지수 백오프 기반의 장애 복구 로직이 적용되었습니다. [cite: 165, 166]
    """
    def __init__(self):
        # 유연한 모델 교체 및 보안 관리를 위해 설정을 외부화함 [cite: 85]
        with open("config/settings.yaml", "r", encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Google GenAI 최신 SDK(v1.0+) 클라이언트 초기화
        self.client = genai.Client(api_key=self.config['gemini']['api_key'])
        # 환경에 따라 다른 모델(Flash/Pro 등)을 적용할 수 있도록 설정값 주입
        self.model_name = self.config['gemini']['model_name']

    def analyze_reviews_batch(self, reviews):
        """
        N개의 리뷰를 하나의 컨텍스트로 묶어 처리함으로써 API 호출 횟수와 토큰 비용을 최적화함. 
        reviews: [{'id': '...', 'text': '...'}, ...] 형태의 리스트
        """
        if not reviews:
            return []

        # LLM으로부터 구조화된 데이터(JSON)를 안정적으로 얻기 위한 프롬프트 엔지니어링 수행
        prompt = f"""
        다음은 고객 리뷰 데이터입니다. 각 리뷰를 분석하여 JSON 형식으로 반환하세요.
        
        [분석 가이드]
        1. category: 배송, 제품품질, 가격, 서비스, 기타 중 하나
        2. sentiment: 긍정, 부정, 중립 중 하나
        3. urgency: 1(매우 낮음) ~ 5(매우 높음) 정수 (부정적이거나 배송/품질 문제는 높게 책정)
        4. summary: 핵심 내용을 10자 이내로 요약

        [입력 데이터]
        {json.dumps(reviews, ensure_ascii=False)}

        [출력 형식 예시]
        [
            {{"id": "리뷰ID", "category": "배송", "sentiment": "부정", "urgency": 4, "summary": "배송이 너무 늦음"}},
            ...
        ]
        
        반드시 JSON 리스트만 출력하세요. 마크다운 태그(```json)는 쓰지 마세요.
        """

        # [Resilience] 외부 API의 일시적 장애(503) 및 Rate Limit에 대응하기 위한 재시도 설계 
        max_retries = 5 
        base_wait_time = 2 # 초기 대기 시간 2초

        for attempt in range(max_retries):
            try:
                # 비정형 데이터를 정형 데이터로 변환하는 핵심 인지 로직 실행
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                
                # LLM 응답 텍스트에 포함될 수 있는 불필요한 마크다운 태그 정제(Cleaning)
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                
                # 정제된 텍스트를 파이썬 객체로 변환하여 후속 모듈(storage/notifier)로 전달
                return json.loads(text)

            except Exception as e:
                # [Exponential Backoff] 실패 시 대기 시간을 지수적으로 늘려(2s -> 4s -> 8s...) 
                # 대상 서버의 부하를 방지하고 성공 확률을 높임 
                wait_time = base_wait_time * (2 ** attempt)
                print(f"      ⚠️ API 오류 발생 ({e})... {wait_time}초 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        
        # 최대 재시도 횟수 초과 시, 시스템 전체 중단을 막기 위해 에러 로깅 후 해당 배치 건너뜀
        print(f"      ❌ 최종 실패: {len(reviews)}건의 리뷰 분석을 건너뜁니다.")
        return []