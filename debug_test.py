import pandas as pd
from datetime import datetime
from data_models import parse_allowed_routes, time_str_to_minutes, minutes_to_time_str
from optimization_engine import OptimizationEngine
from data_models import get_sample_units, get_sample_routes, get_sample_schedules, OperationalParameters

def debug_optimization():
    print("Debugging the optimization process")
    print("=" * 40)
    
    # Use simpler data to identify the issue
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
            ("Depok", "Baltos"): 90,
            ("Baltos", "Depok"): 90
        }
    )
    
    engine = OptimizationEngine(params)
    test_date = datetime(2023, 5, 15)  # Monday
    
    # Test with the original simple version first
    print("Testing with simplified debug approach...")
    
    # Let's trace through the process step by step
    avg_costs = {
        'operational': units_df['operational_cost_per_km'].mean() * routes_df['distance_km'].mean() * 2,
        'fuel': (routes_df['distance_km'].mean() * 2 / units_df['fuel_efficiency'].mean()) * params.fuel_price_per_liter
    }
    
    from data_models import get_day_name, parse_operating_days
    
    target_day = get_day_name(test_date)
    print(f"Target day: {target_day}")
    
    # Filter active schedules
    active_schedules = []
    for idx, schedule in schedules_df.iterrows():
        operating_days = parse_operating_days(schedule['operating_days'])
        if target_day in operating_days:
            active_schedules.append(schedule)

    print(f"Active schedules for {target_day}: {len(active_schedules)}")
    
    # Test first schedule
    if active_schedules:
        schedule = active_schedules[0]
        route = routes_df[routes_df['route_id'] == schedule['route_id']].iloc[0]
        
        print(f"Testing schedule: {schedule['schedule_id']} -> route {route['route_id']} (origin: {route['origin']})")
        
        assignments = []  # Simulate empty assignments for first iteration
        
        # Test the location grouping logic
        schedule_origin = route['origin']
        departure_minutes = time_str_to_minutes(schedule['departure_time'])
        
        print(f"Schedule origin: {schedule_origin}, departure: {schedule['departure_time']} ({departure_minutes} mins)")
        
        # Divide units into two groups: those at the same location and others
        units_at_origin = []
        units_elsewhere = []
        
        for _, unit in units_df.iterrows():
            # Check if unit is feasible in basic constraints (this might be causing issues)
            try:
                basic_score = engine.score_unit_for_schedule(
                    unit, route, schedule, test_date, avg_costs, assignments
                )
                
                if basic_score.is_feasible:
                    # Check the unit's last location
                    unit_last_location = engine.get_unit_last_location(unit['unit_id'], assignments, units_df, routes_df)
                    
                    print(f"Unit {unit['unit_id']}: last location = {unit_last_location}, schedule origin = {schedule_origin}")
                    
                    if unit_last_location == schedule_origin:
                        units_at_origin.append(unit)
                        print(f"  -> Added to units_at_origin")
                    else:
                        units_elsewhere.append(unit)
                        print(f"  -> Added to units_elsewhere")
                else:
                    print(f"  -> Unit {unit['unit_id']} not feasible: {basic_score.constraints_violated}")
                    
            except Exception as e:
                print(f"Error scoring unit {unit['unit_id']}: {e}")
        
        print(f"Units at origin ({schedule_origin}): {len(units_at_origin)}")
        print(f"Units elsewhere: {len(units_elsewhere)}")
        
        # Now test with location-aware scoring
        print("\nTesting with location-aware scoring...")
        feasible_at_origin = []
        for unit in units_at_origin:
            availability_time = engine.calculate_unit_availability_time(
                unit['unit_id'], schedule_origin, departure_minutes, assignments, units_df, routes_df
            )
            
            print(f"Unit {unit['unit_id']} availability time: {minutes_to_time_str(availability_time)} (dep: {schedule['departure_time']})")
            
            # Check if available in time for this schedule
            if availability_time <= departure_minutes:
                try:
                    score = engine.score_unit_for_schedule_with_location(
                        unit, route, schedule, test_date, avg_costs, assignments, units_df, routes_df
                    )
                    if score.is_feasible:
                        feasible_at_origin.append(score)
                        print(f"  -> Feasible with score: {score.total_score}")
                    else:
                        print(f"  -> Not feasible: {score.constraints_violated}")
                except Exception as e:
                    print(f"  -> Error scoring unit with location: {e}")
            else:
                print(f"  -> Not available in time (needs {minutes_to_time_str(availability_time)} but departs at {schedule['departure_time']})")

        feasible_elsewhere = []
        for unit in units_elsewhere:
            availability_time = engine.calculate_unit_availability_time(
                unit['unit_id'], schedule_origin, departure_minutes, assignments, units_df, routes_df
            )
            
            print(f"Unit {unit['unit_id']} elsewhere availability: {minutes_to_time_str(availability_time)} (dep: {schedule['departure_time']})")
            
            # Check if available in time for this schedule (including deadhead time)
            if availability_time <= departure_minutes:
                try:
                    score = engine.score_unit_for_schedule_with_location(
                        unit, route, schedule, test_date, avg_costs, assignments, units_df, routes_df
                    )
                    if score.is_feasible:
                        feasible_elsewhere.append(score)
                        print(f"  -> Feasible with score: {score.total_score}")
                    else:
                        print(f"  -> Not feasible: {score.constraints_violated}")
                except Exception as e:
                    print(f"  -> Error scoring unit with location: {e}")
            else:
                print(f"  -> Not available in time (needs {minutes_to_time_str(availability_time)} but departs at {schedule['departure_time']})")

        print(f"\nFeasible at origin: {len(feasible_at_origin)}")
        print(f"Feasible elsewhere: {len(feasible_elsewhere)}")
        
        # Apply priority rule: if units are available at origin, choose from them first
        if feasible_at_origin:
            print("Selecting from local units")
            best_score = max(feasible_at_origin, key=lambda x: x.total_score)
        elif feasible_elsewhere:
            print("Selecting from elsewhere units")
            best_score = max(feasible_elsewhere, key=lambda x: x.total_score)
        else:
            print("No feasible units found")
            return

        print(f"Best unit: {best_score.unit_id} with score: {best_score.total_score}")

if __name__ == "__main__":
    debug_optimization()