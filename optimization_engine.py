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
        return (route_time_minutes * 2) + self.params.turnaround_time_minutes
    
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
            
            scores = []
            for _, unit in units_df.iterrows():
                score = self.score_unit_for_schedule(
                    unit, route, schedule, target_date, avg_costs, assignments
                )
                scores.append(score)
            
            feasible_scores = [s for s in scores if s.is_feasible]
            
            if feasible_scores:
                best_score = max(feasible_scores, key=lambda x: x.total_score)
                unit = units_df[units_df['unit_id'] == best_score.unit_id].iloc[0]
                
                cycle_time = self.calculate_cycle_time(route['estimated_time_minutes'])
                departure_minutes = time_str_to_minutes(schedule['departure_time'])
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
            else:
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
        
        return {
            'total_schedules': total_schedules,
            'assigned_count': assigned_count,
            'coverage_rate': coverage_rate,
            'utilization_rate': utilization_rate,
            'total_fuel_cost': total_fuel_cost,
            'total_distance': total_distance,
            'average_score': avg_score,
            'units_used': len(assigned_units),
            'units_available': available_units
        }
