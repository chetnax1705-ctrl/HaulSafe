from flask import Blueprint, render_template, request, redirect, session, jsonify
from database import get_db
from functools import wraps

driver_bp = Blueprint('driver', __name__)

def driver_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'driver':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@driver_bp.route('/driver')
@driver_required
def dashboard():
    db = get_db()
    # Find trips assigned to this driver
    trips = db.execute(
        'SELECT * FROM trips WHERE driver_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template('driver_dashboard.html', trips=trips)

@driver_bp.route('/driver/trip/<int:trip_id>')
@driver_required
def active_trip(trip_id):
    from routes import geocode_city, get_route, calculate_fatigue_schedule

    db = get_db()
    trip = db.execute(
        'SELECT * FROM trips WHERE id = ? AND driver_id = ?',
        (trip_id, session['user_id'])
    ).fetchone()
    db.close()

    if not trip:
        return redirect('/driver')

    origin_coords = geocode_city(trip['origin'])
    dest_coords = geocode_city(trip['destination'])
    route_data = get_route(origin_coords, dest_coords)
    route_summary = route_data['routes'][0]['summary']
    duration_minutes = round(route_summary['duration'] / 60)
    geometry = route_data['routes'][0]['geometry']
    schedule, _ = calculate_fatigue_schedule(duration_minutes)

    return render_template('driver_trip.html',
                           trip=trip,
                           schedule=schedule,
                           geometry=geometry,
                           origin_coords=origin_coords,
                           dest_coords=dest_coords,
                           duration_minutes=duration_minutes)

@driver_bp.route('/driver/update_location', methods=['POST'])
@driver_required
def update_location():
    from app import socketio
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    trip_id = data.get('trip_id')
    socketio.emit('location_update', {
        'lat': lat,
        'lng': lng,
        'trip_id': trip_id,
        'driver_id': session['user_id']
    })
    return jsonify({'status': 'ok'})

@driver_bp.route('/driver/log_violation', methods=['POST'])
@driver_required
def log_violation():
    data = request.get_json()
    trip_id = data.get('trip_id')
    event_type = data.get('event_type')  # e.g. 'break_skipped'
    note = data.get('note', '')
    db = get_db()
    db.execute(
        'INSERT INTO compliance_logs (trip_id, driver_id, event_type, note) VALUES (?, ?, ?, ?)',
        (trip_id, session['user_id'], event_type, note)
    )
    db.commit()
    db.close()
    return jsonify({'status': 'logged'})

@driver_bp.route('/driver/heartbeat', methods=['POST'])
@driver_required
def heartbeat():
    data = request.get_json()
    trip_id = data.get('trip_id')
    event = data.get('event', 'heartbeat')  # heartbeat | tab_hidden | tab_visible | session_start
    
    db = get_db()
    db.execute(
        'INSERT INTO compliance_logs (trip_id, driver_id, event_type, note) VALUES (?, ?, ?, ?)',
        (trip_id, session['user_id'], event, f'Auto-logged: {event}')
    )
    db.commit()
    db.close()
    return jsonify({'status': 'ok'})
