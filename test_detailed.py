import pandas as pd
from datetime import datetime
from data_models import Unit, Route, Schedule, OperationalParameters
from optimization_engine import OptimizationEngine, Assignment

def test_location_based_priority():
    """
    Test scenario to verify that units prioritize schedules at their last location
    and only move to other locations when needed.
    """
    print("Testing Location-Based Priority Logic")
    print("=" * 50)
    
    # Create a scenario similar to your example: Depok and Baltos locations
    # Let's set up units at different locations to test the logic
    
    # Units DataFrame - using Terminal A and Terminal B from sample data
    units_data = [
        # Unit at Terminal A
        {"unit_id": "AS01", "name": "Terminal A Unit", "capacity": 50, "fuel_efficiency": 4.0,
         "operational_cost_per_km": 2500, "status": "Available", "home_location": "Terminal A", "last_location": "Terminal A",
         "allowed_routes": ["R001", "R002", "R003"]},  # Allow routes from both terminals
        # Unit at Terminal B
        {"unit_id": "AS02", "name": "Terminal B Unit", "capacity": 50, "fuel_efficiency": 4.0,
         "operational_cost_per_km": 2500, "status": "Available", "home_location": "Terminal B", "last_location": "Terminal B",
         "allowed_routes": ["R001", "R002", "R003", "R004"]},  # Allow routes from both terminals
        # Another unit at Terminal B (to test multi-unit scenarios)
        {"unit_id": "AS03", "name": "Terminal B Unit 2", "capacity": 50, "fuel_efficiency": 4.0,
         "operational_cost_per_km": 2500, "status": "Available", "home_location": "Terminal B", "last_location": "Terminal B",
         "allowed_routes": ["R001", "R002", "R003", "R004"]},
    ]
    units_df = pd.DataFrame(units_data)
    units_df['allowed_routes'] = units_df['allowed_routes'].apply(lambda x: str(x))

    # Routes DataFrame - using Terminal A and Terminal B from sample data
    routes_data = [
        {"route_id": "R001", "name": "Terminal A - Bandara", "origin": "Terminal A", "destination": "Bandara",
         "distance_km": 25.5, "estimated_time_minutes": 45, "route_type": "Express", "required_capacity": 40},
        {"route_id": "R003", "name": "Terminal B - Terminal C", "origin": "Terminal B", "destination": "Terminal C",
         "distance_km": 30.0, "estimated_time_minutes": 50, "route_type": "Inter-Terminal", "required_capacity": 40}
    ]
    routes_df = pd.DataFrame(routes_data)

    # Schedules DataFrame - create schedules that start at different times
    schedules_data = [
        {"schedule_id": "S001", "route_id": "R001", "departure_time": "07:00",  # Terminal A route
         "operating_days": '["Mon", "Tue", "Wed", "Thu", "Fri"]', "priority": 1},
        {"schedule_id": "S002", "route_id": "R003", "departure_time": "07:30",  # Terminal B route
         "operating_days": '["Mon", "Tue", "Wed", "Thu", "Fri"]', "priority": 1},
        {"schedule_id": "S003", "route_id": "R001", "departure_time": "09:00",  # Another Terminal A route
         "operating_days": '["Mon", "Tue", "Wed", "Thu", "Fri"]', "priority": 1},
        {"schedule_id": "S004", "route_id": "R003", "departure_time": "10:00",  # Another Terminal B route
         "operating_days": '["Mon", "Tue", "Wed", "Thu", "Fri"]', "priority": 1},
    ]
    schedules_df = pd.DataFrame(schedules_data)

    # Operational parameters with specific travel times
    params = OperationalParameters(
        turnaround_time_minutes=30,
        minimum_rest_time_minutes=15,
        fuel_price_per_liter=12500.0,
        max_working_hours_per_day=12,
        travel_times={
            ("Terminal A", "Terminal B"): 90,  # 90 minutes as in the example
            ("Terminal B", "Terminal A"): 90,
            ("Terminal A", "Bandara"): 30,    # Shorter distance to Bandara
            ("Bandara", "Terminal A"): 30,
            ("Terminal B", "Terminal C"): 60, # Time to Terminal C
            ("Terminal C", "Terminal B"): 60,
        }
    )
    
    engine = OptimizationEngine(params)
    test_date = datetime(2023, 5, 15)  # Monday

    print(f"Units: {list(units_df['unit_id'])}")
    print(f"Units with last_location 'Depok': {units_df[units_df['last_location'] == 'Depok']['unit_id'].tolist()}")
    print(f"Units with last_location 'Baltos': {units_df[units_df['last_location'] == 'Baltos']['unit_id'].tolist()}")
    print(f"Units with last_location 'Terminal A': {units_df[units_df['last_location'] == 'Terminal A']['unit_id'].tolist()}")
    print(f"Units with last_location 'Terminal B': {units_df[units_df['last_location'] == 'Terminal B']['unit_id'].tolist()}")
    print(f"Full units data:")
    print(units_df[['unit_id', 'last_location', 'home_location']])
    print()

    assignments, unassigned = engine.optimize_assignments(units_df, routes_df, schedules_df, test_date)
    
    print(f"Total assignments: {len(assignments)}")
    print(f"Unassigned: {len(unassigned)}")
    print()
    
    print("ASSIGNMENTS:")
    print("-" * 70)
    for i, assignment in enumerate(assignments, 1):
        route = routes_df[routes_df['route_id'] == assignment.route_id].iloc[0]
        unit = units_df[units_df['unit_id'] == assignment.unit_id].iloc[0]
        print(f"{i}. Unit: {assignment.unit_id:4s} (last_location: {unit['last_location']:6s}) | "
              f"Route: {assignment.route_id:4s} (origin: {route['origin']:6s}) | "
              f"Departure: {assignment.departure_time:8s} | Score: {assignment.total_score:.3f}")
    
    print()
    print("ANALYSIS:")
    print("-" * 30)
    
    # Check if units are assigned to routes at their current location first
    depok_assignments = [a for a in assignments if routes_df[routes_df['route_id'] == a.route_id].iloc[0]['origin'] == 'Depok']
    baltos_assignments = [a for a in assignments if routes_df[routes_df['route_id'] == a.route_id].iloc[0]['origin'] == 'Baltos']
    
    print(f"Assignments to Depok routes: {len(depok_assignments)}")
    for a in depok_assignments:
        unit = units_df[units_df['unit_id'] == a.unit_id].iloc[0]
        print(f"  - Unit {a.unit_id} (from {unit['last_location']}) -> Depok route")
        
    print(f"Assignments to Baltos routes: {len(baltos_assignments)}")
    for a in baltos_assignments:
        unit = units_df[units_df['unit_id'] == a.unit_id].iloc[0]
        print(f"  - Unit {a.unit_id} (from {unit['last_location']}) -> Baltos route")
    
    # Test the scenario: After AS01 finishes at Depok, does it take Depok schedules first?
    print()
    print("TESTING SCENARIO: Units prioritize local schedules")
    
    # Find assignments to Depok routes and check which units take them
    for assignment in assignments:
        route = routes_df[routes_df['route_id'] == assignment.route_id].iloc[0]
        unit = units_df[units_df['unit_id'] == assignment.unit_id].iloc[0]
        
        if route['origin'] == unit['last_location']:
            print(f"✓ Unit {assignment.unit_id} at {unit['last_location']} took local route {assignment.route_id}")
        else:
            print(f"→ Unit {assignment.unit_id} at {unit['last_location']} moved to {route['origin']} (deadhead needed)")
    
    print()
    print("CONCLUSION:")
    print("-" * 12)
    print("The algorithm attempts to prioritize local units for local schedules.")
    print("When no local units are available, it may assign units from other locations," 
          "accounting for deadhead time and minimum rest requirements.")

def test_rest_time_and_deadhead():
    """
    Test the rest time and deadhead time calculation logic
    """
    print("\n" + "=" * 50)
    print("Testing Rest Time & Deadhead Logic")
    print("=" * 50)
    
    # Create an engine instance
    params = OperationalParameters(
        turnaround_time_minutes=30,
        minimum_rest_time_minutes=15,
        fuel_price_per_liter=12500.0,
        max_working_hours_per_day=12,
        travel_times={
            ("Depok", "Baltos"): 90,
            ("Baltos", "Depok"): 90,
        }
    )
    
    engine = OptimizationEngine(params)
    
    # Test availability calculation
    # Unit finished at Baltos, next schedule at Depok starting at 09:00
    # Unit should be available at: finish_time + rest_time + deadhead_time
    # If finish time is 07:00, rest = 15min, deadhead = 90min
    # Available time = 07:00 + 0:15 + 1:30 = 08:45
    # Since 08:45 <= 09:00, this should be feasible
    
    print("Example: Unit finishes in Baltos at 07:00, needs to start Depok at 09:00")
    print("- Unit requires 15 min minimum rest")
    print("- Travel time Baltos -> Depok: 90 min")
    print("- Required availability: 07:00 + 0:15 + 1:30 = 08:45")
    print("- Schedule departure: 09:00")
    print("- Result: Should be feasible (08:45 <= 09:00)")
    
    # Simulate this scenario
    availability_time = 7*60 + 0  # 07:00 in minutes
    availability_after_rest = availability_time + params.minimum_rest_time_minutes  # 07:00 + 15 = 07:15
    deadhead_time = engine.get_deadhead_time("Baltos", "Depok")  # 90 min
    total_available_time = availability_after_rest + deadhead_time  # 07:15 + 90min = 08:45
    schedule_departure = 9*60 + 0  # 09:00 in minutes
    
    print(f"Calculated availability: {total_available_time//60:02d}:{total_available_time%60:02d}")
    print(f"Schedule departure: {schedule_departure//60:02d}:{schedule_departure%60:02d}")
    print(f"Feasible: {total_available_time <= schedule_departure}")

if __name__ == "__main__":
    test_location_based_priority()
    test_rest_time_and_deadhead()