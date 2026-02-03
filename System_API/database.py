import psycopg2
from psycopg.rows import dict_rowimport os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Create a database connection"""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn

def init_db():
    """Initialize the database table"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create table with mac_address, username, and json_data columns
    cur.execute('''
        CREATE TABLE IF NOT EXISTS device_data (
            id SERIAL PRIMARY KEY,
            mac_address VARCHAR(17) UNIQUE NOT NULL,
            username VARCHAR(255),
            json_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database table created successfully!")

if __name__ == '__main__':
    init_db()

