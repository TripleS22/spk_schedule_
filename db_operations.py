import pandas as pd
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import (
    get_db_session, Unit, Route, Schedule, Assignment,
    AuditLog, OptimizationRun, Alert, Scenario, Storage, Location, log_audit, create_alert
)
from data_models import get_sample_units, get_sample_routes, get_sample_schedules

def seed_initial_data():
    db = get_db_session()
    try:
        # Check if data has already been initialized before
        initialization_check = db.query(SystemState).filter(SystemState.key == 'data_initialized').first()

        # Only initialize if initialization has never happened before
        if initialization_check is None:
            print("Initializing database with default data...")

            # Add locations
            locations_data = [
                {'location_id': 'L001', 'name': 'Terminal A', 'address': 'Jl. Sudirman No. 1', 'capacity': 50, 'type': 'terminal', 'status': 'active'},
                {'location_id': 'L002', 'name': 'Terminal B', 'address': 'Jl. Thamrin No. 2', 'capacity': 60, 'type': 'terminal', 'status': 'active'},
                {'location_id': 'L003', 'name': 'Terminal C', 'address': 'Jl. Gatot Subroto No. 3', 'capacity': 40, 'type': 'terminal', 'status': 'active'}
            ]
            for loc_data in locations_data:
                location = Location(**loc_data)
                db.add(location)

            # Add units
            units_df = get_sample_units()
            for _, row in units_df.iterrows():
                unit = Unit(
                    unit_id=row['unit_id'],
                    name=row['name'],
                    capacity=row['capacity'],
                    fuel_efficiency=row['fuel_efficiency'],
                    operational_cost_per_km=row['operational_cost_per_km'],
                    status=row['status'],
                    home_location=row['home_location'],
                    allowed_routes=row['allowed_routes']
                )
                db.add(unit)

            # Add routes
            routes_df = get_sample_routes()
            for _, row in routes_df.iterrows():
                route = Route(
                    route_id=row['route_id'],
                    name=row['name'],
                    origin=row['origin'],
                    destination=row['destination'],
                    distance_km=row['distance_km'],
                    estimated_time_minutes=row['estimated_time_minutes'],
                    route_type=row['route_type'],
                    required_capacity=row['required_capacity']
                )
                db.add(route)

            # Add schedules
            schedules_df = get_sample_schedules()
            for _, row in schedules_df.iterrows():
                schedule = Schedule(
                    schedule_id=row['schedule_id'],
                    route_id=row['route_id'],
                    departure_time=row['departure_time'],
                    operating_days=row['operating_days'],
                    priority=row['priority']
                )
                db.add(schedule)

            # Mark that data has been initialized
            initialization_marker = SystemState(
                key='data_initialized',
                value='true'
            )
            db.add(initialization_marker)

            db.commit()
            print("Database initialized with default data successfully.")
        else:
            print("Database already initialized. Skipping default data seeding.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

def reset_to_default_data():
    """
    Reset all data to default sample data
    """
    db = get_db_session()
    try:
        # First delete all existing data (except SystemState)
        db.query(Assignment).delete()
        db.query(Schedule).delete()
        db.query(Route).delete()
        db.query(Unit).delete()
        db.query(Location).delete()

        # Add locations
        locations_data = [
            {'location_id': 'L001', 'name': 'Terminal A', 'address': 'Jl. Sudirman No. 1', 'capacity': 50, 'type': 'terminal', 'status': 'active'},
            {'location_id': 'L002', 'name': 'Terminal B', 'address': 'Jl. Thamrin No. 2', 'capacity': 60, 'type': 'terminal', 'status': 'active'},
            {'location_id': 'L003', 'name': 'Terminal C', 'address': 'Jl. Gatot Subroto No. 3', 'capacity': 40, 'type': 'terminal', 'status': 'active'}
        ]
        for loc_data in locations_data:
            location = Location(**loc_data)
            db.add(location)

        # Add units
        units_df = get_sample_units()
        for _, row in units_df.iterrows():
            unit = Unit(
                unit_id=row['unit_id'],
                name=row['name'],
                capacity=row['capacity'],
                fuel_efficiency=row['fuel_efficiency'],
                operational_cost_per_km=row['operational_cost_per_km'],
                status=row['status'],
                home_location=row['home_location'],
                allowed_routes=row['allowed_routes']
            )
            db.add(unit)

        # Add routes
        routes_df = get_sample_routes()
        for _, row in routes_df.iterrows():
            route = Route(
                route_id=row['route_id'],
                name=row['name'],
                origin=row['origin'],
                destination=row['destination'],
                distance_km=row['distance_km'],
                estimated_time_minutes=row['estimated_time_minutes'],
                route_type=row['route_type'],
                required_capacity=row['required_capacity']
            )
            db.add(route)

        # Add schedules
        schedules_df = get_sample_schedules()
        for _, row in schedules_df.iterrows():
            schedule = Schedule(
                schedule_id=row['schedule_id'],
                route_id=row['route_id'],
                departure_time=row['departure_time'],
                operating_days=row['operating_days'],
                priority=row['priority']
            )
            db.add(schedule)

        # Update the initialization marker
        initialization_check = db.query(SystemState).filter(SystemState.key == 'data_initialized').first()
        if initialization_check:
            initialization_check.value = 'true'
            initialization_check.updated_at = datetime.utcnow()
        else:
            initialization_marker = SystemState(
                key='data_initialized',
                value='true'
            )
            db.add(initialization_marker)

        db.commit()
        print("Database reset to default data successfully.")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error resetting to default data: {e}")
        return False
    finally:
        db.close()

def get_units_df():
    db = get_db_session()
    try:
        units = db.query(Unit).all()
        if not units:
            return pd.DataFrame(columns=['unit_id', 'name', 'capacity', 'fuel_efficiency', 
                                         'operational_cost_per_km', 'status', 'home_location', 'allowed_routes'])
        data = []
        for u in units:
            data.append({
                'unit_id': u.unit_id,
                'name': u.name,
                'capacity': u.capacity,
                'fuel_efficiency': u.fuel_efficiency,
                'operational_cost_per_km': u.operational_cost_per_km,
                'status': u.status,
                'home_location': u.home_location,
                'allowed_routes': u.allowed_routes
            })
        return pd.DataFrame(data)
    finally:
        db.close()

def get_routes_df():
    db = get_db_session()
    try:
        routes = db.query(Route).all()
        if not routes:
            return pd.DataFrame(columns=['route_id', 'name', 'origin', 'destination', 
                                         'distance_km', 'estimated_time_minutes', 'route_type', 'required_capacity'])
        data = []
        for r in routes:
            data.append({
                'route_id': r.route_id,
                'name': r.name,
                'origin': r.origin,
                'destination': r.destination,
                'distance_km': r.distance_km,
                'estimated_time_minutes': r.estimated_time_minutes,
                'route_type': r.route_type,
                'required_capacity': r.required_capacity
            })
        return pd.DataFrame(data)
    finally:
        db.close()

def get_schedules_df():
    db = get_db_session()
    try:
        schedules = db.query(Schedule).all()
        if not schedules:
            return pd.DataFrame(columns=['schedule_id', 'route_id', 'departure_time', 'operating_days', 'priority'])
        data = []
        for s in schedules:
            data.append({
                'schedule_id': s.schedule_id,
                'route_id': s.route_id,
                'departure_time': s.departure_time,
                'operating_days': s.operating_days,
                'priority': s.priority
            })
        return pd.DataFrame(data)
    finally:
        db.close()

def add_unit(unit_data: dict):
    db = get_db_session()
    try:


        unit = Unit(**unit_data)
        db.add(unit)
        db.commit()
        log_audit(db, 'CREATE', 'Unit', unit_data['unit_id'], new_values=unit_data)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding unit: {e}")
        return False
    finally:
        db.close()

def update_unit(unit_id: str, unit_data: dict):
    db = get_db_session()
    try:
        unit = db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if unit:
            old_values = {
                'name': unit.name,
                'capacity': unit.capacity,
                'fuel_efficiency': unit.fuel_efficiency,
                'operational_cost_per_km': unit.operational_cost_per_km,
                'status': unit.status,
                'home_location': unit.home_location,
                'allowed_routes': unit.allowed_routes
            }
            for key, value in unit_data.items():
                setattr(unit, key, value)
            db.commit()
            log_audit(db, 'UPDATE', 'Unit', unit_id, old_values=old_values, new_values=unit_data)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating unit: {e}")
        return False
    finally:
        db.close()

def delete_unit(unit_id: str):
    db = get_db_session()
    try:
        unit = db.query(Unit).filter(Unit.unit_id == unit_id).first()
        if unit:
            old_values = {'unit_id': unit.unit_id, 'name': unit.name}
            
            # First delete all assignments associated with this unit
            associated_assignments = db.query(Assignment).filter(Assignment.unit_id == unit_id).all()
            for assignment in associated_assignments:
                db.delete(assignment)
            
            # Then delete the unit
            db.delete(unit)
            db.commit()
            log_audit(db, 'DELETE', 'Unit', unit_id, old_values=old_values)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting unit: {e}")
        return False
    finally:
        db.close()

def add_route(route_data: dict):
    db = get_db_session()
    try:
        route = Route(**route_data)
        db.add(route)
        db.commit()
        log_audit(db, 'CREATE', 'Route', route_data['route_id'], new_values=route_data)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding route: {e}")
        return False
    finally:
        db.close()

def update_route(route_id: str, route_data: dict):
    db = get_db_session()
    try:
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if route:
            old_values = {
                'name': route.name,
                'origin': route.origin,
                'destination': route.destination,
                'distance_km': route.distance_km,
                'estimated_time_minutes': route.estimated_time_minutes,
                'route_type': route.route_type,
                'required_capacity': route.required_capacity
            }
            for key, value in route_data.items():
                setattr(route, key, value)
            db.commit()
            log_audit(db, 'UPDATE', 'Route', route_id, old_values=old_values, new_values=route_data)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating route: {e}")
        return False
    finally:
        db.close()

def delete_route(route_id: str):
    db = get_db_session()
    try:
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if route:
            old_values = {'route_id': route.route_id, 'name': route.name}
            
            # First delete all schedules associated with this route
            associated_schedules = db.query(Schedule).filter(Schedule.route_id == route_id).all()
            for schedule in associated_schedules:
                db.delete(schedule)
            
            # Then delete the route
            db.delete(route)
            db.commit()
            log_audit(db, 'DELETE', 'Route', route_id, old_values=old_values)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting route: {e}")
        return False
    finally:
        db.close()

def add_schedule(schedule_data: dict):
    db = get_db_session()
    try:
        schedule = Schedule(**schedule_data)
        db.add(schedule)
        db.commit()
        log_audit(db, 'CREATE', 'Schedule', schedule_data['schedule_id'], new_values=schedule_data)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding schedule: {e}")
        return False
    finally:
        db.close()

def update_schedule(schedule_id: str, schedule_data: dict):
    db = get_db_session()
    try:
        schedule = db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()
        if schedule:
            old_values = {
                'route_id': schedule.route_id,
                'departure_time': schedule.departure_time,
                'operating_days': schedule.operating_days,
                'priority': schedule.priority
            }
            for key, value in schedule_data.items():
                setattr(schedule, key, value)
            db.commit()
            log_audit(db, 'UPDATE', 'Schedule', schedule_id, old_values=old_values, new_values=schedule_data)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating schedule: {e}")
        return False
    finally:
        db.close()

def delete_schedule(schedule_id: str):
    db = get_db_session()
    try:
        schedule = db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()
        if schedule:
            old_values = {'schedule_id': schedule.schedule_id, 'route_id': schedule.route_id}
            
            # First delete all assignments associated with this schedule
            associated_assignments = db.query(Assignment).filter(Assignment.schedule_id == schedule_id).all()
            for assignment in associated_assignments:
                db.delete(assignment)
            
            # Then delete the schedule
            db.delete(schedule)
            db.commit()
            log_audit(db, 'DELETE', 'Schedule', schedule_id, old_values=old_values)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting schedule: {e}")
        return False
    finally:
        db.close()

def save_assignments(assignments: list, target_date: datetime):
    db = get_db_session()
    try:
        db.query(Assignment).filter(Assignment.assignment_date == target_date).delete()
        
        for a in assignments:
            assignment = Assignment(
                assignment_date=target_date,
                schedule_id=a.schedule_id,
                route_id=a.route_id,
                unit_id=a.unit_id,
                departure_time=a.departure_time,
                estimated_return_time=a.estimated_return_time,
                total_score=a.total_score,
                fuel_cost=a.fuel_cost,
                assignment_reason=a.assignment_reason,
                status=a.status
            )
            db.add(assignment)
        
        db.commit()
        log_audit(db, 'OPTIMIZATION', 'Assignment', None, 
                  new_values={'date': target_date.isoformat(), 'count': len(assignments)},
                  details=f"Created {len(assignments)} assignments for {target_date.date()}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error saving assignments: {e}")
        return False
    finally:
        db.close()

def save_optimization_run(metrics: dict, target_date: datetime, parameters: dict = None):
    db = get_db_session()
    try:
        run = OptimizationRun(
            run_date=datetime.utcnow(),
            target_date=target_date,
            total_schedules=metrics.get('total_schedules', 0),
            assigned_count=metrics.get('assigned_count', 0),
            coverage_rate=metrics.get('coverage_rate', 0),
            utilization_rate=metrics.get('utilization_rate', 0),
            total_fuel_cost=metrics.get('total_fuel_cost', 0),
            total_distance=metrics.get('total_distance', 0),
            average_score=metrics.get('average_score', 0),
            parameters=json.dumps(parameters) if parameters else None
        )
        db.add(run)
        db.commit()
        return run.id
    except Exception as e:
        db.rollback()
        print(f"Error saving optimization run: {e}")
        return None
    finally:
        db.close()

def get_historical_assignments(start_date: datetime = None, end_date: datetime = None):
    db = get_db_session()
    try:
        query = db.query(Assignment)
        if start_date:
            query = query.filter(Assignment.assignment_date >= start_date)
        if end_date:
            query = query.filter(Assignment.assignment_date <= end_date)
        
        assignments = query.order_by(Assignment.assignment_date.desc()).all()
        data = []
        for a in assignments:
            data.append({
                'assignment_date': a.assignment_date,
                'schedule_id': a.schedule_id,
                'route_id': a.route_id,
                'unit_id': a.unit_id,
                'departure_time': a.departure_time,
                'estimated_return_time': a.estimated_return_time,
                'total_score': a.total_score,
                'fuel_cost': a.fuel_cost,
                'assignment_reason': a.assignment_reason,
                'status': a.status
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        db.close()

def get_optimization_history():
    db = get_db_session()
    try:
        runs = db.query(OptimizationRun).order_by(OptimizationRun.run_date.desc()).all()
        data = []
        for r in runs:
            data.append({
                'run_date': r.run_date,
                'target_date': r.target_date,
                'total_schedules': r.total_schedules,
                'assigned_count': r.assigned_count,
                'coverage_rate': r.coverage_rate,
                'utilization_rate': r.utilization_rate,
                'total_fuel_cost': r.total_fuel_cost,
                'total_distance': r.total_distance,
                'average_score': r.average_score
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        db.close()

def get_audit_logs(entity_type: str = None, limit: int = 100):
    db = get_db_session()
    try:
        query = db.query(AuditLog)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        data = []
        for log in logs:
            data.append({
                'timestamp': log.timestamp,
                'action': log.action,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'old_values': log.old_values,
                'new_values': log.new_values,
                'user_id': log.user_id,
                'details': log.details
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        db.close()

def get_alerts(include_resolved: bool = False):
    db = get_db_session()
    try:
        query = db.query(Alert)
        if not include_resolved:
            query = query.filter(Alert.is_resolved == False)
        alerts = query.order_by(Alert.created_at.desc()).all()
        data = []
        for a in alerts:
            data.append({
                'id': a.id,
                'alert_type': a.alert_type,
                'severity': a.severity,
                'message': a.message,
                'entity_type': a.entity_type,
                'entity_id': a.entity_id,
                'is_resolved': a.is_resolved,
                'created_at': a.created_at
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        db.close()

def resolve_alert(alert_id: int, resolved_by: str = None):
    db = get_db_session()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = resolved_by
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error resolving alert: {e}")
        return False
    finally:
        db.close()

def save_scenario(name: str, description: str, parameters: dict, results: dict, is_baseline: bool = False):
    db = get_db_session()
    try:
        scenario = Scenario(
            name=name,
            description=description,
            parameters=json.dumps(parameters),
            results=json.dumps(results),
            is_baseline=is_baseline
        )
        db.add(scenario)
        db.commit()
        return scenario.id
    except Exception as e:
        db.rollback()
        print(f"Error saving scenario: {e}")
        return None
    finally:
        db.close()

def get_scenarios():
    db = get_db_session()
    try:
        scenarios = db.query(Scenario).order_by(Scenario.created_at.desc()).all()
        data = []
        for s in scenarios:
            data.append({
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'parameters': json.loads(s.parameters) if s.parameters else {},
                'results': json.loads(s.results) if s.results else {},
                'is_baseline': s.is_baseline,
                'created_at': s.created_at
            })
        return data
    finally:
        db.close()

def check_thresholds(metrics: dict, thresholds: dict):
    alerts_created = []
    db = get_db_session()
    try:
        if metrics.get('coverage_rate', 100) < thresholds.get('min_coverage_rate', 80):
            alert = create_alert(
                db, 
                'LOW_COVERAGE', 
                'warning',
                f"Tingkat cakupan ({metrics['coverage_rate']:.1f}%) di bawah batas minimum ({thresholds['min_coverage_rate']}%)"
            )
            alerts_created.append(alert)
        
        if metrics.get('utilization_rate', 100) < thresholds.get('min_utilization_rate', 60):
            alert = create_alert(
                db,
                'LOW_UTILIZATION',
                'info',
                f"Tingkat utilisasi ({metrics['utilization_rate']:.1f}%) di bawah target ({thresholds['min_utilization_rate']}%)"
            )
            alerts_created.append(alert)
        
        if metrics.get('average_score', 1) < thresholds.get('min_avg_score', 0.6):
            alert = create_alert(
                db,
                'LOW_SCORE',
                'warning',
                f"Skor rata-rata ({metrics['average_score']:.2f}) di bawah minimum ({thresholds['min_avg_score']})"
            )
            alerts_created.append(alert)
        
        return len(alerts_created)
    finally:
        db.close()

def get_storage_items():
    db = get_db_session()
    try:
        items = db.query(Storage).order_by(Storage.created_at.desc()).all()
        data = []
        for item in items:
            data.append({
                'id': item.id,
                'key': item.key,
                'value': item.value,
                'data_type': item.data_type,
                'description': item.description,
                'created_at': item.created_at,
                'updated_at': item.updated_at
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        db.close()

def add_storage_item(key: str, value: str, data_type: str = "text", description: str = None):
    db = get_db_session()
    try:
        item = Storage(
            key=key,
            value=value,
            data_type=data_type,
            description=description
        )
        db.add(item)
        db.commit()
        log_audit(db, 'CREATE', 'Storage', key, new_values={'value': value, 'data_type': data_type})
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding storage item: {e}")
        return False
    finally:
        db.close()

def update_storage_item(key: str, value: str = None, data_type: str = None, description: str = None):
    db = get_db_session()
    try:
        item = db.query(Storage).filter(Storage.key == key).first()
        if item:
            old_values = {
                'value': item.value,
                'data_type': item.data_type,
                'description': item.description
            }
            if value is not None:
                item.value = value
            if data_type is not None:
                item.data_type = data_type
            if description is not None:
                item.description = description
            db.commit()
            new_values = {
                'value': item.value,
                'data_type': item.data_type,
                'description': item.description
            }
            log_audit(db, 'UPDATE', 'Storage', key, old_values=old_values, new_values=new_values)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating storage item: {e}")
        return False
    finally:
        db.close()

def delete_storage_item(key: str):
    db = get_db_session()
    try:
        item = db.query(Storage).filter(Storage.key == key).first()
        if item:
            old_values = {'key': item.key, 'value': item.value}
            db.delete(item)
            db.commit()
            log_audit(db, 'DELETE', 'Storage', key, old_values=old_values)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting storage item: {e}")
        return False
    finally:
        db.close()

def get_storage_item(key: str):
    db = get_db_session()
    try:
        item = db.query(Storage).filter(Storage.key == key).first()
        if item:
            return {
                'id': item.id,
                'key': item.key,
                'value': item.value,
                'data_type': item.data_type,
                'description': item.description,
                'created_at': item.created_at,
                'updated_at': item.updated_at
            }
        return None
    finally:
        db.close()

def get_locations_df():
    db = get_db_session()
    try:
        locations = db.query(Location).order_by(Location.created_at.desc()).all()
        if not locations:
            return pd.DataFrame(columns=['location_id', 'name', 'address', 'capacity', 'type', 'status'])
        data = []
        for l in locations:
            data.append({
                'location_id': l.location_id,
                'name': l.name,
                'address': l.address,
                'capacity': l.capacity,
                'type': l.type,
                'status': l.status
            })
        return pd.DataFrame(data)
    finally:
        db.close()

def add_location(location_data: dict):
    db = get_db_session()
    try:
        location = Location(**location_data)
        db.add(location)
        db.commit()
        log_audit(db, 'CREATE', 'Location', location_data['location_id'], new_values=location_data)
        return True
    except Exception as e:
        db.rollback()
        print(f"Error adding location: {e}")
        return False
    finally:
        db.close()

def update_location(location_id: str, location_data: dict):
    db = get_db_session()
    try:
        location = db.query(Location).filter(Location.location_id == location_id).first()
        if location:
            old_values = {
                'name': location.name,
                'address': location.address,
                'capacity': location.capacity,
                'type': location.type,
                'status': location.status
            }
            for key, value in location_data.items():
                setattr(location, key, value)
            db.commit()
            log_audit(db, 'UPDATE', 'Location', location_id, old_values=old_values, new_values=location_data)
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating location: {e}")
        return False
    finally:
        db.close()

def delete_location(location_id: str):
    db = get_db_session()
    try:
        location = db.query(Location).filter(Location.location_id == location_id).first()
        if location:
            print(f"Attempting to delete location: '{location.name}' (ID: {location_id})")

            # Check if there are units associated with this location
            # Using strip() to handle potential whitespace issues
            associated_units = db.query(Unit).filter(Unit.home_location == location.name.strip()).all()

            print(f"Found {len(associated_units)} associated units for location '{location.name}'")

            if associated_units:
                # Don't delete the location if there are associated units
                print(f"Cannot delete location '{location.name}' because it has {len(associated_units)} associated unit(s)")
                for unit in associated_units:
                    print(f"  - Unit {unit.unit_id}: {unit.name}")
                return False

            old_values = {'location_id': location.location_id, 'name': location.name}
            print(f"Deleting location '{location.name}' with ID {location_id}")

            # Delete the location (no units to worry about)
            db.delete(location)
            db.commit()
            log_audit(db, 'DELETE', 'Location', location_id, old_values=old_values)
            print(f"Location '{location.name}' successfully deleted from database")
            return True
        else:
            print(f"Location with ID {location_id} not found")
            return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting location: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()

def delete_all_units():
    """
    Delete all units from the database
    """
    db = get_db_session()
    try:
        # First delete all assignments associated with units
        db.query(Assignment).delete()

        # Then delete all units
        units = db.query(Unit).all()
        deleted_count = len(units)

        for unit in units:
            old_values = {'unit_id': unit.unit_id, 'name': unit.name}
            log_audit(db, 'DELETE', 'Unit', unit.unit_id, old_values=old_values)

        db.query(Unit).delete()
        db.commit()

        return True, deleted_count
    except Exception as e:
        db.rollback()
        print(f"Error deleting all units: {e}")
        return False, 0
    finally:
        db.close()

def delete_all_routes():
    """
    Delete all routes from the database
    This also deletes associated schedules and assignments
    """
    db = get_db_session()
    try:
        # First delete all assignments associated with schedules that will be deleted
        db.query(Assignment).delete()

        # Then delete all schedules
        db.query(Schedule).delete()

        # Finally delete all routes
        routes = db.query(Route).all()
        deleted_count = len(routes)

        for route in routes:
            old_values = {'route_id': route.route_id, 'name': route.name}
            log_audit(db, 'DELETE', 'Route', route.route_id, old_values=old_values)

        db.query(Route).delete()
        db.commit()

        return True, deleted_count
    except Exception as e:
        db.rollback()
        print(f"Error deleting all routes: {e}")
        return False, 0
    finally:
        db.close()

def delete_all_schedules():
    """
    Delete all schedules from the database
    This also deletes associated assignments
    """
    db = get_db_session()
    try:
        # First delete all assignments associated with schedules
        db.query(Assignment).delete()

        # Then delete all schedules
        schedules = db.query(Schedule).all()
        deleted_count = len(schedules)

        for schedule in schedules:
            old_values = {'schedule_id': schedule.schedule_id, 'route_id': schedule.route_id}
            log_audit(db, 'DELETE', 'Schedule', schedule.schedule_id, old_values=old_values)

        db.query(Schedule).delete()
        db.commit()

        return True, deleted_count
    except Exception as e:
        db.rollback()
        print(f"Error deleting all schedules: {e}")
        return False, 0
    finally:
        db.close()

def delete_all_assignments():
    """
    Delete all assignments from the database
    """
    db = get_db_session()
    try:
        assignments = db.query(Assignment).all()
        deleted_count = len(assignments)

        for assignment in assignments:
            old_values = {
                'assignment_date': str(assignment.assignment_date),
                'schedule_id': assignment.schedule_id,
                'unit_id': assignment.unit_id
            }
            log_audit(db, 'DELETE', 'Assignment', f"{assignment.assignment_date}_{assignment.schedule_id}_{assignment.unit_id}", old_values=old_values)

        db.query(Assignment).delete()
        db.commit()

        return True, deleted_count
    except Exception as e:
        db.rollback()
        print(f"Error deleting all assignments: {e}")
        return False, 0
    finally:
        db.close()

def delete_all_data():
    """
    Delete all data from the database (units, routes, schedules, assignments)
    """
    db = get_db_session()
    try:
        # Delete assignments first to handle foreign key constraints
        db.query(Assignment).delete()

        # Then delete other entities
        unit_count = db.query(Unit).count()
        route_count = db.query(Route).count()
        schedule_count = db.query(Schedule).count()

        # Log the deletion
        log_audit(db, 'DELETE', 'ALL_DATA', None, details="Deleting all units, routes, and schedules")

        db.query(Unit).delete()
        db.query(Route).delete()
        db.query(Schedule).delete()

        db.commit()

        return True, {'units': unit_count, 'routes': route_count, 'schedules': schedule_count}
    except Exception as e:
        db.rollback()
        print(f"Error deleting all data: {e}")
        return False, {'units': 0, 'routes': 0, 'schedules': 0}
    finally:
        db.close()
