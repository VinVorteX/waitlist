from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Simple Waitlist API")

# Email Configuration
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def send_confirmation_email(to_email: str, position: int):
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = "Welcome to our Waitlist!"

        # Email body
        body = f"""
        Thank you for joining our waitlist!
        
        You are currently in position #{position}.
        postgresql://neondb_owner:npg_LmTFhIH3pc0j@ep-dark-cloud-a5vhpodv-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
        We'll keep you updated on our progress.
        
        Best regards,
        Your Team
        """
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Models
class WaitlistEntry(Base):
    __tablename__ = "waitlist"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Request/Response models
class WaitlistRequest(BaseModel):
    email: EmailStr

class WaitlistResponse(BaseModel):
    message: str
    position: int
    email_sent: bool

# Helper function
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Endpoints
@app.post("/join", response_model=WaitlistResponse)
def join_waitlist(request: WaitlistRequest):
    db = get_db()
    try:
        # Create new entry
        entry = WaitlistEntry(email=request.email)
        db.add(entry)
        db.commit()
        
        # Get position
        position = db.query(WaitlistEntry).count()
        
        # Send confirmation email
        email_sent = send_confirmation_email(request.email, position)
        
        return WaitlistResponse(
            message="Successfully joined the waitlist!",
            position=position,
            email_sent=email_sent
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="This email is already registered"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )

@app.get("/total")
def get_total_registrations():
    db = get_db()
    total = db.query(WaitlistEntry).count()
    return {"total_registrations": total}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.delete("/delete_email")
def delete_email(email: str):
    db = get_db()
    try:
        db.query(WaitlistEntry).filter(WaitlistEntry.email == email).delete()
        db.commit()
        return {"message": "Email deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )