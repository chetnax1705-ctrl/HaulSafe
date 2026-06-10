from flask import Blueprint, render_template, request, redirect, session, jsonify, flash
from database import get_db
from functools import wraps

manager = Blueprint('manager', __name__)

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'manager':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@manager.route('/manager')
@manager_required
def dashboard():
    db = get_db()
    trips = db.execute(
        'SELECT * FROM trips WHERE manager_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template('manager_dashboard.html', trips=trips)

@manager.route('/manager/new_trip', methods=['GET', 'POST'])
@manager_required
def new_trip():
    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        cargo_type = request.form.get('cargo_type')
        cargo_fragile = 1 if request.form.get('cargo_fragile') else 0
        cargo_temp_sensitive = 1 if request.form.get('cargo_temp_sensitive') else 0

        db = get_db()
        db.execute(
            '''INSERT INTO trips (manager_id, origin, destination, cargo_type, cargo_fragile, cargo_temp_sensitive)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (session['user_id'], origin, destination, cargo_type, cargo_fragile, cargo_temp_sensitive)
        )
        db.commit()
        db.close()

        flash('Trip planned successfully.')
        return redirect('/manager')

    return render_template('new_trip.html')

@manager.route('/manager/trip/<int:trip_id>')
@manager_required
def trip_detail(trip_id):
    from routes import geocode_city, get_route, calculate_fatigue_schedule
    
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ? AND manager_id = ?',
                      (trip_id, session['user_id'])).fetchone()
    db.close()

    if not trip:
        flash('Trip not found.')
        return redirect('/manager')

    # Get coordinates
    origin_coords = geocode_city(trip['origin'])
    dest_coords = geocode_city(trip['destination'])

    if not origin_coords or not dest_coords:
        flash('Could not find coordinates for one of the cities.')
        return redirect('/manager')

    # Get route from ORS
    route_data = get_route(origin_coords, dest_coords, 
                           avoid_unpaved=bool(trip['cargo_fragile']))

    # Extract route info
    route_summary = route_data['routes'][0]['summary']
    distance_km = round(route_summary['distance'], 1)
    duration_minutes = round(route_summary['duration'] / 60)
    geometry = route_data['routes'][0]['geometry']

    # Calculate fatigue schedule
    schedule, arrival_time = calculate_fatigue_schedule(duration_minutes)

    return render_template('trip_detail.html',
                           trip=trip,
                           distance_km=distance_km,
                           duration_minutes=duration_minutes,
                           schedule=schedule,
                           geometry=geometry,
                           origin_coords=origin_coords,
                           dest_coords=dest_coords)