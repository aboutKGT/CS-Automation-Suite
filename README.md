# 🚀 CS-Automation-Suite: AI 기반 리뷰 모니터링 시스템

이커머스 플랫폼의 고객 리뷰를 실시간으로 수집하고, LLM(Gemini)을 통해 감정 및 시급성을 분석하여 슬랙(Slack)으로 즉시 알림을 보내는 자동화 파이프라인입니다.

## 📌 주요 특징 (Key Features)

* **증분 수집 (Incremental Crawling):** 모든 리뷰를 매번 긁어오지 않습니다. 로컬 DB와 비교하여 중복된 리뷰를 발견하는 즉시 수집을 중단하여 자원 소모를 최소화합니다.
* **Batch AI 분석:** 리뷰 1개당 API를 호출하는 대신, 여러 개의 리뷰를 묶어 한 번에 분석(Batch Processing)함으로써 API 할당량(RPD/RPM)을 최적화하고 비용을 절감합니다.
* **지능형 CS 분류:** 단순 텍스트 수집을 넘어 배송, 제품 질감, 기능성 등 카테고리를 자동 분류하고 1~5점 척도의 시급성을 판단합니다.
* **실시간 슬랙 알림:** 분석된 결과 중 대응이 필요한 리뷰를 담당자에게 즉시 전달하여 CS 대응 속도를 높입니다.

## 🛠 Tech Stack

* **Language:** Python 3.10+
* **Crawling:** Playwright (Asynchronous)
* **AI:** Google Gemini 1.5 Flash API
* **Storage:** CSV-based Local Database
* **Notification:** Slack Webhook API
* **Scheduler:** Python `schedule` library

## 📂 Project Structure

```text
CS-Automation-Suite/
├── config/
│   └── settings.yaml    # API 키 및 타겟 URL 설정
├── data/
│   └── reviews_db.csv   # 수집된 리뷰 데이터베이스
├── src/
│   ├── crawler.py       # Playwright 기반 증분 크롤러
│   ├── processor.py     # Gemini API Batch 분석 엔진
│   ├── storage.py       # 데이터 저장 및 중복 체크 로직
│   └── notifier.py      # 슬랙 알림 발송 모듈
└── scheduler.py         # 전체 프로세스 통합 및 주기적 실행 제어
```

🚀 How to Run
1. 환경 변수 설정
config/settings.yaml 파일에 Gemini API 키와 Slack Webhook URL을 입력합니다.

2. 의존성 설치
Bash
pip install -r requirements.txt
playwright install chromium
3. 실행

Bash
python scheduler.py
📈 Future Roadmap
[ ] 멀티 URL(여러 상품 페이지) 동시 모니터링 지원

[ ] 분석 데이터 시각화 대시보드 (Streamlit) 구축

[ ] 데이터베이스 SQLite/PostgreSQL 전환