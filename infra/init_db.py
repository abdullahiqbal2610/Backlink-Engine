import os
import psycopg2
from dotenv import load_dotenv

def init_db():
    load_dotenv('../.env')
    
    print("[*] Connecting to Neon Postgres...")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        sql_file_path = os.path.join(os.path.dirname(__file__), 'init.sql')
        with open(sql_file_path, 'r') as f:
            sql = f.read()
            
        print("[*] Running init.sql to create tables...")
        cursor.execute(sql)
        print("[+] Database initialized successfully on Neon!")
        
    except Exception as e:
        print(f"[-] Failed to initialize database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_db()
