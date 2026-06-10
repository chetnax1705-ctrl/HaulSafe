from flask import Flask, render_template, redirect, request, jsonify, session
from flask_socketio import SocketIO
from dotenv import load_dotenv
from database import init_db
from auth import auth
import os
import requests
from manager import manager
from driver import driver_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins="*")

app.register_blueprint(auth)
app.register_blueprint(manager)
app.register_blueprint(driver_bp)

init_db()

@app.route("/")
def index():
    if session.get('role') == 'manager':
        return redirect('/manager')
    elif session.get('role') == 'driver':
        return redirect('/driver')
    return render_template("index.html")

if __name__ == "__main__":
    socketio.run(app, debug=True)
