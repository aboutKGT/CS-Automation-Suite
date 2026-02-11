from google import genai
from google.genai import types
import yaml
import json
import time

class ReviewProcessor:
    def __init__(self):
        with open("config/settings.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.api_key = config['gemini']['api_key']
        self.model_name = config['gemini'].get('model_name', 'gemini-1.5-flash')
        self.client = genai.Client(api_key=self.api_key)

    def analyze_reviews_batch(self, review_items):
        """
        여러 개의 리뷰를 한 번에 분석합니다.
        review_items: [{'id': '...', 'text': '...'}, ...] 형태의 리스트
        """
        if not review_items:
            return []

        # 프롬프트 구성
        reviews_formatted = "\n".join([f"- [ID: {item['id']}] {item['text']}" for item in review_items])
        
        prompt = f"""
        당신은 이커머스 CS 분석 전문가입니다. 
        제공된 고객 리뷰 리스트를 분석하여 다음 규칙에 따라 JSON 리스트 형식으로만 응답하세요.
        각 결과는 반드시 입력된 ID를 포함해야 합니다.

        [분류 규칙]
        1. category: '배송', '제품 질감', '기능성', '디자인', '서비스', '기타' 중 하나.
        2. sentiment: '긍정', '부정', '중립' 중 하나.
        3. urgency: 1~5점 (1: 단순칭찬, 5: 즉각대응필요).
        4. summary: 20자 이내 요약.

        [리뷰 리스트]
        {reviews_formatted}

        [응답 형식 예시]
        [
            {{"id": "...", "category": "...", "sentiment": "...", "urgency": 1, "summary": "..."}},
            ...
        ]
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                if response.text:
                    results = json.loads(response.text)
                    return results if isinstance(results, list) else [results]
                
            except Exception as e:
                if "503" in str(e) or "429" in str(e):
                    print(f"⚠️ 서버 혼잡 발생 (Batch 시도 {attempt+1}/{max_retries}). 대기 후 재시도...")
                    time.sleep(5) # Batch는 양이 많으므로 좀 더 길게 쉼
                else:
                    print(f"❌ Gemini 분석 중 치명적 오류: {e}")
                    return []
        
        return []

    def analyze_review(self, text):
        """기존 단일 리뷰 분석 (하위 호환용)"""
        # 간단하게 하려면 1개짜리 리스트를 Batch로 보내서 첫 번째 결과만 리턴해도 됩니다.
        result = self.analyze_reviews_batch([{'id': 'single', 'text': text}])
        return result[0] if result else None

if __name__ == "__main__":
    processor = ReviewProcessor()
    samples = [
        {'id': '1', 'text': '보관할때 용이하게 쓰는중이용'},
        {'id': '2', 'text': '배송이 너무 느려요. 일주일 넘게 걸렸네요.'}
    ]
    print("Batch 분석 시작...")
    results = processor.analyze_reviews_batch(samples)
    print("분석 결과:", json.dumps(results, indent=2, ensure_ascii=False))