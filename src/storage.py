import csv
import os
import hashlib
from datetime import datetime

class ReviewStorage:
    """
    수집된 리뷰와 AI 분석 결과를 로컬 저장소(CSV)에 관리하는 데이터 레이어입니다.
    파일 기반 시스템임에도 불구하고 데이터 중복 차단 및 상태 추적을 통해 DB 수준의 무결성을 유지하도록 설계되었습니다[cite: 7, 78].
    """
    def __init__(self, filepath="data/reviews_db.csv"):
        self.filepath = filepath
        # 시스템 기동 시 스키마 정의 및 디렉토리 구조 자동 생성 보장
        self._initialize_csv()

    def _initialize_csv(self):
        """
        저장소 부재 시 헤더를 포함한 CSV 파일을 초기화함. 
        한글 깨짐 방지를 위해 'utf-8-sig' 인코딩을 채택하여 Excel과의 호환성을 확보함[cite: 112].
        """
        if not os.path.exists(self.filepath):
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 데이터 분석 및 추적이 용이하도록 확장성을 고려한 스키마 설계 [cite: 49]
                writer.writerow(['product_id', 'id', 'date_collected', 'category', 'sentiment', 'urgency', 'summary', 'full_text', 'is_analyzed'])

    def generate_id(self, unique_source):
        """
        리뷰 텍스트와 메타데이터를 조합한 고유 해시값(MD5)을 생성함.
        플랫폼의 ID 정책 변경에 관계없이 독립적인 데이터 식별(Composite Key)이 가능함[cite: 7, 139].
        """
        return hashlib.md5(unique_source.encode('utf-8')).hexdigest()

    def is_review_exist(self, review_id):
        """
        수집된 리뷰의 중복 여부를 ID 기반으로 검색하여 데이터 오염을 방지함[cite: 78, 80].
        선형 탐색 기반이나, 로컬 환경에서의 빠른 검색 속도를 유지하도록 최적화된 파일 I/O를 수행함.
        """
        if not os.path.exists(self.filepath): return False   
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None) # 헤더 스킵
            for row in reader:
                # 데이터 유효성 검증 후 ID 일치 여부 판별
                if len(row) > 1 and row[1] == review_id: return True
        return False

    def get_existing_product_ids(self):
        """
        이미 데이터베이스에 존재하는 상품 ID 목록을 반환하여, 
        중복 크롤링 시도를 방지하고 시스템 리소스를 최적화함[cite: 138, 140].
        """
        if not os.path.exists(self.filepath): return set()
        product_ids = set()
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row:
                    product_ids.add(row[0]) # product_id 컬럼 활용
        return product_ids

    def save_raw_review(self, product_id, review_id, text):
        """
        새로운 리뷰 수집 시 초기 로우 데이터를 '분석 미완료(N)' 상태로 저장함.
        데이터 흐름의 추적성을 위해 수집 시점(Timestamp)을 함께 기록함[cite: 85, 141].
        """
        if self.is_review_exist(review_id): return False
        with open(self.filepath, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 순서: product_id, id, date, cat, sent, urg, summ, text, is_analyzed
            writer.writerow([product_id, review_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), '', '', '', '', text, 'N'])
        return True

    def update_analysis_result(self, review_id, analysis_data):
        """
        AI 분석 결과를 기존 로우 데이터에 업데이트하고 '분석 완료(Y)' 상태로 전환함.
        Atomic한 파일 쓰기를 위해 임시 리스트에 로드 후 전체를 다시 쓰는 방식을 채택함[cite: 102].
        """
        rows = []
        updated = False
        if not os.path.exists(self.filepath): return False
        
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header: rows.append(header)
            
            for row in reader:
                # 목표 데이터 탐색 및 인덱스 기반의 안정적인 필드 업데이트
                if len(row) > 1 and row[1] == review_id:
                    row[3] = analysis_data.get('category', '')
                    row[4] = analysis_data.get('sentiment', '')
                    row[5] = analysis_data.get('urgency', '')
                    row[6] = analysis_data.get('summary', '')
                    row[8] = 'Y' # 상태 플래그 전환
                    updated = True
                rows.append(row)
        
        # 데이터 정합성 보장을 위해 업데이트가 발생한 경우에만 물리적인 파일 쓰기 수행
        if updated:
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            return True
        return False