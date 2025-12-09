import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class Unit:
    unit_id: str
    name: str
    capacity: int
    fuel_efficiency: float
    operational_cost_per_km: float
    status: str
    home_location: str
    last_location: str = field(default_factory=str)  # Added to track last location
    allowed_routes: List[str] = field(default_factory=list)
    
@dataclass
class Route:
    route_id: str
    name: str
    origin: str
    destination: str
    distance_km: float
    estimated_time_minutes: int
    route_type: str
    required_capacity: int

@dataclass
class Schedule:
    schedule_id: str
    route_id: str
    departure_time: str
    operating_days: List[str]
    priority: int

@dataclass
class OperationalParameters:
    turnaround_time_minutes: int = 30
    minimum_rest_time_minutes: int = 60
    fuel_price_per_liter: float = 12500.0
    max_working_hours_per_day: int = 12
    travel_times: Dict[Tuple[str, str], int] = field(default_factory=lambda: {
        ("Depok", "Baltos"): 60,
        ("Baltos", "Depok"): 60
    })
    
def get_sample_units() -> pd.DataFrame:
    units_data = [
        {"unit_id": "U001", "name": "Bus Alpha-01", "capacity": 45, "fuel_efficiency": 4.5,
         "operational_cost_per_km": 2500, "status": "Available", "home_location": "Terminal A",
         "last_location": "Terminal A", "allowed_routes": ["R001", "R002", "R003"]},
        {"unit_id": "U002", "name": "Bus Alpha-02", "capacity": 45, "fuel_efficiency": 4.2,
         "operational_cost_per_km": 2600, "status": "Available", "home_location": "Terminal A",
         "last_location": "Terminal A", "allowed_routes": ["R001", "R002", "R004"]},
        {"unit_id": "U003", "name": "Bus Beta-01", "capacity": 55, "fuel_efficiency": 3.8,
         "operational_cost_per_km": 3000, "status": "Available", "home_location": "Terminal B",
         "last_location": "Terminal B", "allowed_routes": ["R002", "R003", "R004", "R005"]},
        {"unit_id": "U004", "name": "Bus Beta-02", "capacity": 55, "fuel_efficiency": 3.9,
         "operational_cost_per_km": 2900, "status": "Available", "home_location": "Terminal B",
         "last_location": "Terminal B", "allowed_routes": ["R001", "R003", "R005"]},
        {"unit_id": "U005", "name": "Bus Gamma-01", "capacity": 35, "fuel_efficiency": 5.2,
         "operational_cost_per_km": 2200, "status": "Available", "home_location": "Terminal C",
         "last_location": "Terminal C", "allowed_routes": ["R003", "R004", "R005"]},
        {"unit_id": "U006", "name": "Bus Gamma-02", "capacity": 35, "fuel_efficiency": 5.0,
         "operational_cost_per_km": 2300, "status": "Maintenance", "home_location": "Terminal C",
         "last_location": "Terminal C", "allowed_routes": ["R001", "R002", "R005"]},
        {"unit_id": "U007", "name": "Bus Delta-01", "capacity": 50, "fuel_efficiency": 4.0,
         "operational_cost_per_km": 2700, "status": "Available", "home_location": "Terminal A",
         "last_location": "Terminal A", "allowed_routes": ["R001", "R002", "R003", "R004"]},
        {"unit_id": "U008", "name": "Bus Delta-02", "capacity": 50, "fuel_efficiency": 4.1,
         "operational_cost_per_km": 2650, "status": "Available", "home_location": "Terminal B",
         "last_location": "Terminal B", "allowed_routes": ["R002", "R003", "R004", "R005"]},
    ]
    df = pd.DataFrame(units_data)
    df['allowed_routes'] = df['allowed_routes'].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    return df

def get_sample_routes() -> pd.DataFrame:
    routes_data = [
        {"route_id": "R001", "name": "Terminal A - Bandara", "origin": "Terminal A", 
         "destination": "Bandara", "distance_km": 25.5, "estimated_time_minutes": 45,
         "route_type": "Express", "required_capacity": 40},
        {"route_id": "R002", "name": "Terminal A - Pusat Kota", "origin": "Terminal A", 
         "destination": "Pusat Kota", "distance_km": 15.0, "estimated_time_minutes": 35,
         "route_type": "Regular", "required_capacity": 30},
        {"route_id": "R003", "name": "Terminal B - Terminal C", "origin": "Terminal B", 
         "destination": "Terminal C", "distance_km": 30.0, "estimated_time_minutes": 50,
         "route_type": "Inter-Terminal", "required_capacity": 45},
        {"route_id": "R004", "name": "Terminal B - Industri", "origin": "Terminal B", 
         "destination": "Kawasan Industri", "distance_km": 20.0, "estimated_time_minutes": 40,
         "route_type": "Regular", "required_capacity": 50},
        {"route_id": "R005", "name": "Terminal C - Wisata", "origin": "Terminal C", 
         "destination": "Area Wisata", "distance_km": 35.0, "estimated_time_minutes": 60,
         "route_type": "Tourism", "required_capacity": 35},
    ]
    return pd.DataFrame(routes_data)

def get_sample_schedules() -> pd.DataFrame:
    schedules_data = [
        {"schedule_id": "S001", "route_id": "R001", "departure_time": "06:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S002", "route_id": "R001", "departure_time": "08:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S003", "route_id": "R001", "departure_time": "10:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]), "priority": 2},
        {"schedule_id": "S004", "route_id": "R002", "departure_time": "06:30", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S005", "route_id": "R002", "departure_time": "09:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]), "priority": 2},
        {"schedule_id": "S006", "route_id": "R002", "departure_time": "12:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]), "priority": 2},
        {"schedule_id": "S007", "route_id": "R003", "departure_time": "07:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S008", "route_id": "R003", "departure_time": "14:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]), "priority": 2},
        {"schedule_id": "S009", "route_id": "R004", "departure_time": "05:30", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S010", "route_id": "R004", "departure_time": "07:30", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S011", "route_id": "R004", "departure_time": "17:00", 
         "operating_days": json.dumps(["Mon", "Tue", "Wed", "Thu", "Fri"]), "priority": 1},
        {"schedule_id": "S012", "route_id": "R005", "departure_time": "08:00", 
         "operating_days": json.dumps(["Sat", "Sun"]), "priority": 2},
        {"schedule_id": "S013", "route_id": "R005", "departure_time": "10:00", 
         "operating_days": json.dumps(["Sat", "Sun"]), "priority": 2},
        {"schedule_id": "S014", "route_id": "R005", "departure_time": "14:00", 
         "operating_days": json.dumps(["Sat", "Sun"]), "priority": 3},
    ]
    return pd.DataFrame(schedules_data)

def parse_allowed_routes(routes_str):
    if isinstance(routes_str, list):
        return routes_str
    try:
        return json.loads(routes_str)
    except:
        return []

def parse_operating_days(days_str):
    if isinstance(days_str, list):
        return days_str
    try:
        return json.loads(days_str)
    except:
        return []

def get_day_name(date_obj: datetime) -> str:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return days[date_obj.weekday()]

def time_str_to_minutes(time_str: str) -> int:
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])

def minutes_to_time_str(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"
