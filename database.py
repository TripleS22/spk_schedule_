import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./logistics.db")

# Enable foreign key constraints for SQLite
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    engine = create_engine(DATABASE_URL)
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Unit(Base):
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    fuel_efficiency = Column(Float, nullable=False)
    operational_cost_per_km = Column(Float, nullable=False)
    status = Column(String(50), default="Available")
    home_location = Column(String(100))
    allowed_routes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = relationship("Assignment", back_populates="unit")

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    distance_km = Column(Float, nullable=False)
    estimated_time_minutes = Column(Integer, nullable=False)
    route_type = Column(String(50))
    required_capacity = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    schedules = relationship("Schedule", back_populates="route")

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(String(50), unique=True, index=True, nullable=False)
    route_id = Column(String(50), ForeignKey("routes.route_id"), nullable=False)
    departure_time = Column(String(10), nullable=False)
    operating_days = Column(Text)
    priority = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    route = relationship("Route", back_populates="schedules")
    assignments = relationship("Assignment", back_populates="schedule")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    assignment_date = Column(DateTime, nullable=False)
    schedule_id = Column(String(50), ForeignKey("schedules.schedule_id"), nullable=False)
    route_id = Column(String(50), nullable=False)
    unit_id = Column(String(50), ForeignKey("units.unit_id"), nullable=False)
    departure_time = Column(String(10), nullable=False)
    estimated_return_time = Column(String(10), nullable=False)
    total_score = Column(Float)
    fuel_cost = Column(Float)
    assignment_reason = Column(Text)
    status = Column(String(50), default="Assigned")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    unit = relationship("Unit", back_populates="assignments")
    schedule = relationship("Schedule", back_populates="assignments")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50))
    old_values = Column(Text)
    new_values = Column(Text)
    user_id = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text)

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime, nullable=False)
    target_date = Column(DateTime, nullable=False)
    total_schedules = Column(Integer)
    assigned_count = Column(Integer)
    coverage_rate = Column(Float)
    utilization_rate = Column(Float)
    total_fuel_cost = Column(Float)
    total_distance = Column(Float)
    average_score = Column(Float)
    parameters = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(50))
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parameters = Column(Text)
    results = Column(Text)
    is_baseline = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200))
    role = Column(String(50), default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50))
    requested_changes = Column(Text)
    requested_by = Column(String(100))
    status = Column(String(50), default="pending")
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Storage(Base):
    __tablename__ = "storage"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    data_type = Column(String(50), default="text")
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    capacity = Column(Integer)
    type = Column(String(50), default="terminal")
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemState(Base):
    __tablename__ = "system_state"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    return SessionLocal()

def log_audit(db, action: str, entity_type: str, entity_id: str = None, 
              old_values: dict = None, new_values: dict = None, 
              user_id: str = None, details: str = None):
    audit_log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        user_id=user_id,
        details=details
    )
    db.add(audit_log)
    db.commit()
    return audit_log

def create_alert(db, alert_type: str, severity: str, message: str, 
                 entity_type: str = None, entity_id: str = None):
    alert = Alert(
        alert_type=alert_type,
        severity=severity,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id
    )
    db.add(alert)
    db.commit()
    return alert
