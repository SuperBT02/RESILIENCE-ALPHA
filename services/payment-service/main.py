import os
import psycopg2
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Resilience-Alpha Payment API", version="1.0.0")

# Initialize Prometheus Metrics Instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Database connection parameters from environment variables
DB_HOST = os.getenv("DB_HOST", "resilience_db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "resilience_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "super_secure_password_change_me")
DB_NAME = os.getenv("DB_NAME", "payment_si")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

class PaymentRequest(BaseModel):
    sender_id: str
    receiver_id: str
    amount: float

@app.get("/health")
def health_check():
    conn = get_db_connection()
    conn.close()
    return {"status": "healthy", "database": "connected"}

@app.post("/api/pay", status_code=status.HTTP_201_CREATED)
def process_payment(payment: PaymentRequest):
    """Custom payment processing endpoint for Resilience-Alpha"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO transactions (sender_id, receiver_id, amount, status)
            VALUES (%s, %s, %s, 'SUCCESS')
            RETURNING id, created_at, status;
            """,
            (payment.sender_id, payment.receiver_id, payment.amount)
        )
        new_transaction = cursor.fetchone()
        conn.commit()
        
        return {
            "transaction_id": new_transaction[0],
            "status": new_transaction[2],
            "timestamp": new_transaction[1],
            "message": "Payment processed successfully"
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()