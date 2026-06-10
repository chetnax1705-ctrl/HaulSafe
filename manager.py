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

@manager.route('/manager/trip/<int:trip_id>/assign', methods=['GET', 'POST'])
@manager_required
def assign_driver(trip_id):
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ? AND manager_id = ?',
                      (trip_id, session['user_id'])).fetchone()
    if not trip:
        flash('Trip not found.')
        db.close()
        return redirect('/manager')

    if request.method == 'POST':
        driver_email = request.form.get('driver_email', '').strip().lower()
        driver = db.execute(
            'SELECT * FROM users WHERE LOWER(email) = ? AND role = "driver"',
            (driver_email,)
        ).fetchone()
        if not driver:
            flash('No driver found with that email.')
            drivers = db.execute('SELECT id, name, email FROM users WHERE role = "driver"').fetchall()
            db.close()
            return render_template('assign_driver.html', trip=trip, drivers=drivers)

        db.execute('UPDATE trips SET driver_id = ?, status = "Assigned" WHERE id = ?',
                   (driver['id'], trip_id))
        db.commit()
        db.close()
        flash(f'Driver {driver["name"]} assigned successfully!')
        return redirect(f'/manager/trip/{trip_id}')

    drivers = db.execute('SELECT id, name, email FROM users WHERE role = "driver"').fetchall()
    db.close()
    return render_template('assign_driver.html', trip=trip, drivers=drivers)

@manager.route('/manager/trip/<int:trip_id>/track')
@manager_required
def track_trip(trip_id):
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ? AND manager_id = ?',
                      (trip_id, session['user_id'])).fetchone()
    db.close()
    if not trip:
        flash('Trip not found.')
        return redirect('/manager')
    return render_template('track_trip.html', trip=trip)

@manager.route('/manager/trip/<int:trip_id>/chat', methods=['POST'])
@manager_required
def ai_chat(trip_id):
    from google import genai
    import os

    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ?', (trip_id,)).fetchone()
    db.close()

    user_message = request.get_json().get('message', '')

    context = f"""You are HaulSafe AI, an assistant for Indian truck logistics compliance.
Current trip: {trip['origin']} to {trip['destination']}, cargo: {trip['cargo_type']}.
Indian law limits: max 5hr continuous driving, 30min mandatory break, max 8hr/day, 48hr/week, 8hr sleep between shifts (MV Act 1988 + Motor Transport Workers Act 1961).
Answer questions about this trip, fatigue rules, route planning, or compliance."""

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{context}\n\nUser: {user_message}"
    )

    return jsonify({'reply': response.text})
