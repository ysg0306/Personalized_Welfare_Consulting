import pymysql
import chromadb

# ==========================================
# 0. 기본 세팅 (비밀번호 꼭 수정!)
# ==========================================
DB_PASSWORD = '0000'

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

# ==========================================
# 1. 데이터 넣기 함수 (크롤링 담당 팀원이 쓸 기능)
# ==========================================
def insert_policy(policy_id, title, category, content):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    
    sql = """
        INSERT IGNORE INTO policies (policy_id, title, category, original_content) 
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (policy_id, title, category, content))
    conn.commit()
    conn.close()
    
    collection.add(
        documents=[content],
        metadatas=[{"title": title, "category": category}],
        ids=[policy_id]
    )

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