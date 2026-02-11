import csv
import os
import hashlib
from datetime import datetime

class ReviewStorage:
    def __init__(self, filepath="data/reviews_db.csv"):
        self.filepath = filepath
        self._ensure_directory()
        self._initialize_csv()

    def _ensure_directory(self):
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def _initialize_csv(self):
        """파일이 없으면 헤더(제목줄)를 만듭니다."""
        if not os.path.exists(self.filepath):
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 필요한 항목들을 정의합니다.
                writer.writerow(['id', 'date_collected', 'category', 'sentiment', 'urgency', 'summary', 'full_text'])

    def generate_id(self, text):
        """리뷰 내용으로 주민등록번호(고유 ID)를 만듭니다."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def is_review_exist(self, review_id):
        """이 리뷰가 이미 DB에 있는지 확인합니다."""
        if not os.path.exists(self.filepath):
            return False
        
        with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None) # 헤더 건너뛰기
            for row in reader:
                if row and row[0] == review_id:
                    return True
        return False

    def save_review(self, review_data):
        """분석된 리뷰를 CSV 파일에 한 줄 추가합니다."""
        with open(self.filepath, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                review_data['id'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                review_data.get('category', ''),
                review_data.get('sentiment', ''),
                review_data.get('urgency', ''),
                review_data.get('summary', ''),
                review_data.get('raw_text', '')
            ])