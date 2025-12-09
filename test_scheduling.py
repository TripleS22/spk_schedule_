import pandas as pd
from datetime import datetime
from data_models import get_sample_units, get_sample_routes, get_sample_schedules, OperationalParameters
from optimization_engine import OptimizationEngine

def test_location_based_scheduling():
    print("Testing Location-Based Scheduling Algorithm")
    print("=" * 50)
    
    # Load sample data
    units_df = get_sample_units()
    routes_df = get_sample_routes()
    schedules_df = get_sample_schedules()
    
    # Create operational parameters with more specific travel times
    params = OperationalParameters(
        turnaround_time_minutes=30,
        minimum_rest_time_minutes=15,  # Reduced for testing
        fuel_price_per_liter=12500.0,
        max_working_hours_per_day=12,
        travel_times={
            ("Terminal A", "Bandara"): 45,
            ("Bandara", "Terminal A"): 45,
            ("Terminal A", "Pusat Kota"): 20,
            ("Pusat Kota", "Terminal A"): 20,
            ("Terminal B", "Terminal C"): 60,
            ("Terminal C", "Terminal B"): 60,
            ("Terminal B", "Kawasan Industri"): 30,
            ("Kawasan Industri", "Terminal B"): 30,
            ("Terminal C", "Area Wisata"): 90,
            ("Area Wisata", "Terminal C"): 90,
            ("Depok", "Baltos"): 90,  # From original params
            ("Baltos", "Depok"): 90   # From original params
        }
    )
    
    # Initialize the optimization engine
    engine = OptimizationEngine(params)
    
    # Use a test date
    test_date = datetime(2023, 5, 15)  # A Monday
    
    print(f"Units DataFrame shape: {units_df.shape}")
    print(f"Routes DataFrame shape: {routes_df.shape}")
    print(f"Schedules DataFrame shape: {schedules_df.shape}")
    print()
    
    # Run the optimization
    assignments, unassigned = engine.optimize_assignments(units_df, routes_df, schedules_df, test_date)
    
    print(f"Total assignments made: {len(assignments)}")
    print(f"Total unassigned schedules: {len(unassigned)}")
    print()
    
    # Display assignments
    print("ASSIGNMENTS:")
    print("-" * 80)
    for i, assignment in enumerate(assignments[:10], 1):  # Show first 10
        print(f"{i:2d}. Schedule: {assignment.schedule_id:6s} | Unit: {assignment.unit_id:6s} | "
              f"Departure: {assignment.departure_time:8s} | Return: {assignment.estimated_return_time:8s} | "
              f"Score: {assignment.total_score:.3f}")
    
    print()
    if unassigned:
        print("UNASSIGNED SCHEDULES:")
        print("-" * 50)
        for i, unassign in enumerate(unassigned[:5], 1):  # Show first 5
            print(f"{i:2d}. Schedule: {unassign['schedule_id']} | Departure: {unassign['departure_time']} | "
                  f"Reasons: {', '.join(unassign['reasons'][:2])}")
    else:
        print("All schedules have been assigned!")
    
    print("\n" + "=" * 50)
    
    # Test metrics
    metrics = engine.calculate_metrics(assignments, units_df, routes_df, schedules_df, test_date)
    print("OPTIMIZATION METRICS:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key:20s}: {value:.2f}")
        else:
            print(f"{key:20s}: {value}")
    
    print("\n" + "=" * 50)
    
    # Test the location tracking by simulating a scenario
    print("TESTING LOCATION-BASED LOGIC:")
    
    # Let's focus on a few specific units and routes to see location-based assignment in action
    # Select routes from 'Terminal A' and 'Terminal B' to see if units prefer staying local
    terminal_a_routes = routes_df[routes_df['origin'] == 'Terminal A']
    terminal_b_routes = routes_df[routes_df['origin'] == 'Terminal B']
    
    print(f"Routes from Terminal A: {len(terminal_a_routes)}")
    print(f"Routes from Terminal B: {len(terminal_b_routes)}")
    
    # Get assignments for Terminal A origin routes
    terminal_a_assignments = [a for a in assignments if a.route_id in terminal_a_routes['route_id'].values]
    terminal_b_assignments = [a for a in assignments if a.route_id in terminal_b_routes['route_id'].values]
    
    print(f"\nAssignments for Terminal A routes: {len(terminal_a_assignments)}")
    for a in terminal_a_assignments[:5]:
        unit_row = units_df[units_df['unit_id'] == a.unit_id].iloc[0]
        print(f"  Unit {a.unit_id} (home: {unit_row['home_location']}) assigned to {a.route_id}")
    
    print(f"\nAssignments for Terminal B routes: {len(terminal_b_assignments)}")
    for a in terminal_b_assignments[:5]:
        unit_row = units_df[units_df['unit_id'] == a.unit_id].iloc[0]
        print(f"  Unit {a.unit_id} (home: {unit_row['home_location']}) assigned to {a.route_id}")

if __name__ == "__main__":
    test_location_based_scheduling()