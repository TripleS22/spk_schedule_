import pandas as pd
from datetime import datetime
from data_models import OperationalParameters
from optimization_engine import OptimizationEngine

def simple_test():
    # Create a simple scenario
    units_data = [
        {"unit_id": "U001", "name": "Test Unit", "capacity": 50, "fuel_efficiency": 4.0,
         "operational_cost_per_km": 2500, "status": "Available", "home_location": "Terminal A", "last_location": "Terminal A",
         "allowed_routes": '["R001", "R002"]'},
    ]
    units_df = pd.DataFrame(units_data)

    routes_data = [
        {"route_id": "R001", "name": "Terminal A - Bandara", "origin": "Terminal A", "destination": "Bandara",
         "distance_km": 25.5, "estimated_time_minutes": 45, "route_type": "Express", "required_capacity": 40},
    ]
    routes_df = pd.DataFrame(routes_data)

    schedules_data = [
        {"schedule_id": "S001", "route_id": "R001", "departure_time": "07:00",
         "operating_days": '["Mon", "Tue", "Wed", "Thu", "Fri"]', "priority": 1},
    ]
    schedules_df = pd.DataFrame(schedules_data)

    params = OperationalParameters(
        turnaround_time_minutes=30,
        minimum_rest_time_minutes=15,
        fuel_price_per_liter=12500.0,
        max_working_hours_per_day=12,
        travel_times={
            ("Terminal A", "Terminal B"): 90,
            ("Terminal B", "Terminal A"): 90,
        }
    )
    
    engine = OptimizationEngine(params)
    test_date = datetime(2023, 5, 15)  # Monday

    print("Units DataFrame:")
    print(units_df)
    print(f"Columns: {list(units_df.columns)}")
    print(f"last_location value: {units_df.iloc[0]['last_location']}")
    
    # Test just getting the last location
    unit_id = units_df.iloc[0]['unit_id']
    assignments = []  # empty for now
    last_location = engine.get_unit_last_location(unit_id, assignments, units_df, routes_df)
    print(f"get_unit_last_location result: {last_location}")
    
    # Run a simple optimization
    assignments, unassigned = engine.optimize_assignments(units_df, routes_df, schedules_df, test_date)
    print(f"Result: {len(assignments)} assignments, {len(unassigned)} unassigned")

if __name__ == "__main__":
    simple_test()