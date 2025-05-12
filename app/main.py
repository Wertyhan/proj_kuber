from fastapi import FastAPI, HTTPException
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import time
import logging


LOG_PATH = "/logs/app.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(level=logging.INFO, filename=LOG_PATH, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

DB_USER = os.getenv('POSTGRES_DB_USER')
DB_PASSWORD = os.getenv('POSTGRES_DB_PASSWORD')
DB_HOST = 'db'
DB_PORT = 5432
DB_NAME = 'database'
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class User(BaseModel):
    name: str
    email: str


def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            logging.info("Database initialized successfully")
            return
        except Exception as e:
            retries -= 1
            logging.warning(f"DB init failed: {e}. Retries left: {retries}")
            if retries == 0:
                logging.error("DB init failed after max retries")
                raise
            time.sleep(2)

try:
    init_db()
except Exception as e:
    logging.exception("Unhandled exception during DB init")

@app.get("/")
def read_root():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        logging.info("Health check passed")
        return {"status": "Database connection successful", "result": result}
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {"status": "Database connection failed", "error": str(e)}

@app.post("/users/")
def create_user(user: User):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id;",
            (user.name, user.email)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"User created: {user.email}")
        return {"id": user_id, "name": user.name, "email": user.email}
    except Exception as e:
        logging.error(f"Failed to create user {user.email}: {e}")
        raise HTTPException(status_code=400, detail="Failed to create user")

@app.get("/users/")
def get_users():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users;")
        users = cur.fetchall()
        cur.close()
        conn.close()
        logging.info("Fetched all users")
        return {"users": users}
    except Exception as e:
        logging.error(f"Failed to fetch users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@app.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user is None:
            logging.warning(f"User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")
        logging.info(f"Fetched user {user_id}")
        return user
    except Exception as e:
        logging.error(f"Failed to fetch user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user")

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id;", (user_id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id is None:
            logging.warning(f"User {user_id} not found for deletion")
            raise HTTPException(status_code=404, detail="User not found")
        logging.info(f"Deleted user {user_id}")
        return {"message": f"User {user_id} deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")
