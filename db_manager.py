import pymysql
import chromadb
from contextlib import AbstractContextManager

# ==========================================
# 0. 기본 세팅 (비밀번호 꼭 수정!)
# ==========================================
DB_PASSWORD = ''

def get_mysql_conn():
    return pymysql.connect(
        host='localhost', 
        user='root', 
        password=DB_PASSWORD, 
        charset='utf8mb4',
        database='welfare_db'
    )

chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(name="welfare_policies")


class PolicyTransaction(AbstractContextManager):
    """
    (추가 이유 : 기존의 DB에 바로 연결하던 부분을 테스트를 위한 롤백 기능 구현)
    정책 여러 건을 하나의 MySQL 트랜잭션으로 처리한다.
    """

    def __init__(self):
        self.conn = get_mysql_conn()
        self.pending_vectors = []

    def __enter__(self):
        return self

    def get_existing_policy_ids(self, policy_ids):
        policy_ids = [str(policy_id) for policy_id in policy_ids if policy_id]
        if not policy_ids:
            return set()

        cursor = self.conn.cursor()
        existing_ids = set()
        for start in range(0, len(policy_ids), 500):
            chunk = policy_ids[start:start + 500]
            placeholders = ", ".join(["%s"] * len(chunk))
            cursor.execute(
                f"SELECT policy_id FROM policies WHERE policy_id IN ({placeholders})",
                chunk,
            )
            existing_ids.update(str(row[0]) for row in cursor.fetchall())
        return existing_ids

    def insert_policy(self, policy_id, title, category, content):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO policies
                (policy_id, title, category, original_content)
            VALUES (%s, %s, %s, %s)
            """,
            (policy_id, title, category, content),
        )
        inserted = cursor.rowcount == 1
        if inserted:
            self.pending_vectors.append(
                {
                    "document": content or title,
                    "metadata": {"title": title, "category": category},
                    "id": str(policy_id),
                }
            )
        return inserted

    def commit(self):
        self.conn.commit()
        for vector in self.pending_vectors:
            collection.upsert(
                documents=[vector["document"]],
                metadatas=[vector["metadata"]],
                ids=[vector["id"]],
            )
        self.pending_vectors.clear()

    def rollback(self):
        self.conn.rollback()
        self.pending_vectors.clear()

    def close(self):
        self.conn.close()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.rollback()
        self.close()
        return False


def policy_transaction():
    return PolicyTransaction()



def get_existing_policy_ids(policy_ids):
    """
    (추가 이유 : 데이터 크롤링시 불필요한 API호출을 피하기 위해 미리 존재하는 혜택 검사)
    이미 저장된 정책 ID를 한 번의 조회로 확인한다.
    """
    policy_ids = [str(policy_id) for policy_id in policy_ids if policy_id]
    if not policy_ids:
        return set()

    conn = get_mysql_conn()
    try:
        cursor = conn.cursor()
        existing_ids = set()
        for start in range(0, len(policy_ids), 500):
            chunk = policy_ids[start:start + 500]
            placeholders = ", ".join(["%s"] * len(chunk))
            cursor.execute(
                f"SELECT policy_id FROM policies WHERE policy_id IN ({placeholders})",
                chunk,
            )
            existing_ids.update(str(row[0]) for row in cursor.fetchall())
        return existing_ids
    finally:
        conn.close()

# ==========================================
# 1. 데이터 넣기 함수 (크롤링 담당 팀원이 쓸 기능)
# ==========================================
"""
수정 이유 : 테스트를 위한 트랜잭션 롤백 기능구현
"""
def insert_policy(policy_id, title, category, content):
    with policy_transaction() as transaction:
        inserted = transaction.insert_policy(policy_id, title, category, content)
        transaction.commit()
        return inserted

# ==========================================
# 2. 데이터 찾기 함수 (AI/백엔드 담당 팀원이 쓸 기능)
# ==========================================
def search_recommended_policy(user_query):
    results = collection.query(
        query_texts=[user_query],
        n_results=2 
    )
    return results

# ==========================================
# 3. 데이터 하드 필터링 함수 (영준님 요청 기능)
# ==========================================
def get_filtered_policies(user_profile):
    conn = get_mysql_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    income = user_profile.get("user_income", 10)
    region = user_profile.get("user_region", "")
    
    sql = """
        SELECT * FROM policies 
        WHERE target_income >= %s 
        AND (target_region = %s OR target_region = '전국')
    """
    
    cursor.execute(sql, (income, region))
    filtered_results = cursor.fetchall()
    
    conn.close()
    return filtered_results