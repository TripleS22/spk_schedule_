import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from data_models import (
    parse_allowed_routes, parse_operating_days, get_day_name,
    time_str_to_minutes, minutes_to_time_str, OperationalParameters
)

@dataclass
class AssignmentScore:
    unit_id: str
    schedule_id: str
    route_id: str
    capacity_score: float
    distance_score: float
    availability_score: float
    cost_score: float
    total_score: float
    is_feasible: bool
    constraints_violated: List[str] = field(default_factory=list)
    
@dataclass
class Assignment:
    schedule_id: str
    route_id: str
    unit_id: str
    departure_time: str
    estimated_return_time: str
    total_score: float
    fuel_cost: float
    assignment_reason: str
    status: str = "Assigned"

class OptimizationEngine:
    def __init__(self, params: OperationalParameters = None):
        self.params = params or OperationalParameters()
        self.weights = {
            'capacity': 0.25,
            'distance': 0.20,
            'availability': 0.30,
            'cost': 0.25
        }
        
    def calculate_cycle_time(self, route_time_minutes: int) -> int:
        return (route_time_minutes ) + self.params.turnaround_time_minutes
    
    def calculate_fuel_cost(self, distance_km: float, fuel_efficiency: float) -> float:
        fuel_needed = distance_km * 2 / fuel_efficiency
        return fuel_needed * self.params.fuel_price_per_liter
    
    def calculate_capacity_score(self, unit_capacity: int, required_capacity: int) -> float:
        if unit_capacity < required_capacity:
            return 0.0
        excess_ratio = (unit_capacity - required_capacity) / required_capacity
        if excess_ratio <= 0.2:
            return 1.0
        elif excess_ratio <= 0.5:
            return 0.8
        else:
            return max(0.5, 1.0 - excess_ratio * 0.5)
    
    def calculate_distance_score(self, unit_home: str, route_origin: str, route_distance: float) -> float:
        if unit_home == route_origin:
            return 1.0
        else:
            return 0.7

    def calculate_distance_score_location_based(self, unit_current_location: str, route_origin: str, route_distance: float, deadhead_distance: int) -> float:
        """
        Calculate distance score based on current unit location rather than home location
        Includes penalties for deadhead distance if the unit is not at the route origin
        """
        if unit_current_location == route_origin:
            return 1.0  # Full score if already at origin
        else:
            # Lower score if deadhead is required
            # The score decreases as deadhead time increases
            # We'll use the deadhead time to determine the penalty
            if deadhead_distance == 0:
                return 1.0
            elif deadhead_distance <= 30:  # Less than 30 mins deadhead
                return 0.8
            elif deadhead_distance <= 60:  # Less than 1 hour deadhead
                return 0.6
            elif deadhead_distance <= 120:  # Less than 2 hours deadhead
                return 0.4
            else:  # More than 2 hours deadhead
                return 0.2
    
    def calculate_availability_score(self, unit_status: str, is_route_allowed: bool) -> float:
        if unit_status != "Available":
            return 0.0
        if not is_route_allowed:
            return 0.0
        return 1.0
    
    def calculate_cost_score(self, operational_cost: float, fuel_cost: float, 
                            avg_operational_cost: float, avg_fuel_cost: float) -> float:
        total_cost = operational_cost + fuel_cost
        avg_total = avg_operational_cost + avg_fuel_cost
        if avg_total == 0:
            return 0.5
        cost_ratio = total_cost / avg_total
        if cost_ratio <= 0.8:
            return 1.0
        elif cost_ratio <= 1.0:
            return 0.9
        elif cost_ratio <= 1.2:
            return 0.7
        else:
            return max(0.3, 1.0 - (cost_ratio - 1.0) * 0.5)
    
    def get_unit_last_location(self, unit_id: str, current_assignments: List[Assignment], units_df: pd.DataFrame, routes_df: pd.DataFrame) -> str:
        """Get the last location of a unit based on the most recent assignment"""
        # Find the most recent assignment for this unit
        unit_assignments = [a for a in current_assignments if a.unit_id == unit_id]

        if unit_assignments:
            # Get the assignment with the latest departure time
            latest_assignment = max(unit_assignments, key=lambda a: time_str_to_minutes(a.departure_time))

            # Find the associated route to get the destination
            # The destination of the last assignment becomes the current unit's location
            return self.get_destination_from_assignment(latest_assignment, routes_df)
        else:
            # If no assignments, use the home location or last_location field if available
            unit_row = units_df[units_df['unit_id'] == unit_id].iloc[0]
            return unit_row['last_location'] if 'last_location' in unit_row and unit_row['last_location'] else unit_row['home_location']

    def get_destination_from_assignment(self, assignment: Assignment, routes_df: pd.DataFrame) -> str:
        """Get the destination from an assignment based on the route"""
        # Find the route corresponding to the assignment
        route_row = routes_df[routes_df['route_id'] == assignment.route_id].iloc[0]
        return route_row['destination']

    def check_constraints_with_location(self, unit_row: pd.Series, route_row: pd.Series,
                                       schedule_row: pd.Series, target_date: datetime,
                                       current_assignments: List[Assignment],
                                       units_df: pd.DataFrame, routes_df: pd.DataFrame) -> Tuple[bool, List[str]]:
        violations = []

        allowed_routes = parse_allowed_routes(unit_row['allowed_routes'])
        if route_row['route_id'] not in allowed_routes:
            violations.append(f"Unit tidak diizinkan melayani rute {route_row['route_id']}")

        if unit_row['capacity'] < route_row['required_capacity']:
            violations.append(f"Kapasitas unit ({unit_row['capacity']}) kurang dari kebutuhan rute ({route_row['required_capacity']})")

        if unit_row['status'] != "Available":
            violations.append(f"Unit dalam status {unit_row['status']}")

        operating_days = parse_operating_days(schedule_row['operating_days'])
        target_day = get_day_name(target_date)
        if target_day not in operating_days:
            violations.append(f"Jadwal tidak beroperasi pada hari {target_day}")

        schedule_departure = time_str_to_minutes(schedule_row['departure_time'])

        # Get the unit's last location
        unit_last_location = self.get_unit_last_location(unit_row['unit_id'], current_assignments, units_df)

        # Check if the unit needs deadhead time
        if unit_last_location != route_row['origin']:
            # Calculate deadhead time from unit's last location to the route origin
            deadhead_time = self.get_deadhead_time(unit_last_location, route_row['origin'])
            # We need to account for rest time + deadhead time before the departure
            # So the effective availability is later than the simple rest time
        else:
            # Unit is already at the origin, no deadhead time needed
            deadhead_time = 0

        # Check time conflicts with current assignments
        cycle_time = self.calculate_cycle_time(route_row['estimated_time_minutes'])
        schedule_return = schedule_departure + cycle_time

        for assignment in current_assignments:
            if assignment.unit_id == unit_row['unit_id']:
                existing_departure = time_str_to_minutes(assignment.departure_time)
                existing_return = time_str_to_minutes(assignment.estimated_return_time)

                buffer = self.params.minimum_rest_time_minutes

                if not (schedule_return + buffer <= existing_departure or
                       existing_return + buffer <= schedule_departure):
                    violations.append(f"Konflik waktu dengan penugasan {assignment.schedule_id}")

        return len(violations) == 0, violations

    def get_deadhead_time(self, from_location: str, to_location: str) -> int:
        """Get deadhead travel time between two locations"""
        # Check the predefined travel times
        key = (from_location, to_location)
        if key in self.params.travel_times:
            return self.params.travel_times[key]

        reverse_key = (to_location, from_location)
        if reverse_key in self.params.travel_times:
            return self.params.travel_times[reverse_key]

        # If not defined, return a default value or calculate based on proximity
        # For now, return a default travel time of 60 minutes, or 0 if same location
        if from_location == to_location:
            return 0
        else:
            # Return a high value to discourage moving when location is unknown
            return 120  # Default to 2 hours if travel time not defined

    def calculate_unit_availability_time(self, unit_id: str, route_origin: str, schedule_departure: int,
                                       current_assignments: List[Assignment], units_df: pd.DataFrame, routes_df: pd.DataFrame) -> int:
        """
        Calculate when a unit becomes available considering:
        - Last return time
        - Minimum rest time
        - Deadhead time if unit is not at route origin
        """
        # Get the unit's last location
        unit_last_location = self.get_unit_last_location(unit_id, current_assignments, units_df, routes_df)

        # Find the last assignment for this unit to determine when it becomes free
        unit_assignments = [a for a in current_assignments if a.unit_id == unit_id]

        if unit_assignments:
            # Get the assignment with the latest return time (most recent end of duty)
            latest_assignment = max(unit_assignments, key=lambda a: time_str_to_minutes(a.estimated_return_time))
            last_return_time = time_str_to_minutes(latest_assignment.estimated_return_time)
        else:
            # If no assignments, the unit is available from the start of the day (00:00 = 0 minutes)
            last_return_time = 0

        # Add minimum rest time
        availability_after_rest = last_return_time + self.params.minimum_rest_time_minutes

        # Check if unit needs to deadhead to reach the route origin
        if unit_last_location != route_origin:
            # Need to calculate deadhead time from last location to route origin
            deadhead_time = self.get_deadhead_time(unit_last_location, route_origin)
            # Total time required = last_return + rest + deadhead
            total_available_time = availability_after_rest + deadhead_time
        else:
            # Unit is already at the right location
            total_available_time = availability_after_rest

        return total_available_time

    def check_constraints(self, unit_row: pd.Series, route_row: pd.Series,
                         schedule_row: pd.Series, target_date: datetime,
                         current_assignments: List[Assignment]) -> Tuple[bool, List[str]]:
        violations = []

        allowed_routes = parse_allowed_routes(unit_row['allowed_routes'])
        if route_row['route_id'] not in allowed_routes:
            violations.append(f"Unit tidak diizinkan melayani rute {route_row['route_id']}")

        if unit_row['capacity'] < route_row['required_capacity']:
            violations.append(f"Kapasitas unit ({unit_row['capacity']}) kurang dari kebutuhan rute ({route_row['required_capacity']})")

        if unit_row['status'] != "Available":
            violations.append(f"Unit dalam status {unit_row['status']}")

        operating_days = parse_operating_days(schedule_row['operating_days'])
        target_day = get_day_name(target_date)
        if target_day not in operating_days:
            violations.append(f"Jadwal tidak beroperasi pada hari {target_day}")

        schedule_departure = time_str_to_minutes(schedule_row['departure_time'])
        cycle_time = self.calculate_cycle_time(route_row['estimated_time_minutes'])
        schedule_return = schedule_departure + cycle_time

        for assignment in current_assignments:
            if assignment.unit_id == unit_row['unit_id']:
                existing_departure = time_str_to_minutes(assignment.departure_time)
                existing_return = time_str_to_minutes(assignment.estimated_return_time)

                buffer = self.params.minimum_rest_time_minutes

                if not (schedule_return + buffer <= existing_departure or
                       existing_return + buffer <= schedule_departure):
                    violations.append(f"Konflik waktu dengan penugasan {assignment.schedule_id}")

        return len(violations) == 0, violations
    
    def score_unit_for_schedule(self, unit_row: pd.Series, route_row: pd.Series,
                               schedule_row: pd.Series, target_date: datetime,
                               avg_costs: Dict[str, float],
                               current_assignments: List[Assignment]) -> AssignmentScore:
        is_feasible, violations = self.check_constraints(
            unit_row, route_row, schedule_row, target_date, current_assignments
        )

        allowed_routes = parse_allowed_routes(unit_row['allowed_routes'])
        is_route_allowed = route_row['route_id'] in allowed_routes

        capacity_score = self.calculate_capacity_score(
            unit_row['capacity'], route_row['required_capacity']
        )

        distance_score = self.calculate_distance_score(
            unit_row['home_location'], route_row['origin'], route_row['distance_km']
        )

        availability_score = self.calculate_availability_score(
            unit_row['status'], is_route_allowed
        )

        fuel_cost = self.calculate_fuel_cost(
            route_row['distance_km'], unit_row['fuel_efficiency']
        )
        operational_cost = unit_row['operational_cost_per_km'] * route_row['distance_km'] * 2

        cost_score = self.calculate_cost_score(
            operational_cost, fuel_cost,
            avg_costs.get('operational', 50000),
            avg_costs.get('fuel', 30000)
        )

        total_score = (
            self.weights['capacity'] * capacity_score +
            self.weights['distance'] * distance_score +
            self.weights['availability'] * availability_score +
            self.weights['cost'] * cost_score
        )

        return AssignmentScore(
            unit_id=unit_row['unit_id'],
            schedule_id=schedule_row['schedule_id'],
            route_id=route_row['route_id'],
            capacity_score=capacity_score,
            distance_score=distance_score,
            availability_score=availability_score,
            cost_score=cost_score,
            total_score=total_score,
            is_feasible=is_feasible,
            constraints_violated=violations
        )

    def score_unit_for_schedule_with_location(self, unit_row: pd.Series, route_row: pd.Series,
                               schedule_row: pd.Series, target_date: datetime,
                               avg_costs: Dict[str, float],
                               current_assignments: List[Assignment],
                               units_df: pd.DataFrame, routes_df: pd.DataFrame) -> AssignmentScore:
        # First check basic constraints
        is_feasible, violations = self.check_constraints(
            unit_row, route_row, schedule_row, target_date, current_assignments
        )

        # Then check time availability considering location and rest time
        schedule_departure = time_str_to_minutes(schedule_row['departure_time'])
        availability_time = self.calculate_unit_availability_time(
            unit_row['unit_id'], route_row['origin'], schedule_departure, current_assignments, units_df, routes_df
        )

        # Check if unit is available in time
        if availability_time > schedule_departure:
            is_feasible = False
            violations.append(f"Unit tidak tersedia cukup awal. Tersedia pukul {minutes_to_time_str(availability_time)}, jadwal berangkat {schedule_row['departure_time']}")

        allowed_routes = parse_allowed_routes(unit_row['allowed_routes'])
        is_route_allowed = route_row['route_id'] in allowed_routes

        capacity_score = self.calculate_capacity_score(
            unit_row['capacity'], route_row['required_capacity']
        )

        # Calculate distance score based on last location, not home location
        unit_last_location = self.get_unit_last_location(unit_row['unit_id'], current_assignments, units_df, routes_df)
        distance_score = self.calculate_distance_score_location_based(
            unit_last_location, route_row['origin'], route_row['distance_km'], self.get_deadhead_time(unit_last_location, route_row['origin'])
        )

        availability_score = self.calculate_availability_score(
            unit_row['status'], is_route_allowed
        )

        fuel_cost = self.calculate_fuel_cost(
            route_row['distance_km'], unit_row['fuel_efficiency']
        )
        operational_cost = unit_row['operational_cost_per_km'] * route_row['distance_km'] * 2

        cost_score = self.calculate_cost_score(
            operational_cost, fuel_cost,
            avg_costs.get('operational', 50000),
            avg_costs.get('fuel', 30000)
        )

        # Add location fit score
        location_fit_score = 1.0 if unit_last_location == route_row['origin'] else 0.3

        # Add rest time fit score
        time_available = schedule_departure - availability_time
        min_rest_needed = self.params.minimum_rest_time_minutes
        if time_available >= min_rest_needed:
            rest_fit_score = 1.0
        elif time_available > 0:
            rest_fit_score = 0.5
        else:
            rest_fit_score = 0.0

        # Update weights for the new factors
        total_score = (
            self.weights['capacity'] * capacity_score * 0.8 +
            self.weights['distance'] * distance_score * 0.8 +
            self.weights['availability'] * availability_score +
            self.weights['cost'] * cost_score * 0.9 +
            0.1 * location_fit_score +  # New location fit factor
            0.1 * rest_fit_score        # New rest time fit factor
        )

        return AssignmentScore(
            unit_id=unit_row['unit_id'],
            schedule_id=schedule_row['schedule_id'],
            route_id=route_row['route_id'],
            capacity_score=capacity_score,
            distance_score=distance_score,
            availability_score=availability_score,
            cost_score=cost_score,
            total_score=total_score,
            is_feasible=is_feasible,
            constraints_violated=violations
        )
    
    def optimize_assignments(self, units_df: pd.DataFrame, routes_df: pd.DataFrame,
                           schedules_df: pd.DataFrame, target_date: datetime) -> Tuple[List[Assignment], List[Dict]]:
        assignments = []
        unassigned = []

        avg_costs = {
            'operational': units_df['operational_cost_per_km'].mean() * routes_df['distance_km'].mean() * 2,
            'fuel': (routes_df['distance_km'].mean() * 2 / units_df['fuel_efficiency'].mean()) * self.params.fuel_price_per_liter
        }

        target_day = get_day_name(target_date)

        active_schedules = []
        for _, schedule in schedules_df.iterrows():
            operating_days = parse_operating_days(schedule['operating_days'])
            if target_day in operating_days:
                active_schedules.append(schedule)

        active_schedules.sort(key=lambda x: (x['priority'], x['departure_time']))

        for schedule in active_schedules:
            route = routes_df[routes_df['route_id'] == schedule['route_id']].iloc[0]

            # Group units by location relative to schedule origin
            schedule_origin = route['origin']
            departure_minutes = time_str_to_minutes(schedule['departure_time'])

            # Divide units into two groups: those at the same location and others
            units_at_origin = []
            units_elsewhere = []

            for _, unit in units_df.iterrows():
                # Check if unit is feasible in basic constraints
                basic_score = self.score_unit_for_schedule(
                    unit, route, schedule, target_date, avg_costs, assignments
                )

                if basic_score.is_feasible:
                    # Check the unit's last location
                    unit_last_location = self.get_unit_last_location(unit['unit_id'], assignments, units_df, routes_df)

                    if unit_last_location == schedule_origin:
                        units_at_origin.append(unit)
                    else:
                        units_elsewhere.append(unit)

            # Calculate availability times and check feasibility for each group
            feasible_at_origin = []
            for unit in units_at_origin:
                availability_time = self.calculate_unit_availability_time(
                    unit['unit_id'], schedule_origin, departure_minutes, assignments, units_df, routes_df
                )

                # Check if available in time for this schedule
                if availability_time <= departure_minutes:
                    score = self.score_unit_for_schedule_with_location(
                        unit, route, schedule, target_date, avg_costs, assignments, units_df, routes_df
                    )
                    if score.is_feasible:
                        feasible_at_origin.append(score)

            feasible_elsewhere = []
            for unit in units_elsewhere:
                availability_time = self.calculate_unit_availability_time(
                    unit['unit_id'], schedule_origin, departure_minutes, assignments, units_df, routes_df
                )

                # Check if available in time for this schedule (including deadhead time)
                if availability_time <= departure_minutes:
                    score = self.score_unit_for_schedule_with_location(
                        unit, route, schedule, target_date, avg_costs, assignments, units_df, routes_df
                    )
                    if score.is_feasible:
                        feasible_elsewhere.append(score)

            # Apply priority rule: if units are available at origin, choose from them first
            if feasible_at_origin:
                # Select best from local units only
                best_score = max(feasible_at_origin, key=lambda x: x.total_score)
            elif feasible_elsewhere:
                # Only if no local units are available, choose from elsewhere
                best_score = max(feasible_elsewhere, key=lambda x: x.total_score)
            else:
                # No feasible units
                all_units = list(units_at_origin) + list(units_elsewhere)
                scores = []
                for unit in all_units:
                    score = self.score_unit_for_schedule_with_location(
                        unit, route, schedule, target_date, avg_costs, assignments, units_df, routes_df
                    )
                    scores.append(score)

                all_violations = []
                for s in scores:
                    all_violations.extend(s.constraints_violated)
                unique_violations = list(set(all_violations))

                unassigned.append({
                    'schedule_id': schedule['schedule_id'],
                    'route_id': schedule['route_id'],
                    'departure_time': schedule['departure_time'],
                    'reasons': unique_violations[:3]
                })
                continue

            # Create assignment with the selected best unit
            unit = units_df[units_df['unit_id'] == best_score.unit_id].iloc[0]

            cycle_time = self.calculate_cycle_time(route['estimated_time_minutes'])
            return_minutes = departure_minutes + cycle_time

            fuel_cost = self.calculate_fuel_cost(route['distance_km'], unit['fuel_efficiency'])

            reason_parts = []
            if best_score.capacity_score >= 0.9:
                reason_parts.append("kapasitas optimal")
            if best_score.distance_score >= 0.9:
                reason_parts.append("lokasi asal sesuai")
            if best_score.cost_score >= 0.8:
                reason_parts.append("biaya efisien")

            reason = f"Skor tertinggi ({best_score.total_score:.2f}): " + ", ".join(reason_parts) if reason_parts else f"Skor tertinggi: {best_score.total_score:.2f}"

            assignment = Assignment(
                schedule_id=schedule['schedule_id'],
                route_id=schedule['route_id'],
                unit_id=best_score.unit_id,
                departure_time=schedule['departure_time'],
                estimated_return_time=minutes_to_time_str(return_minutes),
                total_score=best_score.total_score,
                fuel_cost=fuel_cost,
                assignment_reason=reason
            )
            assignments.append(assignment)

        return assignments, unassigned
    
    def calculate_metrics(self, assignments: List[Assignment],
                         units_df: pd.DataFrame, routes_df: pd.DataFrame,
                         schedules_df: pd.DataFrame, target_date: datetime) -> Dict:
        target_day = get_day_name(target_date)

        active_schedules = []
        for _, schedule in schedules_df.iterrows():
            operating_days = parse_operating_days(schedule['operating_days'])
            if target_day in operating_days:
                active_schedules.append(schedule)

        total_schedules = len(active_schedules)
        assigned_count = len(assignments)
        coverage_rate = (assigned_count / total_schedules * 100) if total_schedules > 0 else 0

        assigned_units = set(a.unit_id for a in assignments)
        available_units = len(units_df[units_df['status'] == 'Available'])
        utilization_rate = (len(assigned_units) / available_units * 100) if available_units > 0 else 0

        total_fuel_cost = sum(a.fuel_cost for a in assignments)

        total_distance = 0
        for a in assignments:
            route = routes_df[routes_df['route_id'] == a.route_id].iloc[0]
            total_distance += route['distance_km'] * 2

        avg_score = np.mean([a.total_score for a in assignments]) if assignments else 0

        # Calculate idle time for each unit
        idle_times = {}
        working_times = {}

        for unit_id in units_df['unit_id']:
            # Calculate total working time for this unit
            unit_assignments = [a for a in assignments if a.unit_id == unit_id]
            total_working_time = 0

            for assignment in unit_assignments:
                departure_minutes = time_str_to_minutes(assignment.departure_time)
                return_minutes = time_str_to_minutes(assignment.estimated_return_time)

                # Calculate the actual cycle time from departure to return
                cycle_time = return_minutes - departure_minutes
                # Use the calculated cycle time (which includes travel and turnaround)
                total_working_time += max(0, cycle_time)  # Ensure non-negative cycle time

            working_times[unit_id] = total_working_time
            # Idle time = max working hours - working time
            max_working_minutes = self.params.max_working_hours_per_day * 60
            idle_time = max_working_minutes - total_working_time
            idle_times[unit_id] = max(0, idle_time)  # Ensure non-negative idle time

        # Calculate average idle time across all available units
        total_idle_time = sum(idle_times.values())
        total_available_units = len(units_df[units_df['status'] == 'Available'])
        avg_idle_time = total_idle_time / total_available_units if total_available_units > 0 else 0

        return {
            'total_schedules': total_schedules,
            'assigned_count': assigned_count,
            'coverage_rate': coverage_rate,
            'utilization_rate': utilization_rate,
            'total_fuel_cost': total_fuel_cost,
            'total_distance': total_distance,
            'average_score': avg_score,
            'units_used': len(assigned_units),
            'units_available': available_units,
            'idle_times': idle_times,
            'working_times': working_times,
            'average_idle_time_minutes': avg_idle_time,
            'total_idle_time_minutes': total_idle_time
        }
