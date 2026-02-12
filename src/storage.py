import csv
import os
import hashlib
from datetime import datetime

class ReviewStorage:
    def __init__(self, filepath="data/reviews_db.csv"):
        self.filepath = filepath
        self._initialize_csv()

    def _initialize_csv(self):
        if not os.path.exists(self.filepath):
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['product_id', 'id', 'date_collected', 'category', 'sentiment', 'urgency', 'summary', 'full_text', 'is_analyzed'])

    def generate_id(self, unique_source):
        return hashlib.md5(unique_source.encode('utf-8')).hexdigest()

    def is_review_exist(self, review_id):
        if not os.path.exists(self.filepath): return False   
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) > 1 and row[1] == review_id: return True
        return False

    # [신규 추가] 이미 수집된 적 있는 product_id 목록 반환
    def get_existing_product_ids(self):
        if not os.path.exists(self.filepath): return set()
        product_ids = set()
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None) # 헤더 스킵
            for row in reader:
                if row:
                    product_ids.add(row[0]) # product_id는 0번째 컬럼
        return product_ids

    def save_raw_review(self, product_id, review_id, text):
        if self.is_review_exist(review_id): return False
        with open(self.filepath, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([product_id, review_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), '', '', '', '', text, 'N'])
        return True

    def update_analysis_result(self, review_id, analysis_data):
        rows = []
        updated = False
        if not os.path.exists(self.filepath): return False
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header: rows.append(header)
            for row in reader:
                if len(row) > 1 and row[1] == review_id:
                    row[3] = analysis_data.get('category', '')
                    row[4] = analysis_data.get('sentiment', '')
                    row[5] = analysis_data.get('urgency', '')
                    row[6] = analysis_data.get('summary', '')
                    row[8] = 'Y'
                    updated = True
                rows.append(row)
        if updated:
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            return True
        return False