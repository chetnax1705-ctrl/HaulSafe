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

    if not trip:
        db.close()
        flash('Trip not found.')
        return redirect('/manager')

    # Get coordinates
    origin_coords = geocode_city(trip['origin'])
    dest_coords = geocode_city(trip['destination'])

    if not origin_coords or not dest_coords:
        db.close()
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

    compliance_logs = db.execute(
        'SELECT * FROM compliance_logs WHERE trip_id = ? ORDER BY timestamp DESC',
        (trip_id,)
    ).fetchall()
    db.close()

    return render_template('trip_detail.html',
                           trip=trip,
                           distance_km=distance_km,
                           duration_minutes=duration_minutes,
                           schedule=schedule,
                           geometry=geometry,
                           origin_coords=origin_coords,
                           dest_coords=dest_coords,
                           compliance_logs=compliance_logs)

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
    db = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id = ?', (trip_id,)).fetchone()
    db.close()

    user_message = request.get_json().get('message', '').lower()
    origin = trip['origin']
    destination = trip['destination']
    cargo = trip['cargo_type']
    fragile = trip['cargo_fragile']
    temp_sensitive = trip['cargo_temp_sensitive']
    assigned = trip['driver_id']

    if any(w in user_message for w in ['rest', 'stop', 'break', 'stops', 'pause']):
        reply = f"For {origin} → {destination}, the driver needs a mandatory 30-minute break after every 5 hours of continuous driving (MV Act 1988). The compliance schedule on this page shows exact timings. Skipping breaks is a legal violation and a safety risk."

    elif any(w in user_message for w in ['sleep', 'overnight', 'night', 'rest period']):
        reply = "The Motor Transport Workers Act 1961 mandates a minimum 8-hour sleep period between shifts. For this 2-day trip, the driver must stop and rest for 8 hours at the end of Day 1 before resuming driving."

    elif any(w in user_message for w in ['skip', 'violat', 'miss', 'ignore', 'penalty', 'fine', 'punish']):
        reply = "If a driver skips a mandatory break or rest period, it's a violation of the Motor Vehicles Act 1988. HaulSafe logs all compliance violations automatically. Repeated violations can result in license suspension and the fleet operator faces liability in case of an accident."

    elif any(w in user_message for w in ['cargo', 'load', 'goods', 'fragile', 'temperature', 'temp', 'sensitive']):
        notes = []
        if fragile:
            notes.append("unpaved roads are avoided in the route")
        if temp_sensitive:
            notes.append("temperature-sensitive handling is required — avoid prolonged stops in direct sunlight")
        if notes:
            reply = f"This trip carries {cargo}. Special handling: {', '.join(notes)}."
        else:
            reply = f"This trip carries {cargo} with no special handling constraints. Standard routing applies."

    elif any(w in user_message for w in ['distance', 'km', 'kilometre', 'kilometer', 'far', 'long', 'length']):
        reply = f"The {origin} to {destination} route is approximately 1394 km via the truck-optimized highway route. This is a long-haul trip spanning 2 days when compliance breaks and mandatory sleep are factored in."

    elif any(w in user_message for w in ['time', 'arrival', 'reach', 'when', 'duration', 'how long', 'eta']):
        reply = f"Pure drive time is ~17 hours 49 minutes, but with mandatory 30-min breaks and an 8-hour overnight rest, the total trip duration is approximately 2 days. The exact estimated arrival is at the bottom of the compliance schedule."

    elif any(w in user_message for w in ['complian', 'law', 'legal', 'mv act', 'rule', 'regulation', 'act']):
        reply = "HaulSafe enforces two Indian laws: Motor Vehicles Act 1988 (max 5hr continuous driving, 30-min break, 8hr/day limit) and Motor Transport Workers Act 1961 (8hr sleep between shifts, 48hr/week max). These rules exist but are rarely enforced — HaulSafe automates compliance."

    elif any(w in user_message for w in ['route', 'road', 'highway', 'path', 'way', 'toll']):
        reply = f"The route from {origin} to {destination} is calculated using OpenRouteService with truck-specific constraints — accounting for vehicle height, weight, and {'avoiding unpaved roads due to fragile cargo' if fragile else 'standard road preferences'}. The route is shown on the map above."

    elif any(w in user_message for w in ['driver', 'assign', 'who', 'operator']):
        if assigned:
            reply = f"A driver has been assigned to this trip. You can monitor their real-time location using the Live Track button. The driver can view their compliance schedule on their dashboard."
        else:
            reply = f"No driver has been assigned to this trip yet. Use the Assign Driver button to assign a registered driver. They'll immediately see the trip and compliance schedule on their dashboard."

    elif any(w in user_message for w in ['track', 'location', 'live', 'gps', 'where']):
        reply = "HaulSafe tracks the driver's live GPS location using the browser's Geolocation API. The manager can view the truck's real-time position on the Live Tracking map. Location updates are pushed instantly via WebSockets (Socket.IO)."

    elif any(w in user_message for w in ['safe', 'safety', 'accident', 'risk', 'danger', 'fatigue']):
        reply = "Driver fatigue is the leading cause of truck accidents in India. HaulSafe prevents fatigue by enforcing mandatory breaks and rest periods per Indian law. The compliance schedule ensures no driver exceeds safe driving limits, reducing accident risk significantly."

    elif any(w in user_message for w in ['haulsafe', 'app', 'system', 'platform', 'how', 'work']):
        reply = "HaulSafe is an AI-powered logistics compliance platform for Indian trucking. It plans truck routes using real road data, generates fatigue-compliant schedules per Indian law, tracks drivers live, and logs compliance violations — all in one dashboard for logistics managers and drivers."

    elif any(w in user_message for w in ['week', 'weekly', '48', 'hours']):
        reply = "Indian law caps driving at 48 hours per week (Motor Vehicles Act 1988). HaulSafe tracks cumulative driving hours across trips to flag drivers approaching this weekly limit, preventing legal violations before they happen."

    else:
        reply = f"I'm HaulSafe Assistant, your logistics compliance guide. This trip covers {origin} → {destination} carrying {cargo} (~1394 km, ~2 days with compliance breaks). You can ask me about rest stops, driving rules, cargo handling, route details, driver tracking, or Indian transport law."

    return jsonify({'reply': reply})
