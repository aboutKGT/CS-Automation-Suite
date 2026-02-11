import requests
import yaml
import json

class SlackNotifier:
    def __init__(self):
        # 설정 파일에서 Webhook URL 로드
        with open("config/settings.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.webhook_url = config['slack']['webhook_url']

    def get_urgency_display(self, score):
        """점수에 따른 이모지와 텍스트를 반환합니다."""
        try:
            score = int(score)
        except:
            score = 1
            
        if score <= 1:
            return "🟢 (낮음)"   # 1점: 평화로움
        elif score == 2:
            return "🟡 (보통)"   # 2점: 단순 문의 등
        elif score == 3:
            return "🟠 (주의)"   # 3점: 신경 써야 함
        elif score == 4:
            return "🔥 (높음)"   # 4점: 불남
        else:
            return "🚨 (매우 긴급)" # 5점: 비상 사태

    def send_notification(self, analysis_result):
        """분석 결과를 슬랙 메시지로 전송합니다."""
        
        urgency_score = analysis_result.get('urgency', 1)
        urgency_display = self.get_urgency_display(urgency_score)
        
        # 헤더 이모지도 긴급도에 따라 다르게 설정 (긴급하면 🚨, 아니면 📢)
        header_icon = "🚨" if urgency_score >= 4 else "📢"

        # 슬랙 메시지 포맷 설정
        payload = {
            "text": f"{header_icon} *새로운 고객 리뷰 분석 결과*\n"
                    f"• *요약:* {analysis_result.get('summary', '요약 없음')}\n"
                    f"• *카테고리:* {analysis_result.get('category', '미분류')}\n"
                    f"• *감성:* {analysis_result.get('sentiment', '중립')}\n"
                    f"• *긴급도:* {urgency_display}\n"
                    f"• *내용:* {analysis_result.get('raw_text', '내용 없음')}"
        }

        try:
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                print(f"✅ 슬랙 알림 전송 성공! ({urgency_display})")
            else:
                print(f"❌ 슬랙 알림 전송 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 슬랙 연동 중 오류 발생: {e}")

if __name__ == "__main__":
    # 단독 테스트용
    notifier = SlackNotifier()
    test_data = {
        "summary": "하드케이스 디자인 만족",
        "category": "디자인",
        "sentiment": "긍정",
        "urgency": 1,
        "raw_text": "하얀색의 하드케이스가 눈이부실정도로 영롱하네요"
    }
    notifier.send_notification(test_data)