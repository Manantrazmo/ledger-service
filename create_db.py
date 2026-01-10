import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    try:
        # Connect to default 'postgres' database
        conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='123456789',
            host='localhost'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'tigerBettleClient'")
        exists = cur.fetchone()
        
        if not exists:
            print("Creating database 'tigerBettleClient'...")
            cur.execute('CREATE DATABASE "tigerBettleClient"')
            print("Database created successfully.")
        else:
            print("Database 'tigerBettleClient' already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_database()
