from google import genai
import yaml
import json
import time

class ReviewProcessor:
    def __init__(self):
        # 설정 파일 로드
        with open("config/settings.yaml", "r", encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # [수정] 신규 SDK 클라이언트 초기화 방식 (Client 객체 생성)
        self.client = genai.Client(api_key=self.config['gemini']['api_key'])
        # settings.yaml에 있는 모델명(예: gemini-1.5-flash)을 가져옴
        self.model_name = self.config['gemini']['model_name']

    def analyze_reviews_batch(self, reviews):
        """
        여러 리뷰(딕셔너리 리스트)를 받아 한 번에 분석합니다.
        reviews: [{'id': '...', 'text': '...'}, ...]
        """
        if not reviews:
            return []

        # 프롬프트 구성 (기존과 동일)
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

        # 재시도 로직 (Exponential Backoff)
        max_retries = 5 
        base_wait_time = 2 

        for attempt in range(max_retries):
            try:
                # [수정] 신규 SDK 호출 방식 (client.models.generate_content)
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                
                # 응답 텍스트 정제
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                
                return json.loads(text)

            except Exception as e:
                # 실패 시 대기 시간을 2배씩 늘림
                wait_time = base_wait_time * (2 ** attempt)
                print(f"      ⚠️ API 오류 발생 ({e})... {wait_time}초 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        
        print(f"      ❌ 최종 실패: {len(reviews)}건의 리뷰 분석을 건너뜁니다.")
        return []