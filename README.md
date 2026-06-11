# 🚛 HaulSafe

> A software-layer compliance platform for truck fleet management — enforcing driver rest limits that exist in law but never in practice.

---

## The Problem

Research by SaveLIFE Foundation found that Indian truck drivers average 11.9 hours of driving per day — nearly 4 hours over the legal limit. 49% admit to driving while fatigued. The laws exist (Motor Vehicles Act 1988, Motor Transport Workers Act 1961) but enforcement infrastructure does not.

The result: driver fatigue is one of the leading causes of highway accidents in India. Fleet owners face no accountability. Drivers have no protection.

Globally, this problem is solved by Electronic Logging Devices (ELDs) — mandatory in the US since 2017, EU, and Canada. India has no equivalent.

HaulSafe is the software-first answer.

---

## What HaulSafe Does

HaulSafe gives logistics managers and truck drivers a single platform to plan, assign, and monitor trips — with compliance built in from the start.

**For Managers:**
- Plan trips with real truck-optimized routing (via OpenRouteService)
- Auto-generated fatigue compliance schedule per Indian law
- Assign drivers to trips
- Live GPS tracking dashboard
- Compliance audit log — tamper-detected, auto-generated

**For Drivers:**
- View assigned trips with full route map
- Compliance schedule in plain language
- Break overdue alerts (triggered at 5-hour continuous driving limit)
- Quick Find — nearest fuel, food, rest stop, washroom
- Session tamper detection (app close, tab switch, session interruption — all logged)

---

## Why It's Different

Most fleet tools track packages. HaulSafe tracks compliance.

- No hardware required — works on any smartphone browser today
- ELD-ready architecture — GPS and logging endpoints can receive hardware feeds when ready
- Manager accountability — if a manager assigns an impossible schedule, it's documented
- Driver protection — drivers can point to a system-generated compliant schedule if pressured to overwork

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask, Flask-SocketIO |
| Database | SQLite |
| Routing | OpenRouteService API (HGV truck profile) |
| Maps | Leaflet.js |
| Live Tracking | Browser Geolocation API + WebSockets |
| Frontend | HTML, Bootstrap 5, CSS |
| Compliance Logic | Custom Python (MV Act 1988 limits hardcoded) |

---

## Legal Basis

HaulSafe enforces the following Indian statutory limits:

- Max 5 hours continuous driving → mandatory 30-minute break
- Max 8 hours driving per day
- Max 48 hours driving per week
- 8-hour sleep minimum between shifts
- 12-hour spread-over per day

*Source: Motor Vehicles Act 1988 & Motor Transport Workers Act 1961*

## Vision

The United States, Canada, and the European Union use digital systems to monitor driver working hours and reduce fatigue-related risk.

HaulSafe explores what a software-first, India-focused compliance layer could look like for the future of trucking operations.

---

## Demo Credentials

**Manager Account**
- Email: manager@test.com
- Password: ron@manager

**Driver Account**
- Email: driver@test.com
- Password: ben@driver

---

## Running Locally

```bash
git clone https://github.com/chetnax1705-ctrl/HaulSafe.git
cd HaulSafe
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your ORS_API_KEY and SECRET_KEY to .env
python app.py
```

Then open http://127.0.0.1:5000

---

*Built for Far Away 2026 Hackathon*
