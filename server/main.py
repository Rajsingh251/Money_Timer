from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy import Column, Integer, String, Float, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://51.20.130.223:8000", "http://127.0.0.1:5501","https://rajsingh251.github.io"],  # Update with your frontend's address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection setup
DATABASE_URL = "postgresql://timer_owner:xtbkDfgZP38w@ep-polished-star-a1xmqcp1.ap-southeast-1.aws.neon.tech/timer?sslmode=require"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Database connected successfully.")
except Exception as e:
    print(f"Database connection failed: {e}")

Base = declarative_base()

class Timer(Base):
    __tablename__ = "timers"
    id = Column(Integer, primary_key=True, index=True)
    dateid = Column(Date, unique=True, index=True)
    status = Column(String, index=True)
    points = Column(Float)

Base.metadata.create_all(bind=engine)
print("Database tables created.")

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Global variables to manage timer state
REDUCE_AMOUNT_PER_SECOND = 2.7  # Points deducted every second
TOTAL_DURATION_SECONDS = 8 * 60 * 60  # 8 hours in seconds

start_time: Optional[datetime] = None
remaining_points: float = 0
timer_running: bool = False
elapsed_seconds: int = 0

class TimerStatus(BaseModel):
    points: float
    initial_remaining_seconds: int
    timer_running: bool
    elapsed_seconds: int

class Points(BaseModel):
    points: float

@app.post("/start_timer")
async def start_timer(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    global start_time, timer_running, remaining_points
    if not timer_running:
        start_time = datetime.now()
        timer_running = True

        try:
            # Check if there's an existing entry for today's date
            today = date.today()
            timer_entry = db.query(Timer).filter(Timer.dateid == today).first()
            if timer_entry:
                timer_entry.status = "started"
                timer_entry.points = remaining_points
                print(f"Updated timer entry for {today}: status='started', points={remaining_points}")
            else:
                new_timer = Timer(dateid=today, status="started", points=remaining_points)
                db.add(new_timer)
                print(f"Created new timer entry for {today}: status='started', points={remaining_points}")
            db.commit()
            print("Database commit successful.")
        except Exception as e:
            db.rollback()
            print(f"Database operation failed: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

        background_tasks.add_task(update_points_periodically)
        return {"message": "Timer started"}
    else:
        print("Attempt to start the timer failed: Timer is already running.")
        raise HTTPException(status_code=400, detail="Timer is already running")

@app.post("/stop_timer")
async def stop_timer(db: Session = Depends(get_db)):
    global timer_running, start_time, remaining_points, elapsed_seconds
    if timer_running:
        points_data = calculate_points()
        print(points_data)
        
        try:
            # Update today's timer entry
            today = date.today()
            timer_entry = db.query(Timer).filter(Timer.dateid == today).first()
            if timer_entry:
                timer_entry.status = "stopped"
                timer_entry.points = points_data["points"]
                print(f"Updated timer entry for {today}: status='stopped', points={points_data['points']}")
            else:
                new_timer = Timer(dateid=today, status="stopped", points=points_data["points"])
                db.add(new_timer)
                print(f"Created new timer entry for {today}: status='stopped', points={points_data['points']}")
            db.commit()
            print("Database commit successful.")
        except Exception as e:
            db.rollback()
            print(f"Database operation failed: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

        timer_running = False
        print("Timer stopped.")
        return {"message": "Timer stopped"}
    else:
        print("Attempt to stop the timer failed: Timer is not running.")
        raise HTTPException(status_code=400, detail="Timer is not running")

@app.post("/reset_timer")
async def reset_timer(db: Session = Depends(get_db)):
    global start_time, remaining_points, timer_running, elapsed_seconds
    start_time = None
    remaining_points = 0
    timer_running = False
    elapsed_seconds = 0
    print("Timer reset.")
    
    try:
        # Update today's timer entry with reset status and points
        today = date.today()
        timer_entry = db.query(Timer).filter(Timer.dateid == today).first()
        if timer_entry:
            timer_entry.status = "reset"
            timer_entry.points = 0
            print(f"Updated timer entry for {today}: status='reset', points=0")
        else:
            new_timer = Timer(dateid=today, status="reset", points=0)
            db.add(new_timer)
            print(f"Created new timer entry for {today}: status='reset', points=0")
        db.commit()
        print("Database commit successful.")
    except Exception as e:
        db.rollback()
        print(f"Database operation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"message": "Timer reset"}

@app.post("/add_points")
async def add_points(points: Points, db: Session = Depends(get_db)):
    global remaining_points
    remaining_points += points.points
    print(f"Added {points.points} points. Total remaining points: {remaining_points}")

    try:
        # Update today's timer entry with added points
        today = date.today()
        timer_entry = db.query(Timer).filter(Timer.dateid == today).first()
        if timer_entry:
            timer_entry.points = remaining_points
            print(f"Updated timer entry for {today}: points={remaining_points}")
        else:
            new_timer = Timer(dateid=today, status="not_started", points=remaining_points)
            db.add(new_timer)
            print(f"Created new timer entry for {today}: points={remaining_points}")
        db.commit()
        print("Database commit successful.")
    except Exception as e:
        db.rollback()
        print(f"Database operation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"message": f"{points.points} points added", "remaining_points": remaining_points}

def calculate_points():
    global remaining_points, start_time, elapsed_seconds, timer_running
    if start_time and timer_running:
        elapsed_seconds = (datetime.now() - start_time).seconds
        remaining_points -= elapsed_seconds * REDUCE_AMOUNT_PER_SECOND
    return {
        "points": remaining_points,
        "initial_remaining_seconds": TOTAL_DURATION_SECONDS,
        "timer_running": timer_running,
        "elapsed_seconds": elapsed_seconds
    }

async def update_points_periodically():
    while timer_running:
        await asyncio.sleep(30)  # Wait for 30 seconds
        try:
            # Update points in the database
            with SessionLocal() as db:
                points_data = calculate_points()
                today = date.today()
                timer_entry = db.query(Timer).filter(Timer.dateid == today).first()
                if timer_entry:
                    timer_entry.points = points_data["points"]
                    db.commit()
                    print(f"Updated timer entry for {today} every 30 seconds: points={points_data['points']}")
        except Exception as e:
            print(f"Periodic update failed: {e}")

@app.get("/points_info")
async def points_info():
    points_data = calculate_points()
    print(f"Points info requested: {points_data['points']} points remaining, timer running: {points_data['timer_running']}, elapsed seconds: {points_data['elapsed_seconds']}")
    return points_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_certfile="/etc/ssl/fastapi/cert.pem",  # Path to your SSL certificate
        ssl_keyfile="/etc/ssl/fastapi/key.pem",    # Path to your SSL key
        log_level="warning",
        reload=True
    )
