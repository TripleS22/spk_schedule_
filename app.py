import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from io import BytesIO

from data_models import (
    get_sample_units, get_sample_routes, get_sample_schedules,
    parse_allowed_routes, parse_operating_days, get_day_name,
    time_str_to_minutes, minutes_to_time_str, OperationalParameters
)
from optimization_engine import OptimizationEngine, Assignment
from db_operations import (
    get_units_df, get_routes_df, get_schedules_df,
    add_unit, update_unit, delete_unit,
    add_route, update_route, delete_route,
    add_schedule, update_schedule, delete_schedule,
    save_assignments, save_optimization_run,
    get_historical_assignments, get_optimization_history,
    get_audit_logs, get_alerts, resolve_alert,
    save_scenario, get_scenarios, check_thresholds, seed_initial_data,
    delete_all_units, delete_all_routes, delete_all_schedules, delete_all_assignments, delete_all_data, reset_to_default_data,
    get_locations_df, add_location, update_location, delete_location
)
from database import init_db

init_db()
seed_initial_data()

st.set_page_config(
    page_title="Modul Analisis Logistik",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    if 'units_df' not in st.session_state:
        st.session_state.units_df = get_units_df()
    if 'routes_df' not in st.session_state:
        st.session_state.routes_df = get_routes_df()
    if 'schedules_df' not in st.session_state:
        st.session_state.schedules_df = get_schedules_df()
    if 'assignments' not in st.session_state:
        st.session_state.assignments = []
    if 'unassigned' not in st.session_state:
        st.session_state.unassigned = []
    if 'metrics' not in st.session_state:
        st.session_state.metrics = {}
    if 'last_optimization_date' not in st.session_state:
        st.session_state.last_optimization_date = None
    if 'params' not in st.session_state:
        st.session_state.params = OperationalParameters()
    if 'thresholds' not in st.session_state:
        st.session_state.thresholds = {
            'min_coverage_rate': 80,
            'min_utilization_rate': 60,
            'min_avg_score': 0.6
        }

def refresh_data():
    st.session_state.units_df = get_units_df()
    st.session_state.routes_df = get_routes_df()
    st.session_state.schedules_df = get_schedules_df()

def render_sidebar():
    with st.sidebar:
        st.title("Navigasi")
        
        page = st.radio(
            "Pilih Menu:",
            ["Dashboard", "Data Unit", "Data Rute", "Data Jadwal", "Data Lokasi",
             "Optimasi Penugasan", "Monitoring & Alert", "Analisis Skenario",
             "Laporan & Analitik", "Analisis Idle Time", "Audit Trail", "Pengaturan"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("### Status Sistem")
        available_units = len(st.session_state.units_df[st.session_state.units_df['status'] == 'Available'])
        total_units = len(st.session_state.units_df)
        
        st.metric("Unit Tersedia", f"{available_units}/{total_units}")
        st.metric("Total Rute", len(st.session_state.routes_df))
        st.metric("Total Jadwal", len(st.session_state.schedules_df))
        
        if st.session_state.last_optimization_date:
            st.caption(f"Optimasi terakhir: {st.session_state.last_optimization_date.strftime('%d/%m/%Y')}")
        
        return page

def render_dashboard():
    st.title("Dashboard Logistik")
    st.markdown("Ringkasan operasional dan status penugasan harian")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        available = len(st.session_state.units_df[st.session_state.units_df['status'] == 'Available'])
        st.metric("Unit Tersedia", available, 
                 delta=f"dari {len(st.session_state.units_df)} total")
    
    with col2:
        st.metric("Rute Aktif", len(st.session_state.routes_df))
    
    with col3:
        if st.session_state.metrics:
            st.metric("Tingkat Cakupan", f"{st.session_state.metrics.get('coverage_rate', 0):.1f}%")
        else:
            st.metric("Tingkat Cakupan", "Belum dihitung")

    with col4:
        if st.session_state.metrics:
            st.metric("Utilisasi Unit", f"{st.session_state.metrics.get('utilization_rate', 0):.1f}%")
        else:
            st.metric("Utilisasi Unit", "Belum dihitung")

    # Add additional metrics row
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        if st.session_state.metrics:
            avg_idle_time = st.session_state.metrics.get('average_idle_time_minutes', 0)
            avg_idle_hours = avg_idle_time / 60  # Convert to hours
            st.metric("Rata-rata Idle Time", f"{avg_idle_hours:.1f} jam")
        else:
            st.metric("Rata-rata Idle Time", "Belum dihitung")

    with col6:
        if st.session_state.metrics:
            st.metric("Unit Digunakan", st.session_state.metrics.get('units_used', 0))
        else:
            st.metric("Unit Digunakan", "Belum dihitung")

    with col7:
        if st.session_state.metrics:
            total_idle_time = st.session_state.metrics.get('total_idle_time_minutes', 0)
            total_idle_hours = total_idle_time / 60
            st.metric("Total Idle Time", f"{total_idle_hours:.1f} jam")
        else:
            st.metric("Total Idle Time", "Belum dihitung")

    with col8:
        if st.session_state.metrics:
            avg_score = st.session_state.metrics.get('average_score', 0)
            st.metric("Skor Rata-rata", f"{avg_score:.2f}")
        else:
            st.metric("Skor Rata-rata", "Belum dihitung")
    
    st.divider()
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Status Unit")
        status_counts = st.session_state.units_df['status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Distribusi Status Unit",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_layout(height=300)
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col_right:
        st.subheader("Kapasitas per Rute")
        routes_df = st.session_state.routes_df
        fig_capacity = px.bar(
            routes_df,
            x='name',
            y='required_capacity',
            title="Kebutuhan Kapasitas per Rute",
            color='route_type',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_capacity.update_layout(height=300, xaxis_title="Rute", yaxis_title="Kapasitas")
        st.plotly_chart(fig_capacity, use_container_width=True)
    
    if st.session_state.assignments:
        st.subheader("Penugasan Terkini")

        assignments_data = []
        for a in st.session_state.assignments[:10]:
            # Safely get route and unit data, skip if not found (in case data was deleted)
            route_row = st.session_state.routes_df[st.session_state.routes_df['route_id'] == a.route_id]
            unit_row = st.session_state.units_df[st.session_state.units_df['unit_id'] == a.unit_id]

            if not route_row.empty and not unit_row.empty:
                route = route_row.iloc[0]
                unit = unit_row.iloc[0]
                assignments_data.append({
                    'Jadwal': a.schedule_id,
                    'Unit': unit['name'],
                    'Rute': route['name'],
                    'Berangkat': a.departure_time,
                    'Kembali': a.estimated_return_time,
                    'Skor': f"{a.total_score:.2f}",
                    'Status': a.status
                })
            else:
                # Skip this assignment if route or unit doesn't exist
                continue

        if assignments_data:
            st.dataframe(pd.DataFrame(assignments_data), use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada penugasan valid saat ini.")
    else:
        st.info("Belum ada penugasan. Jalankan optimasi untuk menghasilkan penugasan.")

def render_units_page():
    st.title("Data Unit")
    st.markdown("Kelola data armada unit transportasi")
    
    tab1, tab2, tab3 = st.tabs(["Daftar Unit", "Tambah Unit", "Edit/Hapus Unit"])
    
    with tab1:
        units_display = st.session_state.units_df.copy()
        units_display['allowed_routes'] = units_display['allowed_routes'].apply(
            lambda x: ', '.join(parse_allowed_routes(x))
        )
        
        st.dataframe(
            units_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "unit_id": "ID Unit",
                "name": "Nama Unit",
                "capacity": st.column_config.NumberColumn("Kapasitas", format="%d penumpang"),
                "fuel_efficiency": st.column_config.NumberColumn("Efisiensi BBM", format="%.1f km/L"),
                "operational_cost_per_km": st.column_config.NumberColumn("Biaya/km", format="Rp %,.0f"),
                "status": "Status",
                "home_location": "Lokasi Asal",
                "allowed_routes": "Rute Diizinkan"
            }
        )
        
        st.subheader("Visualisasi Kapasitas Unit")
        fig = px.bar(
            st.session_state.units_df,
            x='name',
            y='capacity',
            color='status',
            title="Kapasitas Unit berdasarkan Status",
            color_discrete_map={'Available': '#2ecc71', 'Maintenance': '#e74c3c'}
        )
        fig.update_layout(xaxis_title="Unit", yaxis_title="Kapasitas (penumpang)")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Tambah Unit Baru")
        
        with st.form("add_unit_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_id = st.text_input("ID Unit", placeholder="U009")
                new_name = st.text_input("Nama Unit", placeholder="Bus Epsilon-01")
                new_capacity = st.number_input("Kapasitas", min_value=10, max_value=100, value=45)
                new_efficiency = st.number_input("Efisiensi BBM (km/L)", min_value=1.0, max_value=10.0, value=4.0)
            
            with col2:
                new_cost = st.number_input("Biaya Operasional/km", min_value=100, max_value=10000, value=2500)
                new_status = st.selectbox("Status", ["Available", "Maintenance"])

                # Get available locations from database
                locations_df = get_locations_df()
                location_options = ["Belum Dipilih"] + locations_df['name'].tolist() if not locations_df.empty else ["Terminal A", "Terminal B", "Terminal C"]
                new_location = st.selectbox("Lokasi Asal", location_options)

                new_routes = st.multiselect(
                    "Rute Diizinkan",
                    st.session_state.routes_df['route_id'].tolist()
                )
            
            if st.form_submit_button("Tambah Unit", type="primary"):
                if new_id and new_name and new_routes:
                    unit_data = {
                        'unit_id': new_id,
                        'name': new_name,
                        'capacity': new_capacity,
                        'fuel_efficiency': new_efficiency,
                        'operational_cost_per_km': new_cost,
                        'status': new_status,
                        'home_location': new_location,
                        'allowed_routes': json.dumps(new_routes)
                    }
                    if add_unit(unit_data):
                        refresh_data()
                        st.success(f"Unit {new_name} berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan unit. ID mungkin sudah ada.")
                else:
                    st.error("Mohon lengkapi semua field yang diperlukan")
    
    with tab3:
        st.subheader("Edit atau Hapus Unit")
        
        if len(st.session_state.units_df) == 0:
            st.info("Tidak ada data unit.")
        else:
            selected_unit_id = st.selectbox(
                "Pilih Unit untuk diedit/dihapus",
                st.session_state.units_df['unit_id'].tolist(),
                format_func=lambda x: f"{x} - {st.session_state.units_df[st.session_state.units_df['unit_id']==x]['name'].values[0]}",
                key="edit_unit_select"
            )
            
            if selected_unit_id:
                unit_idx = st.session_state.units_df[st.session_state.units_df['unit_id'] == selected_unit_id].index[0]
                unit_data = st.session_state.units_df.loc[unit_idx]
                
                with st.form("edit_unit_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Nama Unit", value=unit_data['name'])
                        edit_capacity = st.number_input("Kapasitas", min_value=10, max_value=100, value=int(unit_data['capacity']))
                        edit_efficiency = st.number_input("Efisiensi BBM (km/L)", min_value=1.0, max_value=10.0, value=float(unit_data['fuel_efficiency']))
                    
                    with col2:
                        edit_cost = st.number_input("Biaya Operasional/km", min_value=100, max_value=10000, value=int(unit_data['operational_cost_per_km']))
                        status_options = ["Available", "Maintenance"]
                        edit_status = st.selectbox("Status", status_options, index=status_options.index(unit_data['status']) if unit_data['status'] in status_options else 0)

                        # Get available locations from database
                        locations_df = get_locations_df()
                        location_options = ["Belum Dipilih"] + locations_df['name'].tolist() if not locations_df.empty else ["Terminal A", "Terminal B", "Terminal C"]

                        # Find the index of the current location in the options
                        try:
                            current_location_index = location_options.index(unit_data['home_location'])
                        except ValueError:
                            current_location_index = 0  # Default to "Belum Dipilih"

                        edit_location = st.selectbox("Lokasi Asal", location_options, index=current_location_index)

                        current_routes = parse_allowed_routes(unit_data['allowed_routes'])
                        edit_routes = st.multiselect(
                            "Rute Diizinkan",
                            st.session_state.routes_df['route_id'].tolist(),
                            default=current_routes
                        )
                    
                    if st.form_submit_button("Simpan Perubahan", type="primary"):
                        update_data = {
                            'name': edit_name,
                            'capacity': edit_capacity,
                            'fuel_efficiency': edit_efficiency,
                            'operational_cost_per_km': edit_cost,
                            'status': edit_status,
                            'home_location': edit_location,
                            'allowed_routes': json.dumps(edit_routes)
                        }
                        if update_unit(selected_unit_id, update_data):
                            refresh_data()
                            st.success(f"Unit {edit_name} berhasil diperbarui!")
                            st.rerun()
                        else:
                            st.error("Gagal memperbarui unit.")
                
                st.divider()
                
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("Hapus Unit", type="secondary", use_container_width=True):
                        if delete_unit(selected_unit_id):
                            refresh_data()
                            st.success(f"Unit {unit_data['name']} berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error("Gagal menghapus unit.")

def render_routes_page():
    st.title("Data Rute")
    st.markdown("Kelola data rute perjalanan")
    
    tab1, tab2, tab3 = st.tabs(["Daftar Rute", "Tambah Rute", "Edit/Hapus Rute"])
    
    with tab1:
        st.dataframe(
            st.session_state.routes_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "route_id": "ID Rute",
                "name": "Nama Rute",
                "origin": "Asal",
                "destination": "Tujuan",
                "distance_km": st.column_config.NumberColumn("Jarak", format="%.1f km"),
                "estimated_time_minutes": st.column_config.NumberColumn("Waktu Tempuh", format="%d menit"),
                "route_type": "Tipe Rute",
                "required_capacity": st.column_config.NumberColumn("Kapasitas Min", format="%d penumpang")
            }
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_dist = px.bar(
                st.session_state.routes_df,
                x='name',
                y='distance_km',
                color='route_type',
                title="Jarak Tempuh per Rute"
            )
            fig_dist.update_layout(xaxis_title="Rute", yaxis_title="Jarak (km)")
            st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            fig_time = px.bar(
                st.session_state.routes_df,
                x='name',
                y='estimated_time_minutes',
                color='route_type',
                title="Waktu Tempuh per Rute"
            )
            fig_time.update_layout(xaxis_title="Rute", yaxis_title="Waktu (menit)")
            st.plotly_chart(fig_time, use_container_width=True)
    
    with tab2:
        st.subheader("Tambah Rute Baru")
        
        with st.form("add_route_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_route_id = st.text_input("ID Rute", placeholder="R006")
                new_route_name = st.text_input("Nama Rute", placeholder="Terminal A - Pelabuhan")
                new_origin = st.text_input("Asal", placeholder="Terminal A")
                new_destination = st.text_input("Tujuan", placeholder="Pelabuhan")
            
            with col2:
                new_distance = st.number_input("Jarak (km)", min_value=1.0, max_value=500.0, value=20.0)
                new_time = st.number_input("Waktu Tempuh (menit)", min_value=10, max_value=180, value=40)
                new_type = st.selectbox("Tipe Rute", ["Regular", "Express", "Inter-Terminal", "Tourism"])
                new_req_capacity = st.number_input("Kapasitas Minimum", min_value=10, max_value=60, value=30)
            
            if st.form_submit_button("Tambah Rute", type="primary"):
                if new_route_id and new_route_name and new_origin and new_destination:
                    route_data = {
                        'route_id': new_route_id,
                        'name': new_route_name,
                        'origin': new_origin,
                        'destination': new_destination,
                        'distance_km': new_distance,
                        'estimated_time_minutes': new_time,
                        'route_type': new_type,
                        'required_capacity': new_req_capacity
                    }
                    if add_route(route_data):
                        refresh_data()
                        st.success(f"Rute {new_route_name} berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan rute. ID mungkin sudah ada.")
                else:
                    st.error("Mohon lengkapi semua field yang diperlukan")
    
    with tab3:
        st.subheader("Edit atau Hapus Rute")
        
        if len(st.session_state.routes_df) == 0:
            st.info("Tidak ada data rute.")
        else:
            selected_route_id = st.selectbox(
                "Pilih Rute untuk diedit/dihapus",
                st.session_state.routes_df['route_id'].tolist(),
                format_func=lambda x: f"{x} - {st.session_state.routes_df[st.session_state.routes_df['route_id']==x]['name'].values[0]}",
                key="edit_route_select"
            )
            
            if selected_route_id:
                route_idx = st.session_state.routes_df[st.session_state.routes_df['route_id'] == selected_route_id].index[0]
                route_data = st.session_state.routes_df.loc[route_idx]
                
                with st.form("edit_route_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_route_name = st.text_input("Nama Rute", value=route_data['name'])
                        edit_origin = st.text_input("Asal", value=route_data['origin'])
                        edit_destination = st.text_input("Tujuan", value=route_data['destination'])
                    
                    with col2:
                        edit_distance = st.number_input("Jarak (km)", min_value=1.0, max_value=500.0, value=float(route_data['distance_km']))
                        edit_time = st.number_input("Waktu Tempuh (menit)", min_value=10, max_value=180, value=int(route_data['estimated_time_minutes']))
                        type_options = ["Regular", "Express", "Inter-Terminal", "Tourism"]
                        edit_type = st.selectbox("Tipe Rute", type_options, index=type_options.index(route_data['route_type']) if route_data['route_type'] in type_options else 0)
                        edit_req_capacity = st.number_input("Kapasitas Minimum", min_value=10, max_value=60, value=int(route_data['required_capacity']))
                    
                    if st.form_submit_button("Simpan Perubahan", type="primary"):
                        update_data = {
                            'name': edit_route_name,
                            'origin': edit_origin,
                            'destination': edit_destination,
                            'distance_km': edit_distance,
                            'estimated_time_minutes': edit_time,
                            'route_type': edit_type,
                            'required_capacity': edit_req_capacity
                        }
                        if update_route(selected_route_id, update_data):
                            refresh_data()
                            st.success(f"Rute {edit_route_name} berhasil diperbarui!")
                            st.rerun()
                        else:
                            st.error("Gagal memperbarui rute.")
                
                st.divider()
                
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("Hapus Rute", type="secondary", use_container_width=True):
                        if delete_route(selected_route_id):
                            refresh_data()
                            st.success(f"Rute {route_data['name']} berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error("Gagal menghapus rute.")

def render_schedules_page():
    st.title("Data Jadwal")
    st.markdown("Kelola jadwal keberangkatan harian")
    
    tab1, tab2, tab3 = st.tabs(["Daftar Jadwal", "Tambah Jadwal", "Edit/Hapus Jadwal"])
    
    with tab1:
        schedules_display = st.session_state.schedules_df.copy()
        schedules_display['operating_days'] = schedules_display['operating_days'].apply(
            lambda x: ', '.join(parse_operating_days(x))
        )
        
        schedules_display = schedules_display.merge(
            st.session_state.routes_df[['route_id', 'name']],
            on='route_id',
            how='left'
        ).rename(columns={'name': 'route_name'})
        
        st.dataframe(
            schedules_display[['schedule_id', 'route_name', 'departure_time', 'operating_days', 'priority']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "schedule_id": "ID Jadwal",
                "route_name": "Rute",
                "departure_time": "Jam Berangkat",
                "operating_days": "Hari Operasi",
                "priority": st.column_config.NumberColumn("Prioritas", format="%d")
            }
        )
        
        st.subheader("Distribusi Jadwal")
        
        route_schedule_count = schedules_display.groupby('route_name').size().reset_index(name='count')
        fig = px.pie(
            route_schedule_count,
            values='count',
            names='route_name',
            title="Jumlah Jadwal per Rute"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Tambah Jadwal Baru")
        
        with st.form("add_schedule_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_sched_id = st.text_input("ID Jadwal", placeholder="S015")
                new_sched_route = st.selectbox(
                    "Rute",
                    st.session_state.routes_df['route_id'].tolist(),
                    format_func=lambda x: f"{x} - {st.session_state.routes_df[st.session_state.routes_df['route_id']==x]['name'].values[0]}"
                )
                new_departure = st.time_input("Jam Keberangkatan")
            
            with col2:
                new_days = st.multiselect(
                    "Hari Operasi",
                    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    default=["Mon", "Tue", "Wed", "Thu", "Fri"]
                )
                new_priority = st.selectbox("Prioritas", [1, 2, 3], help="1 = Tertinggi, 3 = Terendah")
            
            if st.form_submit_button("Tambah Jadwal", type="primary"):
                if new_sched_id and new_sched_route and new_days:
                    schedule_data = {
                        'schedule_id': new_sched_id,
                        'route_id': new_sched_route,
                        'departure_time': new_departure.strftime("%H:%M"),
                        'operating_days': json.dumps(new_days),
                        'priority': new_priority
                    }
                    if add_schedule(schedule_data):
                        refresh_data()
                        st.success(f"Jadwal {new_sched_id} berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan jadwal. ID mungkin sudah ada.")
                else:
                    st.error("Mohon lengkapi semua field yang diperlukan")
    
    with tab3:
        st.subheader("Edit atau Hapus Jadwal")
        
        if len(st.session_state.schedules_df) == 0:
            st.info("Tidak ada data jadwal.")
        else:
            schedules_with_route = st.session_state.schedules_df.merge(
                st.session_state.routes_df[['route_id', 'name']],
                on='route_id',
                how='left'
            )
            
            selected_schedule_id = st.selectbox(
                "Pilih Jadwal untuk diedit/dihapus",
                st.session_state.schedules_df['schedule_id'].tolist(),
                format_func=lambda x: f"{x} - {schedules_with_route[schedules_with_route['schedule_id']==x]['name'].values[0]} ({st.session_state.schedules_df[st.session_state.schedules_df['schedule_id']==x]['departure_time'].values[0]})",
                key="edit_schedule_select"
            )
            
            if selected_schedule_id:
                sched_idx = st.session_state.schedules_df[st.session_state.schedules_df['schedule_id'] == selected_schedule_id].index[0]
                sched_data = st.session_state.schedules_df.loc[sched_idx]
                
                with st.form("edit_schedule_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        route_ids = st.session_state.routes_df['route_id'].tolist()
                        current_route_idx = route_ids.index(sched_data['route_id']) if sched_data['route_id'] in route_ids else 0
                        edit_sched_route = st.selectbox(
                            "Rute",
                            route_ids,
                            index=current_route_idx,
                            format_func=lambda x: f"{x} - {st.session_state.routes_df[st.session_state.routes_df['route_id']==x]['name'].values[0]}"
                        )
                        
                        current_time = datetime.strptime(sched_data['departure_time'], "%H:%M").time()
                        edit_departure = st.time_input("Jam Keberangkatan", value=current_time)
                    
                    with col2:
                        current_days = parse_operating_days(sched_data['operating_days'])
                        edit_days = st.multiselect(
                            "Hari Operasi",
                            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                            default=current_days
                        )
                        priority_options = [1, 2, 3]
                        current_priority_idx = priority_options.index(sched_data['priority']) if sched_data['priority'] in priority_options else 0
                        edit_priority = st.selectbox("Prioritas", priority_options, index=current_priority_idx, help="1 = Tertinggi, 3 = Terendah")
                    
                    if st.form_submit_button("Simpan Perubahan", type="primary"):
                        update_data = {
                            'route_id': edit_sched_route,
                            'departure_time': edit_departure.strftime("%H:%M"),
                            'operating_days': json.dumps(edit_days),
                            'priority': edit_priority
                        }
                        if update_schedule(selected_schedule_id, update_data):
                            refresh_data()
                            st.success(f"Jadwal {selected_schedule_id} berhasil diperbarui!")
                            st.rerun()
                        else:
                            st.error("Gagal memperbarui jadwal.")
                
                st.divider()
                
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("Hapus Jadwal", type="secondary", use_container_width=True):
                        if delete_schedule(selected_schedule_id):
                            refresh_data()
                            st.success(f"Jadwal {selected_schedule_id} berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error("Gagal menghapus jadwal.")

def render_optimization_page():
    st.title("Optimasi Penugasan")
    st.markdown("Jalankan algoritma optimasi untuk menugaskan unit ke jadwal rute")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        target_date = st.date_input(
            "Tanggal Target Optimasi",
            value=datetime.now().date(),
            help="Pilih tanggal untuk menjalankan optimasi penugasan"
        )

        target_datetime = datetime.combine(target_date, datetime.min.time())
        day_name = get_day_name(target_datetime)

        active_schedules_count = 0
        for _, schedule in st.session_state.schedules_df.iterrows():
            operating_days = parse_operating_days(schedule['operating_days'])
            if day_name in operating_days:
                active_schedules_count += 1

        st.info(f"Hari: {day_name} | Jadwal aktif: {active_schedules_count}")

    with col2:
        if st.button("Jalankan Optimasi", type="primary", use_container_width=True):
            with st.spinner("Menjalankan algoritma optimasi..."):
                engine = OptimizationEngine(st.session_state.params)

                assignments, unassigned = engine.optimize_assignments(
                    st.session_state.units_df,
                    st.session_state.routes_df,
                    st.session_state.schedules_df,
                    target_datetime
                )

                metrics = engine.calculate_metrics(
                    assignments,
                    st.session_state.units_df,
                    st.session_state.routes_df,
                    st.session_state.schedules_df,
                    target_datetime
                )

                st.session_state.assignments = assignments
                st.session_state.unassigned = unassigned
                st.session_state.metrics = metrics
                st.session_state.last_optimization_date = target_datetime

                save_assignments(assignments, target_datetime)
                params_dict = {
                    'turnaround': st.session_state.params.turnaround_time_minutes,
                    'rest_time': st.session_state.params.minimum_rest_time_minutes,
                    'fuel_price': st.session_state.params.fuel_price_per_liter
                }
                save_optimization_run(metrics, target_datetime, params_dict)

                alerts_count = check_thresholds(metrics, st.session_state.thresholds)
                if alerts_count > 0:
                    st.warning(f"{alerts_count} alert baru terdeteksi. Periksa halaman Monitoring.")

            st.success(f"Optimasi selesai! {len(assignments)} penugasan berhasil dibuat dan disimpan.")
            st.rerun()

    st.divider()

    if st.session_state.assignments:
        st.subheader("Hasil Penugasan")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Jadwal Terlayani", st.session_state.metrics.get('assigned_count', 0))
        with col2:
            st.metric("Tingkat Cakupan", f"{st.session_state.metrics.get('coverage_rate', 0):.1f}%")
        with col3:
            st.metric("Total Biaya BBM", f"Rp {st.session_state.metrics.get('total_fuel_cost', 0):,.0f}")
        with col4:
            st.metric("Skor Rata-rata", f"{st.session_state.metrics.get('average_score', 0):.2f}")

        # Additional metrics including idle time
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            avg_idle_time = st.session_state.metrics.get('average_idle_time_minutes', 0)
            avg_idle_hours = avg_idle_time / 60  # Convert to hours
            st.metric("Rata-rata Idle Time", f"{avg_idle_hours:.1f} jam")
        with col6:
            st.metric("Unit Digunakan", st.session_state.metrics.get('units_used', 0))
        with col7:
            total_idle_time = st.session_state.metrics.get('total_idle_time_minutes', 0)
            total_idle_hours = total_idle_time / 60
            st.metric("Total Idle Time", f"{total_idle_hours:.1f} jam")
        with col8:
            st.metric("Unit Tersedia", st.session_state.metrics.get('units_available', 0))
        
        st.subheader("Detail Penugasan")
        
        assignments_data = []
        for a in st.session_state.assignments:
            # Safely get route and unit data, skip if not found (in case data was deleted)
            route_row = st.session_state.routes_df[st.session_state.routes_df['route_id'] == a.route_id]
            unit_row = st.session_state.units_df[st.session_state.units_df['unit_id'] == a.unit_id]

            if not route_row.empty and not unit_row.empty:
                route = route_row.iloc[0]
                unit = unit_row.iloc[0]

                assignments_data.append({
                    'Jadwal': a.schedule_id,
                    'Rute': route['name'],
                    'Unit': unit['name'],
                    'Kapasitas': unit['capacity'],
                    'Berangkat': a.departure_time,
                    'Kembali': a.estimated_return_time,
                    'Biaya BBM': f"Rp {a.fuel_cost:,.0f}",
                    'Skor': a.total_score,
                    'Alasan': a.assignment_reason
                })
            else:
                # Skip this assignment if route or unit doesn't exist
                continue
        
        st.dataframe(
            pd.DataFrame(assignments_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Skor": st.column_config.ProgressColumn(
                    "Skor",
                    format="%.2f",
                    min_value=0,
                    max_value=1
                )
            }
        )
        
        if st.session_state.unassigned:
            st.subheader("Jadwal Tidak Terlayani")
            st.warning(f"{len(st.session_state.unassigned)} jadwal tidak dapat ditugaskan")
            
            unassigned_data = []
            for u in st.session_state.unassigned:
                # Safely get route data, skip if not found (in case data was deleted)
                route_row = st.session_state.routes_df[st.session_state.routes_df['route_id'] == u['route_id']]

                if not route_row.empty:
                    route = route_row.iloc[0]
                    unassigned_data.append({
                        'Jadwal': u['schedule_id'],
                        'Rute': route['name'],
                        'Jam Berangkat': u['departure_time'],
                        'Alasan': '; '.join(u['reasons'])
                    })
                else:
                    # Skip this unassigned if route doesn't exist
                    continue
            
            st.dataframe(pd.DataFrame(unassigned_data), use_container_width=True, hide_index=True)
        
        st.subheader("Visualisasi Penugasan")
        
        fig = go.Figure()
        
        unit_assignments = {}
        for a in st.session_state.assignments:
            if a.unit_id not in unit_assignments:
                unit_assignments[a.unit_id] = []
            unit_assignments[a.unit_id].append(a)
        
        for unit_id, assignments in unit_assignments.items():
            # Safely get unit data, skip if not found
            unit_row = st.session_state.units_df[st.session_state.units_df['unit_id'] == unit_id]
            if unit_row.empty:
                continue
            unit = unit_row.iloc[0]

            for a in assignments:
                # Safely get route data, skip if not found
                route_row = st.session_state.routes_df[st.session_state.routes_df['route_id'] == a.route_id]
                if route_row.empty:
                    continue
                route = route_row.iloc[0]

                start_minutes = time_str_to_minutes(a.departure_time)
                end_minutes = time_str_to_minutes(a.estimated_return_time)

                fig.add_trace(go.Bar(
                    name=route['name'],
                    y=[unit['name']],
                    x=[end_minutes - start_minutes],
                    base=[start_minutes],
                    orientation='h',
                    text=f"{a.departure_time}-{a.estimated_return_time}",
                    textposition='inside',
                    hovertemplate=f"<b>{route['name']}</b><br>Unit: {unit['name']}<br>Waktu: {a.departure_time} - {a.estimated_return_time}<extra></extra>",
                    showlegend=False
                ))
        
        fig.update_layout(
            title="Timeline Penugasan Unit",
            xaxis_title="Waktu (menit dari 00:00)",
            yaxis_title="Unit",
            barmode='overlay',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("Klik 'Jalankan Optimasi' untuk menghasilkan penugasan unit ke jadwal.")

def render_reports_page():
    st.title("Laporan & Analitik")
    st.markdown("Analisis mendalam dan laporan performa operasional")
    
    if not st.session_state.assignments:
        st.warning("Belum ada data penugasan. Jalankan optimasi terlebih dahulu.")
        return
    
    tab1, tab2, tab3 = st.tabs(["Ringkasan Harian", "Analisis Unit", "Analisis Rute"])
    
    with tab1:
        st.subheader("Ringkasan Penugasan Harian")
        
        metrics = st.session_state.metrics
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Jadwal", metrics.get('total_schedules', 0))
            st.metric("Jadwal Terlayani", metrics.get('assigned_count', 0))
        with col2:
            st.metric("Tingkat Cakupan", f"{metrics.get('coverage_rate', 0):.1f}%")
            st.metric("Tingkat Utilisasi", f"{metrics.get('utilization_rate', 0):.1f}%")
        with col3:
            st.metric("Total Jarak", f"{metrics.get('total_distance', 0):,.0f} km")
            st.metric("Total Biaya BBM", f"Rp {metrics.get('total_fuel_cost', 0):,.0f}")

        # Add idle time metrics if available
        if 'average_idle_time_minutes' in metrics:
            st.divider()
            st.subheader("Metric Idle Time")
            col_idle1, col_idle2, col_idle3 = st.columns(3)
            with col_idle1:
                avg_idle_hours = metrics.get('average_idle_time_minutes', 0) / 60
                st.metric("Rata-rata Idle Time", f"{avg_idle_hours:.1f} jam")
            with col_idle2:
                total_idle_hours = metrics.get('total_idle_time_minutes', 0) / 60
                st.metric("Total Idle Time", f"{total_idle_hours:.1f} jam")
            with col_idle3:
                avg_score = metrics.get('average_score', 0)
                st.metric("Skor Rata-rata", f"{avg_score:.2f}")
        
        st.divider()
        
        score_data = []
        for a in st.session_state.assignments:
            score_data.append({
                'Jadwal': a.schedule_id,
                'Skor': a.total_score
            })
        
        fig_scores = px.histogram(
            pd.DataFrame(score_data),
            x='Skor',
            nbins=10,
            title="Distribusi Skor Penugasan"
        )
        fig_scores.update_layout(xaxis_title="Skor", yaxis_title="Jumlah Penugasan")
        st.plotly_chart(fig_scores, use_container_width=True)
    
    with tab2:
        st.subheader("Analisis Performa Unit")
        
        unit_stats = []
        for _, unit in st.session_state.units_df.iterrows():
            unit_assignments = [a for a in st.session_state.assignments if a.unit_id == unit['unit_id']]
            
            total_fuel = sum(a.fuel_cost for a in unit_assignments)
            avg_score = np.mean([a.total_score for a in unit_assignments]) if unit_assignments else 0
            
            unit_stats.append({
                'Unit': unit['name'],
                'Status': unit['status'],
                'Kapasitas': unit['capacity'],
                'Penugasan': len(unit_assignments),
                'Total BBM': total_fuel,
                'Skor Rata-rata': avg_score
            })
        
        unit_stats_df = pd.DataFrame(unit_stats)
        
        st.dataframe(
            unit_stats_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total BBM": st.column_config.NumberColumn("Total BBM", format="Rp %,.0f"),
                "Skor Rata-rata": st.column_config.ProgressColumn(
                    "Skor Rata-rata",
                    format="%.2f",
                    min_value=0,
                    max_value=1
                )
            }
        )
        
        fig_unit = px.bar(
            unit_stats_df,
            x='Unit',
            y='Penugasan',
            color='Status',
            title="Jumlah Penugasan per Unit"
        )
        st.plotly_chart(fig_unit, use_container_width=True)

        # Add Idle Time Analysis
        if 'idle_times' in st.session_state.metrics:
            st.subheader("Analisis Waktu Idle Unit")

            idle_data = []
            for unit_id, idle_minutes in st.session_state.metrics['idle_times'].items():
                unit_row = st.session_state.units_df[st.session_state.units_df['unit_id'] == unit_id]
                if not unit_row.empty:
                    unit_name = unit_row.iloc[0]['name']
                    idle_hours = idle_minutes / 60
                    idle_data.append({
                        'Unit': unit_name,
                        'Unit ID': unit_id,
                        'Idle Time (jam)': idle_hours,
                        'Waktu Kerja (jam)': (st.session_state.params.max_working_hours_per_day * 60 - idle_minutes) / 60,
                        'Status': unit_row.iloc[0]['status']
                    })

            if idle_data:
                idle_df = pd.DataFrame(idle_data)

                # Metric cards for idle time
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_idle = idle_df['Idle Time (jam)'].mean()
                    st.metric("Rata-rata Idle Time", f"{avg_idle:.1f} jam")
                with col2:
                    min_idle = idle_df['Idle Time (jam)'].min()
                    st.metric("Idle Time Minimum", f"{min_idle:.1f} jam")
                with col3:
                    max_idle = idle_df['Idle Time (jam)'].max()
                    st.metric("Idle Time Maksimum", f"{max_idle:.1f} jam")

                st.dataframe(
                    idle_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Idle Time (jam)": st.column_config.NumberColumn("Idle Time (jam)", format="%.2f jam"),
                        "Waktu Kerja (jam)": st.column_config.NumberColumn("Waktu Kerja (jam)", format="%.2f jam")
                    }
                )

                fig_idle = px.bar(
                    idle_df,
                    x='Unit',
                    y='Idle Time (jam)',
                    color='Status',
                    title="Waktu Idle per Unit",
                    color_discrete_map={'Available': '#2ecc71', 'Maintenance': '#e74c3c'}
                )
                fig_idle.update_layout(xaxis_title="Unit", yaxis_title="Idle Time (jam)")
                st.plotly_chart(fig_idle, use_container_width=True)

                # Utilization vs Idle Time comparison
                fig_util_idle = px.scatter(
                    idle_df,
                    x='Waktu Kerja (jam)',
                    y='Idle Time (jam)',
                    color='Status',
                    title="Hubungan Waktu Kerja vs Idle Time",
                    hover_data=['Unit', 'Unit ID']
                )
                fig_util_idle.update_layout(
                    xaxis_title="Waktu Kerja (jam)",
                    yaxis_title="Idle Time (jam)"
                )
                st.plotly_chart(fig_util_idle, use_container_width=True)
    
    with tab3:
        st.subheader("Analisis Performa Rute")
        
        route_stats = []
        for _, route in st.session_state.routes_df.iterrows():
            route_assignments = [a for a in st.session_state.assignments if a.route_id == route['route_id']]
            
            total_fuel = sum(a.fuel_cost for a in route_assignments)
            avg_score = np.mean([a.total_score for a in route_assignments]) if route_assignments else 0
            
            route_stats.append({
                'Rute': route['name'],
                'Tipe': route['route_type'],
                'Jarak': route['distance_km'],
                'Jadwal Terlayani': len(route_assignments),
                'Total BBM': total_fuel,
                'Skor Rata-rata': avg_score
            })
        
        route_stats_df = pd.DataFrame(route_stats)
        
        st.dataframe(
            route_stats_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Jarak": st.column_config.NumberColumn("Jarak", format="%.1f km"),
                "Total BBM": st.column_config.NumberColumn("Total BBM", format="Rp %,.0f"),
                "Skor Rata-rata": st.column_config.ProgressColumn(
                    "Skor Rata-rata",
                    format="%.2f",
                    min_value=0,
                    max_value=1
                )
            }
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_route_assign = px.pie(
                route_stats_df,
                values='Jadwal Terlayani',
                names='Rute',
                title="Distribusi Penugasan per Rute"
            )
            st.plotly_chart(fig_route_assign, use_container_width=True)
        
        with col2:
            fig_route_cost = px.bar(
                route_stats_df,
                x='Rute',
                y='Total BBM',
                color='Tipe',
                title="Total Biaya BBM per Rute"
            )
            st.plotly_chart(fig_route_cost, use_container_width=True)

def render_settings_page():
    st.title("Pengaturan")
    st.markdown("Konfigurasi parameter operasional sistem")
    
    st.subheader("Parameter Operasional")
    
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            turnaround = st.number_input(
                "Waktu Turnaround (menit)",
                min_value=10,
                max_value=120,
                value=st.session_state.params.turnaround_time_minutes,
                help="Waktu persiapan unit di terminal"
            )
            
            rest_time = st.number_input(
                "Waktu Istirahat Minimum (menit)",
                min_value=30,
                max_value=180,
                value=st.session_state.params.minimum_rest_time_minutes,
                help="Jeda minimum antara penugasan"
            )
        
        with col2:
            fuel_price = st.number_input(
                "Harga BBM (Rp/Liter)",
                min_value=5000,
                max_value=25000,
                value=int(st.session_state.params.fuel_price_per_liter),
                step=500,
                help="Harga bahan bakar per liter"
            )
            
            max_hours = st.number_input(
                "Jam Kerja Maksimum (jam)",
                min_value=6,
                max_value=16,
                value=st.session_state.params.max_working_hours_per_day,
                help="Batas jam kerja harian per unit"
            )
        
        if st.form_submit_button("Simpan Pengaturan", type="primary"):
            st.session_state.params = OperationalParameters(
                turnaround_time_minutes=turnaround,
                minimum_rest_time_minutes=rest_time,
                fuel_price_per_liter=float(fuel_price),
                max_working_hours_per_day=max_hours
            )
            st.success("Pengaturan berhasil disimpan!")
    
    st.divider()
    
    st.subheader("Bobot Scoring")
    st.markdown("Sesuaikan bobot untuk algoritma optimasi")
    
    engine = OptimizationEngine()
    
    col1, col2 = st.columns(2)
    with col1:
        w_capacity = st.slider("Bobot Kapasitas", 0.0, 1.0, engine.weights['capacity'], 0.05)
        w_distance = st.slider("Bobot Jarak", 0.0, 1.0, engine.weights['distance'], 0.05)
    with col2:
        w_availability = st.slider("Bobot Ketersediaan", 0.0, 1.0, engine.weights['availability'], 0.05)
        w_cost = st.slider("Bobot Biaya", 0.0, 1.0, engine.weights['cost'], 0.05)
    
    total_weight = w_capacity + w_distance + w_availability + w_cost
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"Total bobot: {total_weight:.2f}. Idealnya harus = 1.0 untuk hasil optimal.")
    else:
        st.success(f"Total bobot: {total_weight:.2f}")
    
    st.divider()
    
    st.subheader("Reset Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Reset Data Unit", type="secondary"):
            success, count = delete_all_units()
            if success:
                # Clear session state and refresh data
                st.session_state.units_df = get_units_df()  # Refresh from DB
                st.session_state.assignments = []  # Clear any cached assignments
                st.session_state.unassigned = []   # Clear unassigned list
                st.success(f"Data unit berhasil dihapus! Jumlah unit dihapus: {count}")
                st.rerun()
            else:
                st.error("Gagal menghapus data unit.")

    with col2:
        if st.button("Reset Data Rute", type="secondary"):
            success, count = delete_all_routes()
            if success:
                # Clear session state and refresh data
                st.session_state.routes_df = get_routes_df()  # Refresh from DB
                st.session_state.assignments = []  # Clear any cached assignments
                st.session_state.unassigned = []   # Clear unassigned list
                st.success(f"Data rute berhasil dihapus! Jumlah rute dihapus: {count}")
                st.rerun()
            else:
                st.error("Gagal menghapus data rute.")

    with col3:
        if st.button("Reset Data Jadwal", type="secondary"):
            success, count = delete_all_schedules()
            if success:
                # Clear session state and refresh data
                st.session_state.schedules_df = get_schedules_df()  # Refresh from DB
                st.session_state.assignments = []  # Clear any cached assignments
                st.session_state.unassigned = []   # Clear unassigned list
                st.success(f"Data jadwal berhasil dihapus! Jumlah jadwal dihapus: {count}")
                st.rerun()
            else:
                st.error("Gagal menghapus data jadwal.")

    st.divider()

    st.subheader("Reset Semua Data")
    if st.button("Hapus Semua Data", type="secondary", help="Hapus semua data unit, rute, dan jadwal sekaligus"):
        success, counts = delete_all_data()
        if success:
            # Clear all session state data
            st.session_state.units_df = get_units_df()      # Refresh from DB (should be empty now)
            st.session_state.routes_df = get_routes_df()    # Refresh from DB (should be empty now)
            st.session_state.schedules_df = get_schedules_df()  # Refresh from DB (should be empty now)
            st.session_state.assignments = []               # Clear assignments
            st.session_state.unassigned = []                # Clear unassigned
            st.session_state.metrics = {}                   # Clear metrics
            st.session_state.last_optimization_date = None  # Clear last optimization date
            st.success(f"Semua data berhasil dihapus! Unit: {counts['units']}, Rute: {counts['routes']}, Jadwal: {counts['schedules']}")
            st.rerun()
        else:
            st.error("Gagal menghapus semua data.")

    st.divider()

    st.subheader("Reset ke Data Default")
    if st.button("Reset ke Data Default", type="primary", help="Reset semua data ke data sample awal"):
        success = reset_to_default_data()
        if success:
            # Clear all session state data and refresh from DB
            st.session_state.units_df = get_units_df()
            st.session_state.routes_df = get_routes_df()
            st.session_state.schedules_df = get_schedules_df()
            st.session_state.assignments = []
            st.session_state.unassigned = []
            st.session_state.metrics = {}
            st.session_state.last_optimization_date = None
            st.success("Semua data berhasil direset ke data default!")
            st.rerun()
        else:
            st.error("Gagal mereset data ke default.")

def render_monitoring_page():
    st.title("Monitoring & Alert")
    st.markdown("Pantau status operasional dan kelola alert sistem")
    
    tab1, tab2, tab3 = st.tabs(["Alert Aktif", "Riwayat Optimasi", "Threshold Settings"])
    
    with tab1:
        st.subheader("Alert Aktif")
        
        alerts_df = get_alerts(include_resolved=False)
        
        if len(alerts_df) == 0:
            st.success("Tidak ada alert aktif saat ini.")
        else:
            for idx, alert in alerts_df.iterrows():
                severity_color = {"warning": "orange", "info": "blue", "critical": "red"}.get(alert['severity'], "gray")
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{alert['alert_type']}** - {alert['message']}")
                        st.caption(f"Dibuat: {alert['created_at']}")
                    with col2:
                        st.markdown(f":{severity_color}[{alert['severity'].upper()}]")
                    with col3:
                        if st.button("Resolve", key=f"resolve_{alert['id']}"):
                            if resolve_alert(alert['id']):
                                st.success("Alert resolved!")
                                st.rerun()
                    st.divider()
        
        st.subheader("Semua Alert")
        all_alerts = get_alerts(include_resolved=True)
        if len(all_alerts) > 0:
            st.dataframe(
                all_alerts,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn("Waktu", format="DD/MM/YYYY HH:mm"),
                    "is_resolved": st.column_config.CheckboxColumn("Resolved")
                }
            )
    
    with tab2:
        st.subheader("Riwayat Optimasi")
        
        history_df = get_optimization_history()
        
        if len(history_df) == 0:
            st.info("Belum ada riwayat optimasi.")
        else:
            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "run_date": st.column_config.DatetimeColumn("Tanggal Run", format="DD/MM/YYYY HH:mm"),
                    "target_date": st.column_config.DatetimeColumn("Target", format="DD/MM/YYYY"),
                    "coverage_rate": st.column_config.ProgressColumn("Coverage", format="%.1f%%", min_value=0, max_value=100),
                    "utilization_rate": st.column_config.ProgressColumn("Utilisasi", format="%.1f%%", min_value=0, max_value=100),
                    "total_fuel_cost": st.column_config.NumberColumn("Biaya BBM", format="Rp %,.0f"),
                    "average_score": st.column_config.NumberColumn("Skor Avg", format="%.2f")
                }
            )
            
            if len(history_df) > 1:
                st.subheader("Trend Performa")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=history_df['run_date'], y=history_df['coverage_rate'], 
                                         mode='lines+markers', name='Coverage Rate'))
                fig.add_trace(go.Scatter(x=history_df['run_date'], y=history_df['utilization_rate'], 
                                         mode='lines+markers', name='Utilization Rate'))
                fig.update_layout(title="Trend Coverage & Utilization", xaxis_title="Tanggal", yaxis_title="Persentase (%)")
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Threshold Settings")
        st.markdown("Konfigurasi batas yang memicu alert otomatis")
        
        with st.form("threshold_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                min_coverage = st.number_input(
                    "Minimum Coverage Rate (%)",
                    min_value=50, max_value=100,
                    value=st.session_state.thresholds.get('min_coverage_rate', 80),
                    help="Alert jika coverage di bawah nilai ini"
                )
                
                min_utilization = st.number_input(
                    "Minimum Utilization Rate (%)",
                    min_value=30, max_value=100,
                    value=st.session_state.thresholds.get('min_utilization_rate', 60),
                    help="Alert jika utilisasi di bawah nilai ini"
                )
            
            with col2:
                min_score = st.number_input(
                    "Minimum Average Score",
                    min_value=0.3, max_value=1.0,
                    value=st.session_state.thresholds.get('min_avg_score', 0.6),
                    step=0.05,
                    help="Alert jika skor rata-rata di bawah nilai ini"
                )
            
            if st.form_submit_button("Simpan Threshold", type="primary"):
                st.session_state.thresholds = {
                    'min_coverage_rate': min_coverage,
                    'min_utilization_rate': min_utilization,
                    'min_avg_score': min_score
                }
                st.success("Threshold berhasil disimpan!")

def render_scenarios_page():
    st.title("Analisis Skenario")
    st.markdown("Bandingkan berbagai strategi penugasan dengan analisis what-if")
    
    tab1, tab2 = st.tabs(["Buat Skenario", "Perbandingan Skenario"])
    
    with tab1:
        st.subheader("Buat Skenario Baru")
        
        with st.form("scenario_form"):
            scenario_name = st.text_input("Nama Skenario", placeholder="Skenario Efisiensi BBM")
            scenario_desc = st.text_area("Deskripsi", placeholder="Fokus pada minimasi biaya BBM...")
            
            st.markdown("**Parameter Skenario:**")
            col1, col2 = st.columns(2)
            
            with col1:
                s_turnaround = st.number_input("Waktu Turnaround (menit)", min_value=10, max_value=120, value=30)
                s_rest_time = st.number_input("Waktu Istirahat (menit)", min_value=30, max_value=180, value=60)
            
            with col2:
                s_fuel_price = st.number_input("Harga BBM (Rp/L)", min_value=5000, max_value=25000, value=12500)
            
            st.markdown("**Bobot Scoring:**")
            col1, col2 = st.columns(2)
            with col1:
                s_w_capacity = st.slider("Bobot Kapasitas", 0.0, 1.0, 0.25, 0.05, key="s_cap")
                s_w_distance = st.slider("Bobot Jarak", 0.0, 1.0, 0.20, 0.05, key="s_dist")
            with col2:
                s_w_availability = st.slider("Bobot Ketersediaan", 0.0, 1.0, 0.30, 0.05, key="s_avail")
                s_w_cost = st.slider("Bobot Biaya", 0.0, 1.0, 0.25, 0.05, key="s_cost")
            
            is_baseline = st.checkbox("Jadikan sebagai baseline")
            
            if st.form_submit_button("Jalankan & Simpan Skenario", type="primary"):
                if scenario_name:
                    scenario_params = OperationalParameters(
                        turnaround_time_minutes=s_turnaround,
                        minimum_rest_time_minutes=s_rest_time,
                        fuel_price_per_liter=float(s_fuel_price)
                    )
                    
                    engine = OptimizationEngine(scenario_params)
                    engine.weights = {
                        'capacity': s_w_capacity,
                        'distance': s_w_distance,
                        'availability': s_w_availability,
                        'cost': s_w_cost
                    }
                    
                    target_date = datetime.now()
                    assignments, unassigned = engine.optimize_assignments(
                        st.session_state.units_df,
                        st.session_state.routes_df,
                        st.session_state.schedules_df,
                        target_date
                    )
                    
                    metrics = engine.calculate_metrics(
                        assignments,
                        st.session_state.units_df,
                        st.session_state.routes_df,
                        st.session_state.schedules_df,
                        target_date
                    )
                    
                    params = {
                        'turnaround': s_turnaround,
                        'rest_time': s_rest_time,
                        'fuel_price': s_fuel_price,
                        'weights': {
                            'capacity': s_w_capacity,
                            'distance': s_w_distance,
                            'availability': s_w_availability,
                            'cost': s_w_cost
                        }
                    }
                    
                    scenario_id = save_scenario(scenario_name, scenario_desc, params, metrics, is_baseline)
                    if scenario_id:
                        st.success(f"Skenario '{scenario_name}' berhasil dibuat!")
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan skenario.")
                else:
                    st.error("Nama skenario harus diisi.")
    
    with tab2:
        st.subheader("Perbandingan Skenario")
        
        scenarios = get_scenarios()
        
        if not scenarios:
            st.info("Belum ada skenario. Buat skenario baru di tab 'Buat Skenario'.")
        else:
            comparison_data = []
            for s in scenarios:
                results = s['results']
                comparison_data.append({
                    'Nama': s['name'],
                    'Baseline': 'Ya' if s['is_baseline'] else 'Tidak',
                    'Coverage (%)': results.get('coverage_rate', 0),
                    'Utilisasi (%)': results.get('utilization_rate', 0),
                    'Biaya BBM': results.get('total_fuel_cost', 0),
                    'Skor Avg': results.get('average_score', 0),
                    'Dibuat': s['created_at']
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Coverage (%)": st.column_config.ProgressColumn("Coverage", format="%.1f%%", min_value=0, max_value=100),
                    "Utilisasi (%)": st.column_config.ProgressColumn("Utilisasi", format="%.1f%%", min_value=0, max_value=100),
                    "Biaya BBM": st.column_config.NumberColumn("Biaya BBM", format="Rp %,.0f"),
                    "Skor Avg": st.column_config.NumberColumn("Skor", format="%.2f")
                }
            )
            
            if len(comparison_df) > 1:
                st.subheader("Visualisasi Perbandingan")
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='Coverage', x=comparison_df['Nama'], y=comparison_df['Coverage (%)']))
                fig.add_trace(go.Bar(name='Utilisasi', x=comparison_df['Nama'], y=comparison_df['Utilisasi (%)']))
                fig.update_layout(barmode='group', title="Perbandingan Coverage & Utilisasi")
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = px.bar(comparison_df, x='Nama', y='Biaya BBM', title="Perbandingan Biaya BBM")
                st.plotly_chart(fig2, use_container_width=True)

def render_idle_time_page():
    st.title("Analisis Idle Time")
    st.markdown("Analisis waktu idle/unit istirahat kendaraan untuk optimalisasi penggunaan armada")

    if not st.session_state.assignments:
        st.warning("Belum ada data penugasan. Jalankan optimasi terlebih dahulu untuk melihat analisis idle time.")
        return

    if 'idle_times' not in st.session_state.metrics:
        st.warning("Data idle time belum tersedia. Jalankan optimasi kembali.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_idle_minutes = st.session_state.metrics.get('average_idle_time_minutes', 0)
        avg_idle_hours = avg_idle_minutes / 60
        st.metric("Rata-rata Idle Time", f"{avg_idle_hours:.1f} jam")

    with col2:
        total_idle_minutes = st.session_state.metrics.get('total_idle_time_minutes', 0)
        total_idle_hours = total_idle_minutes / 60
        st.metric("Total Idle Time", f"{total_idle_hours:.1f} jam")

    with col3:
        units_used = st.session_state.metrics.get('units_used', 0)
        st.metric("Unit Digunakan", units_used)

    with col4:
        units_available = st.session_state.metrics.get('units_available', 0)
        st.metric("Unit Tersedia", units_available)

    st.divider()

    # Detailed idle time analysis
    idle_data = []
    for unit_id, idle_minutes in st.session_state.metrics['idle_times'].items():
        unit_row = st.session_state.units_df[st.session_state.units_df['unit_id'] == unit_id]
        if not unit_row.empty:
            unit_name = unit_row.iloc[0]['name']
            idle_hours = idle_minutes / 60
            working_hours = (st.session_state.params.max_working_hours_per_day * 60 - idle_minutes) / 60
            idle_data.append({
                'Unit': unit_name,
                'Unit ID': unit_id,
                'Status': unit_row.iloc[0]['status'],
                'Kapasitas': unit_row.iloc[0]['capacity'],
                'Idle Time (jam)': idle_hours,
                'Waktu Kerja (jam)': working_hours,
                'Utilisasi (%)': (working_hours / st.session_state.params.max_working_hours_per_day) * 100
            })

    if idle_data:
        idle_df = pd.DataFrame(idle_data)

        # Sort by idle time to show units with most idle time first
        idle_df = idle_df.sort_values(by='Idle Time (jam)', ascending=False)

        st.subheader("Data Idle Time per Unit")
        st.dataframe(
            idle_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Idle Time (jam)": st.column_config.NumberColumn("Idle Time (jam)", format="%.2f jam"),
                "Waktu Kerja (jam)": st.column_config.NumberColumn("Waktu Kerja (jam)", format="%.2f jam"),
                "Utilisasi (%)": st.column_config.ProgressColumn(
                    "Utilisasi (%)",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            }
        )

        # Visualizations
        col1, col2 = st.columns(2)

        with col1:
            fig_idle = px.bar(
                idle_df,
                x='Unit',
                y='Idle Time (jam)',
                color='Status',
                title="Waktu Idle per Unit",
                color_discrete_map={'Available': '#2ecc71', 'Maintenance': '#e74c3c'}
            )
            fig_idle.update_layout(xaxis_title="Unit", yaxis_title="Idle Time (jam)")
            st.plotly_chart(fig_idle, use_container_width=True)

        with col2:
            fig_util = px.bar(
                idle_df,
                x='Unit',
                y='Utilisasi (%)',
                color='Status',
                title="Tingkat Utilisasi per Unit",
                color_discrete_map={'Available': '#2ecc71', 'Maintenance': '#e74c3c'}
            )
            fig_util.update_layout(xaxis_title="Unit", yaxis_title="Utilisasi (%)")
            st.plotly_chart(fig_util, use_container_width=True)

        st.subheader("Distribusi Idle Time")
        fig_dist = px.histogram(
            idle_df,
            x='Idle Time (jam)',
            nbins=15,
            title="Distribusi Waktu Idle Unit",
            marginal="box"
        )
        fig_dist.update_layout(xaxis_title="Idle Time (jam)", yaxis_title="Jumlah Unit")
        st.plotly_chart(fig_dist, use_container_width=True)

        # Capacity vs Idle Time analysis
        fig_capacity_idle = px.scatter(
            idle_df,
            x='Kapasitas',
            y='Idle Time (jam)',
            color='Status',
            title="Hubungan Kapasitas vs Idle Time",
            hover_data=['Unit', 'Unit ID']
        )
        fig_capacity_idle.update_layout(
            xaxis_title="Kapasitas Unit",
            yaxis_title="Idle Time (jam)"
        )
        st.plotly_chart(fig_capacity_idle, use_container_width=True)

        # Recommendations based on idle time
        st.subheader("Rekomendasi Berdasarkan Analisis Idle Time")

        high_idle_units = idle_df[idle_df['Idle Time (jam)'] > idle_df['Idle Time (jam)'].quantile(0.75)]
        low_idle_units = idle_df[idle_df['Idle Time (jam)'] < idle_df['Idle Time (jam)'].quantile(0.25)]

        if not high_idle_units.empty:
            st.info(f"Unit dengan idle time tinggi (>{idle_df['Idle Time (jam)'].quantile(0.75):.1f} jam): "
                   f"{', '.join(high_idle_units['Unit'].tolist())}. "
                   f"Pertimbangkan untuk memberikan penugasan tambahan pada unit ini.")

        if not low_idle_units.empty:
            st.info(f"Unit dengan idle time rendah (<{idle_df['Idle Time (jam)'].quantile(0.25):.1f} jam): "
                   f"{', '.join(low_idle_units['Unit'].tolist())}. "
                   f"Unit ini sudah optimal digunakan, pastikan waktu istirahat cukup.")

def render_locations_page():
    st.title("Data Lokasi")
    st.markdown("Kelola data lokasi terminal dan tempat penting lainnya")

    tab1, tab2, tab3 = st.tabs(["Daftar Lokasi", "Tambah Lokasi", "Edit/Hapus Lokasi"])

    with tab1:
        locations_df = get_locations_df()
        st.dataframe(
            locations_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "location_id": "ID Lokasi",
                "name": "Nama Lokasi",
                "address": "Alamat",
                "capacity": st.column_config.NumberColumn("Kapasitas", format="%d unit"),
                "type": "Tipe",
                "status": "Status"
            }
        )

        if not locations_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                fig_type = px.pie(
                    locations_df,
                    values='capacity',
                    names='type',
                    title="Distribusi Kapasitas berdasarkan Tipe Lokasi"
                )
                st.plotly_chart(fig_type, use_container_width=True)

            with col2:
                fig_status = px.bar(
                    locations_df,
                    x='name',
                    y='capacity',
                    color='status',
                    title="Kapasitas Lokasi berdasarkan Status",
                    color_discrete_map={'active': '#2ecc71', 'inactive': '#95a5a6'}
                )
                fig_status.update_layout(xaxis_title="Lokasi", yaxis_title="Kapasitas")
                st.plotly_chart(fig_status, use_container_width=True)

    with tab2:
        st.subheader("Tambah Lokasi Baru")

        with st.form("add_location_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_location_id = st.text_input("ID Lokasi", placeholder="L004")
                new_name = st.text_input("Nama Lokasi", placeholder="Terminal Timur")
                new_address = st.text_area("Alamat", placeholder="Jl. Raya Bogor No. 100")

            with col2:
                new_capacity = st.number_input("Kapasitas", min_value=10, max_value=200, value=50)
                new_type = st.selectbox("Tipe Lokasi", ["terminal", "depot", "maintenance", "parking"])
                new_status = st.selectbox("Status", ["active", "inactive"])

            if st.form_submit_button("Tambah Lokasi", type="primary"):
                if new_location_id and new_name and new_address:
                    location_data = {
                        'location_id': new_location_id,
                        'name': new_name,
                        'address': new_address,
                        'capacity': new_capacity,
                        'type': new_type,
                        'status': new_status
                    }
                    if add_location(location_data):
                        st.success(f"Lokasi {new_name} berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan lokasi. ID mungkin sudah ada.")
                else:
                    st.error("Mohon lengkapi semua field yang diperlukan")

    with tab3:
        st.subheader("Edit atau Hapus Lokasi")

        locations_df = get_locations_df()
        if locations_df.empty:
            st.info("Tidak ada data lokasi.")
        else:
            selected_location_id = st.selectbox(
                "Pilih Lokasi untuk diedit/dihapus",
                locations_df['location_id'].tolist(),
                format_func=lambda x: f"{x} - {locations_df[locations_df['location_id']==x]['name'].values[0]}",
                key="edit_location_select"
            )

            if selected_location_id:
                location_idx = locations_df[locations_df['location_id'] == selected_location_id].index[0]
                location_data = locations_df.loc[location_idx]

                with st.form("edit_location_form"):
                    col1, col2 = st.columns(2)

                    with col1:
                        edit_name = st.text_input("Nama Lokasi", value=location_data['name'])
                        edit_address = st.text_area("Alamat", value=location_data['address'])

                    with col2:
                        edit_capacity = st.number_input("Kapasitas", min_value=10, max_value=200, value=int(location_data['capacity']))
                        type_options = ["terminal", "depot", "maintenance", "parking"]
                        edit_type = st.selectbox("Tipe Lokasi", type_options, index=type_options.index(location_data['type']) if location_data['type'] in type_options else 0)
                        status_options = ["active", "inactive"]
                        edit_status = st.selectbox("Status", status_options, index=status_options.index(location_data['status']) if location_data['status'] in status_options else 0)

                    if st.form_submit_button("Simpan Perubahan", type="primary"):
                        update_data = {
                            'name': edit_name,
                            'address': edit_address,
                            'capacity': edit_capacity,
                            'type': edit_type,
                            'status': edit_status
                        }
                        if update_location(selected_location_id, update_data):
                            st.success(f"Lokasi {edit_name} berhasil diperbarui!")
                            st.rerun()
                        else:
                            st.error("Gagal memperbarui lokasi.")

                st.divider()

                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("Hapus Lokasi", type="secondary", use_container_width=True):
                        if st.button("Konfirmasi Hapus", key="confirm_delete_location", type="secondary", use_container_width=True):
                            if delete_location(selected_location_id):
                                st.success(f"Lokasi {location_data['name']} berhasil dihapus!")
                                st.rerun()
                            else:
                                st.error("Gagal menghapus lokasi.")

def render_audit_page():
    st.title("Audit Trail")
    st.markdown("Riwayat perubahan dan aktivitas sistem")

    tab1, tab2 = st.tabs(["Log Aktivitas", "Riwayat Penugasan"])

    with tab1:
        st.subheader("Log Aktivitas Terbaru")

        col1, col2 = st.columns([2, 1])
        with col1:
            entity_filter = st.selectbox(
                "Filter berdasarkan entitas:",
                ["Semua", "Unit", "Route", "Schedule", "Assignment", "OPTIMIZATION"]
            )
        with col2:
            limit = st.number_input("Jumlah log:", min_value=10, max_value=500, value=100)

        entity_type = None if entity_filter == "Semua" else entity_filter
        audit_logs = get_audit_logs(entity_type=entity_type, limit=limit)

        if len(audit_logs) == 0:
            st.info("Belum ada log aktivitas.")
        else:
            st.dataframe(
                audit_logs,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Waktu", format="DD/MM/YYYY HH:mm:ss"),
                    "action": "Aksi",
                    "entity_type": "Entitas",
                    "entity_id": "ID",
                    "details": "Detail"
                }
            )

            output = BytesIO()
            audit_logs.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)

            st.download_button(
                label="Download Audit Log (Excel)",
                data=output,
                file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with tab2:
        st.subheader("Riwayat Penugasan")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari tanggal:", value=datetime.now().date() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Sampai tanggal:", value=datetime.now().date())

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        hist_assignments = get_historical_assignments(start_datetime, end_datetime)

        if len(hist_assignments) == 0:
            st.info("Tidak ada riwayat penugasan dalam periode ini.")
        else:
            st.dataframe(
                hist_assignments,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "assignment_date": st.column_config.DatetimeColumn("Tanggal", format="DD/MM/YYYY"),
                    "total_score": st.column_config.ProgressColumn("Skor", format="%.2f", min_value=0, max_value=1),
                    "fuel_cost": st.column_config.NumberColumn("Biaya BBM", format="Rp %,.0f")
                }
            )

            output = BytesIO()
            hist_assignments.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)

            st.download_button(
                label="Download Riwayat Penugasan (Excel)",
                data=output,
                file_name=f"assignment_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def main():
    init_session_state()
    
    page = render_sidebar()
    
    if page == "Dashboard":
        render_dashboard()
    elif page == "Data Unit":
        render_units_page()
    elif page == "Data Rute":
        render_routes_page()
    elif page == "Data Jadwal":
        render_schedules_page()
    elif page == "Data Lokasi":
        render_locations_page()
    elif page == "Optimasi Penugasan":
        render_optimization_page()
    elif page == "Monitoring & Alert":
        render_monitoring_page()
    elif page == "Analisis Skenario":
        render_scenarios_page()
    elif page == "Laporan & Analitik":
        render_reports_page()
    elif page == "Analisis Idle Time":
        render_idle_time_page()
    elif page == "Audit Trail":
        render_audit_page()
    elif page == "Pengaturan":
        render_settings_page()

if __name__ == "__main__":
    main()
