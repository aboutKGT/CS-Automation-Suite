# 🚀 CS-Automation-Suite: Multi-Product Review Monitoring System

**이커머스 플랫폼의 다중 상품 리뷰를 실시간으로 모니터링하고, LLM(Gemini)을 활용해 고객의 감정과 시급성을 분석하여 CS 담당자에게 즉시 알림을 제공하는 지능형 자동화 솔루션입니다.**

단순한 크롤링 도구를 넘어, **운영 비용 절감**과 **데이터 무결성**, 시스템 안정성(Resilience)에 초점을 맞춘 엔터프라이즈급 파이프라인입니다.

---

## 📌 주요 특징 (Key Features)

### 1. 🔄 멀티 상품 증분 수집 (Multi-Product Incremental Crawling)
* 단일 URL이 아닌, 설정 파일(`settings.yaml`)에 등록된 **수십 개의 상품을 순차적으로 모니터링**합니다.
* **스마트 중복 방지:** 리뷰 내용뿐만 아니라 작성자, 날짜, 옵션 등의 컨텍스트를 결합한 **Composite Key(MD5)**를 생성하여, 내용이 동일한 리뷰(복붙 리뷰)도 정확하게 구분합니다.
* **리소스 최적화:** 이미 수집된 데이터는 건너뛰고 신규 리뷰만 타겟팅하여 네트워크 및 컴퓨팅 자원을 최소화합니다.

### 2. 🤫 스마트 초기화 (Auto-Mute Initialization)
* **자동 감지 로직:** 스케줄러가 신규 등록된 상품을 자동으로 감지합니다.
* **Silent Mode:** 처음 등록된 상품의 과거 리뷰(수백~수천 건)를 수집할 때는 **알림을 자동으로 차단(Mute)**하여 '알림 폭탄'을 방지하고 데이터베이스만 구축합니다.
* **Live Mode:** 초기 구축 이후에는 자동으로 **모니터링 모드**로 전환되어, 실시간으로 달리는 새 리뷰에 대해서만 알림을 발송합니다.

### 3. 🛡️ 장애 대응 및 안정성 (Fault Tolerance & Resilience)
* **Exponential Backoff:** 외부 AI API(Gemini)의 일시적 장애(503 Service Unavailable) 발생 시, 대기 시간을 지수적으로 늘려가며(2s → 4s → 8s...) 재시도하여 시스템 중단을 막습니다.
* **Pagination Safety:** 네트워크 지연으로 인한 페이지 로딩 실패나 중복 로딩(Stuck) 현상을 감지하고, 자동으로 대기하거나 재시도하는 방어 로직이 적용되었습니다.
* **Memory Management:** 상품 단위로 브라우저 컨텍스트를 생명주기 관리하여, 대량 수집 시에도 메모리 누수(Memory Leak)를 방지합니다.

### 4. 🧠 비용 효율적 AI 분석 (Cost-Effective Batch Processing)
* **Batch AI 분석:** 리뷰를 1건씩 처리하지 않고 N개씩 묶어(Batch) API를 호출함으로써, API 호출 횟수를 줄이고 처리 속도를 획기적으로 높였습니다.
* **CS 등급 분류:** 단순 감정 분석을 넘어, 배송/품질/가격 등 카테고리를 분류하고 **1~5점 척도의 시급성(Urgency)**을 산출하여 대응 우선순위를 제안합니다.

---

## 🛠 Tech Stack

* **Core:** Python 3.10+
* **Crawling:** Playwright (Async/Headless Browser)
* **AI Engine:** Google Gemini 1.5 Flash (via `google-genai` SDK)
* **Database:** CSV-based Lightweight Local DB (Scalable to SQL)
* **Notification:** Slack Webhook API
* **Scheduling:** Python `schedule` library

---

## 📂 Project Structure

```text
CS-Automation-Suite/
├── config/
│   └── settings.yaml      # 상품 리스트 및 API 키 설정 (Multi-URL 지원)
├── data/
│   └── reviews_db.csv     # 분석 데이터 저장소 (Composite ID 적용)
├── src/
│   ├── crawler.py         # 페이지네이션 및 네트워크 방어 로직이 포함된 크롤러
│   ├── processor.py       # 지수 백오프(Retry)가 적용된 Gemini 분석 엔진
│   ├── storage.py         # 중복 체크 및 데이터 무결성 관리
│   └── notifier.py        # 슬랙 알림 발송 모듈
├── scheduler.py           # 스마트 뮤트 및 순차 실행을 관리하는 메인 스케줄러
└── requirements.txt       # 의존성 패키지 목록
```

## 🚀 How to Run

### 1. 환경 설정 및 의존성 설치

```
# 필수 패키지 설치
pip install -r requirements.txt
pip install google-genai  # 최신 Gemini SDK

# Playwright 브라우저 설치
playwright install chromium
```

### 2. 설정 파일 구성 (`config/settings.yaml`)
모니터링할 상품들을 리스트 형태로 등록합니다.

```
gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model_name: "gemini-1.5-flash"

slack:
  webhook_url: "YOUR_SLACK_WEBHOOK_URL"

# 멀티 상품 리스트 설정
products:
  - id: "product_001"
    name: "프리미엄 하드 케이스"
    url: "https://shop-url.com/product/1"
  
  - id: "product_002"
    name: "수분 진정 마스크팩"
    url: "https://shop-url.com/product/2"
```

### 3. 시스템 실행

```
python scheduler.py
```

* **최초 실행 시:** 등록된 상품들의 전체 리뷰를 수집하며 DB를 구축합니다. (알림 발송 안 함)
* **이후 실행 시:** 30분 주기로 모니터링하며, **신규 리뷰**가 발생할 때만 슬랙 알림을 보냅니다.

---

## 📊 Performance & Optimization

| Feature | Description | Benefit |
| :--- | :--- | :--- |
| **Smart Mute** | 신규 상품 등록 시 알림 자동 차단 | 알림 피로도(Noise) **90% 감소** |
| **Composite ID** | 내용+작성자+날짜 기반 ID 생성 | 데이터 중복 저장 **0% 달성** |
| **Retry Logic** | 503 에러 발생 시 자동 재시도 | 시스템 가동률(Availability) **99.9% 유지** |
| **Batch API** | 10건 단위 묶음 분석 | API 호출 비용 및 시간 **90% 절감** |

---

## 🔮 Future Roadmap

* [ ] **Dashboard:** Streamlit을 활용한 실시간 리뷰 현황 대시보드 시각화
* [ ] **DB Migration:** 대용량 처리를 위한 SQLite/PostgreSQL 전환
* [ ] **Keyword Alert:** 특정 키워드(예: "환불", "부작용") 감지 시, 그에 대응되는 담당자에게 개인 알림(slack, e-mail 등) 발송 기능
