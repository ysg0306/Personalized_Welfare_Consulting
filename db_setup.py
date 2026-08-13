import pymysql
import chromadb

def setup_mysql():
    conn = pymysql.connect(
        host='localhost', 
        user='root', 
        password='0000', 
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS welfare_db;")
    cursor.execute("USE welfare_db;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_name VARCHAR(50),
        user_age INT,
        user_income INT,
        user_region VARCHAR(50),
        is_student BOOLEAN
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        policy_id VARCHAR(50) PRIMARY KEY,
        title VARCHAR(200),
        category VARCHAR(50),
        target_age_min INT,
        target_age_max INT,
        target_income INT,
        target_region VARCHAR(50),
        target_student BOOLEAN,
        original_content TEXT,
        text_embedding LONGTEXT,
        keyword_embedding LONGTEXT
    );
    """)
    
    conn.commit()
    conn.close()
    print("✅ MySQL 사용자 및 정책 테이블 세팅 완료!")

def setup_chromadb():
    client = chromadb.PersistentClient(path="./chroma_data")
    
    collection = client.get_or_create_collection(name="welfare_policies")
    
    print("✅ ChromaDB 벡터 데이터베이스 세팅 완료!")
    return collection

if __name__ == "__main__":
    print("데이터베이스 초기 세팅을 시작합니다...")
    setup_mysql()
    setup_chromadb()
    print("세팅이 모두 끝났습니다!")