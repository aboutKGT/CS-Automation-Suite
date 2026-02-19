import requests
import yaml
import json

class SlackNotifier:
    """
    분석된 리뷰 결과를 실무자(CS팀)에게 전달하는 알림 엔진입니다.
    정보의 가독성과 시급성에 따른 시각적 차별화에 중점을 두어 설계되었습니다.
    """
    def __init__(self):
        # 보안 및 유지보수를 위해 Webhook URL과 같은 민감 정보는 
        # 하드코딩하지 않고 외부 설정 파일(YAML)에서 주입받는 방식을 채택함
        with open("config/settings.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.webhook_url = config['slack']['webhook_url']

    def get_urgency_display(self, score):
        """
        수치화된 긴급도를 실무자가 직관적으로 인지할 수 있도록 시각적 요소(Emoji)로 변환함.
        이는 비개발 조직과의 협업 시 데이터 해석의 오류를 줄이기 위한 '의사결정 지원' 로직임
        """
        try:
            score = int(score)
        except:
            # 예상치 못한 데이터 형식 입력 시 시스템 중단을 막기 위한 방어적 기본값 설정
            score = 1
            
        if score <= 1:
            return "🟢 (낮음)"   # 일상적인 긍정/문의 리뷰
        elif score == 2:
            return "🟡 (보통)"   # 일반적인 피드백
        elif score == 3:
            return "🟠 (주의)"   # 빠른 확인이 필요한 건
        elif score == 4:
            return "🔥 (높음)"   # 잠재적 컴플레인 위험
        else:
            return "🚨 (매우 긴급)" # 즉각적인 대응이 필요한 심각한 이슈

    def send_notification(self, analysis_result):
        """
        LLM의 분석 결과물을 슬랙의 Block Kit 구조에 최적화하여 전송함.
        정보 계층 구조를 명확히 하여 담당자가 핵심 요약을 3초 내에 파악하도록 함
        """
        
        urgency_score = analysis_result.get('urgency', 1)
        urgency_display = self.get_urgency_display(urgency_score)
        
        # 긴급도에 따른 헤더 아이콘 가변 설정을 통해 알림 채널 내에서의 주목도 차별화
        header_icon = "🚨" if urgency_score >= 4 else "📢"

        # 정보의 가독성을 극대화하기 위한 슬랙 메시지 레이아웃 구성
        payload = {
            "text": f"{header_icon} *새로운 고객 리뷰 분석 결과*\n"
                    f"• *요약:* {analysis_result.get('summary', '요약 없음')}\n"
                    f"• *카테고리:* {analysis_result.get('category', '미분류')}\n"
                    f"• *감성:* {analysis_result.get('sentiment', '중립')}\n"
                    f"• *긴급도:* {urgency_display}\n"
                    f"• *내용:* {analysis_result.get('raw_text', '내용 없음')}"
        }

        try:
            # 외부 API 호출 시 발생할 수 있는 네트워크 예외 및 타임아웃에 대비한 예외 처리
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10 # 무한 대기를 방지하여 시스템 자원 고갈 예방
            )
            
            if response.status_code == 200:
                print(f"✅ 슬랙 알림 전송 성공! ({urgency_display})")
            else:
                # HTTP 상태 코드에 따른 트러블슈팅 로그 남김
                print(f"❌ 슬랙 알림 전송 실패: {response.status_code}")
        except Exception as e:
            # 네트워크 단절 등 예외 상황 발생 시 파이프라인 전체가 죽지 않도록 독립적 로깅 수행
            print(f"❌ 슬랙 연동 중 오류 발생: {e}")

if __name__ == "__main__":
    # 단위 테스트를 통해 모듈의 독립적인 작동 여부를 검증함
    notifier = SlackNotifier()
    test_data = {
        "summary": "하드케이스 디자인 만족",
        "category": "디자인",
        "sentiment": "긍정",
        "urgency": 1,
        "raw_text": "하얀색의 하드케이스가 눈이부실정도로 영롱하네요"
    }
    notifier.send_notification(test_data)