import requests
import os
from datetime import datetime, timedelta

ORS_API_KEY = os.getenv("ORS_API_KEY")

# Indian compliance constants (MV Act 1988 + Motor Transport Workers Act 1961)
MAX_CONTINUOUS_DRIVE = 5 * 60  # 5 hours in minutes
MANDATORY_BREAK = 30  # minutes
MAX_DAILY_DRIVE = 8 * 60  # 8 hours in minutes
MAX_SPREAD_OVER = 12 * 60  # 12 hours total work window
SLEEP_TIME = 8 * 60  # minimum 8 hours rest between shifts

def geocode_city(city_name):
    """Convert city name to coordinates using ORS geocoding"""
    url = "https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": ORS_API_KEY,
        "text": city_name + ", India",
        "size": 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data['features']:
        coords = data['features'][0]['geometry']['coordinates']
        return coords  # [longitude, latitude]
    return None

def get_route(origin_coords, destination_coords, avoid_unpaved=False):
    """Get route from ORS"""
    url = "https://api.openrouteservice.org/v2/directions/driving-hgv"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [origin_coords, destination_coords],
        "instructions": True,
        "units": "km"
    }
    response = requests.post(url, json=body, headers=headers)
    data = response.json()
    return data

def calculate_fatigue_schedule(total_drive_minutes, departure_time=None):
    """
    Calculate legally compliant rest schedule based on Indian law.
    Returns a list of events (drive, break, sleep) with timestamps.
    """
    if departure_time is None:
        departure_time = datetime.now().replace(second=0, microsecond=0)

    schedule = []
    remaining = total_drive_minutes
    current_time = departure_time
    continuous_driven = 0
    daily_driven = 0
    day = 1

    while remaining > 0:
        # How long can we drive before hitting continuous or daily limit?
        can_drive = min(
            MAX_CONTINUOUS_DRIVE - continuous_driven,
            MAX_DAILY_DRIVE - daily_driven,
            remaining
        )

        if can_drive <= 0:
            if daily_driven >= MAX_DAILY_DRIVE:
                # End of day — mandatory sleep
                schedule.append({
                    "type": "sleep",
                    "start": current_time.strftime("%I:%M %p"),
                    "duration_minutes": SLEEP_TIME,
                    "label": f"Day {day} Rest — Mandatory 8-hour sleep",
                    "day": day
                })
                current_time += timedelta(minutes=SLEEP_TIME)
                daily_driven = 0
                continuous_driven = 0
                day += 1
            else:
                # Mandatory 30 min break
                schedule.append({
                    "type": "break",
                    "start": current_time.strftime("%I:%M %p"),
                    "duration_minutes": MANDATORY_BREAK,
                    "label": "Mandatory 30-min break",
                    "day": day
                })
                current_time += timedelta(minutes=MANDATORY_BREAK)
                continuous_driven = 0
            continue

        # Drive segment
        schedule.append({
            "type": "drive",
            "start": current_time.strftime("%I:%M %p"),
            "duration_minutes": can_drive,
            "label": f"Drive — {round(can_drive/60, 1)} hours",
            "day": day
        })
        current_time += timedelta(minutes=can_drive)
        continuous_driven += can_drive
        daily_driven += can_drive
        remaining -= can_drive

        # Check if break needed after this segment
        if continuous_driven >= MAX_CONTINUOUS_DRIVE and remaining > 0:
            schedule.append({
                "type": "break",
                "start": current_time.strftime("%I:%M %p"),
                "duration_minutes": MANDATORY_BREAK,
                "label": "Mandatory 30-min break",
                "day": day
            })
            current_time += timedelta(minutes=MANDATORY_BREAK)
            continuous_driven = 0

    # Add arrival
    schedule.append({
        "type": "arrival",
        "start": current_time.strftime("%I:%M %p"),
        "duration_minutes": 0,
        "label": "Estimated Arrival",
        "day": day
    })

    return schedule, current_time
