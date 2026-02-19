# 🚀 CS-Automation-Suite: Multi-Product Review Monitoring System

**단순한 크롤링을 넘어, 실제 운영 환경에서의 비용 효율과 알림 피로도 문제를 엔지니어링으로 해결한 리뷰 모니터링 도구**

브랜드가 성장함에 따라 수동으로 확인하기 어려워진 고객 리뷰를 Playwright와 Gemini LLM을 결합해 자동화했습니다. 특히, 초기 데이터 구축 시 발생하는 '알림 폭탄' 문제와 AI 추론 비용을 최적화하는 데 초점을 맞췄습니다.

---

## 📌 주요 특징 (Key Features)

### 1. 🔄 멀티 상품 증분 수집 (Multi-Product Incremental Crawling)
* 단일 URL이 아닌, 설정 파일(`settings.yaml`)에 등록된 **수십 개의 상품을 순차적으로 모니터링**합니다.
* **스마트 중복 방지:** 리뷰 내용뿐만 아니라 작성자, 날짜, 옵션 등의 컨텍스트를 결합한 **Composite Key(MD5)** 를 생성하여, 내용이 동일한 리뷰(복붙 리뷰)도 정확하게 구분합니다.
* **리소스 최적화:** 이미 수집된 데이터는 건너뛰고 신규 리뷰만 타겟팅하여 네트워크 및 컴퓨팅 자원을 최소화합니다.

### 2. 🤫 스마트 초기화 (Auto-Mute Initialization)
* **자동 감지 로직:** 스케줄러가 신규 등록된 상품을 자동으로 감지합니다.
* **Silent Mode:** 처음 등록된 상품의 과거 리뷰(수백~수천 건)를 수집할 때는 **알림을 자동으로 차단(Mute)** 하여 '알림 폭탄'을 방지하고 데이터베이스만 구축합니다.
* **Live Mode:** 초기 구축 이후에는 자동으로 **모니터링 모드**로 전환되어, 실시간으로 달리는 새 리뷰에 대해서만 알림을 발송합니다.

### 3. 🛡️ 장애 대응 및 안정성 (Fault Tolerance & Resilience)
* **Exponential Backoff:** 외부 AI API(Gemini)의 일시적 장애(503 Service Unavailable) 발생 시, 대기 시간을 지수적으로 늘려가며(2s → 4s → 8s...) 재시도하여 시스템 중단을 막습니다.
* **Pagination Safety:** 네트워크 지연으로 인한 페이지 로딩 실패나 중복 로딩(Stuck) 현상을 감지하고, 자동으로 대기하거나 재시도하는 방어 로직이 적용되었습니다.
* **Memory Management:** 상품 단위로 브라우저 컨텍스트를 생명주기 관리하여, 대량 수집 시에도 메모리 누수(Memory Leak)를 방지합니다.

### 4. 🧠 비용 효율적 AI 분석 (Cost-Effective Batch Processing)
* **Batch AI 분석:** 리뷰를 1건씩 처리하지 않고 N개씩 묶어(Batch) API를 호출함으로써, API 호출 횟수를 줄이고 처리 속도를 획기적으로 높였습니다.
* **CS 등급 분류:** 단순 감정 분석을 넘어, 배송/품질/가격 등 카테고리를 분류하고 **1~5점 척도의 시급성(Urgency)** 을 산출하여 대응 우선순위를 제안합니다.

---

## 🛠️ Development Challenges & Solutions
1. Gemini API 503 장애 및 Rate Limit 대응
문제: 대량의 리뷰 분석 시 외부 API의 일시적 장애나 속도 제한으로 전체 프로세스가 중단되는 현상 발생.
해결: 단순 재시도가 아닌 **Exponential Backoff(지수 백오프)** 로직을 적용하여 시스템의 회복 탄력성(Resilience)을 확보했습니다.

2. 데이터 무결성을 위한 Composite Key 설계
문제: 같은 내용의 리뷰라도 플랫폼 내부 ID가 바뀌거나 중복 수집될 경우 발생하는 데이터 왜곡 문제.
해결: 리뷰 본문, 작성자, 날짜를 조합한 **MD5 해시값(Composite Key)** 을 생성하여, 데이터베이스 수준에서 중복을 0%로 차단했습니다.

3. 장기 가동 시 메모리 누수 방지
문제: Headless 브라우저 특성상 수십 개의 상품을 연속 크롤링할 때 메모리 점유율이 지속적으로 상승함.
해결: 상품별로 브라우저 컨텍스트의 **생명주기를 엄격히 분리(Close/New Context)** 하여 장시간 구동에도 안정적인 메모리 수치를 유지하도록 설계했습니다.

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
  api_key: "GEMINI_API_KEY"
  model_name: "gemini-flash-latest"

slack:
  webhook_url: "SLACK_WEBHOOK_URL"

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
| **Smart Mute** | 신규 상품 등록 시 알림 자동 차단 | 신규 상품 등록 시 발생하는 **불필요한 알림 피로도 제거** |
| **Batch AI** | 10건 단위 묶음 분석 요청 | 개별 호출 대비 **API 처리 속도 향상 및 비용 최적화** |
| **Retry Logic** | 지수 백오프 기반 재시도 모듈 | 외부 API 장애 상황에서도 **수집 파이프라인의 연속성 보장** |

---

## 🔮 Future Roadmap

* [ ] **Dashboard:** Streamlit을 활용한 실시간 리뷰 현황 대시보드 시각화
* [ ] **DB Migration:** 대용량 처리를 위한 SQLite/PostgreSQL 전환
* [ ] **Keyword Alert:** 특정 키워드(예: "환불", "부작용") 감지 시, 그에 대응되는 담당자에게 개인 알림(slack, e-mail 등) 발송 기능
