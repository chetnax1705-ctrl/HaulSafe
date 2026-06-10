from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not name or not email or not password or not role:
            flash('All fields are required.')
            return redirect('/register')

        db = get_db()
        existing = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered.')
            db.close()
            return redirect('/register')

        hashed = generate_password_hash(password)
        db.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                   (name, email, hashed, role))
        db.commit()
        db.close()

        flash('Account created. Please log in.')
        return redirect('/login')

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password.')
            return redirect('/login')

        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']

        if user['role'] == 'manager':
            return redirect('/manager')
        else:
            return redirect('/driver')

    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return redirect('/login')