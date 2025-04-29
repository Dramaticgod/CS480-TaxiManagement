from flask import render_template, request, redirect, url_for, session, flash, abort, jsonify
import random
import secrets
import time
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from application import app, db, sha256_crypt, session
from flask_login import login_user, logout_user, current_user, login_required
from application.models import User, Manager, Client, Driver, Address, Car, Model, Rent, Review, ClientAddress, CreditCard


@app.before_request
def validate_session():
    if current_user.is_authenticated:
        try:
            # Verify session integrity
            if 'user_id' not in session or 'login_time' not in session:
                logout_user()
                session.clear()
                flash('Session invalid. Please login again.', 'warning')
                return redirect(url_for('home'))
            
            # Verify user match
            if session.get('user_id') != current_user.id:
                logout_user()
                session.clear()
                flash('Session mismatch. Please login again.', 'warning')
                return redirect(url_for('home'))
            
            # Check session age
            login_timestamp = session.get('login_time', 0)
            session_age = datetime.utcnow().timestamp() - login_timestamp
            
            if session_age > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                logout_user()
                session.clear()
                flash('Session expired. Please login again.', 'warning')
                return redirect(url_for('home'))
                
        except Exception as e:
            app.logger.error(f"Session validation error: {str(e)}")
            logout_user()
            session.clear()
            flash('Session error. Please login again.', 'danger')
            return redirect(url_for('home'))
        
@app.route('/')
def home():
    # Return json of all drivers
    drivers = Driver.query.all()
    driver_list = []
    for driver in drivers:
        driver_list.append({
            'name': driver.name,
            'road_name': driver.road_name,
            'number': driver.number,
            'city': driver.city
        })
    # return jsonify(driver_list)
    return render_template('index.html')



# Manager login route
@app.route('/manager/login', methods=['POST'])
def manager_login():
    if request.method == 'POST':
        ssn = request.form.get('ssn')

        # print(f"SSN: {ssn}")  # Debugging line to check the SSN value   
        
        if not ssn:
            return jsonify({'success': False, 'message': 'SSN is required'})
            
        manager = Manager.query.get(ssn)

        # print(manager)
        # print("got past manager query")  
        
        if manager:
            # Create a User object and log in
            user = User(manager.SSN, 'manager', manager)

            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('manager_dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405

# Client login route
@app.route('/client/login', methods=['POST'])
def client_login():
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
            
        client = Client.query.get(email)
        
        if client:
            # Create a User object and log in
            user = User(client.email, 'client', client)
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('client_dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405

# Driver login route
@app.route('/driver/login', methods=['POST'])
def driver_login():
    if request.method == 'POST':
        name = request.form.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
            
        driver = Driver.query.get(name)
        
        if driver:
            # Create a User object and log in
            user = User(driver.name, 'driver', driver)
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('driver_dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405

# Registration routes for each user type
@app.route('/manager/register', methods=['GET', 'POST'])
def manager_register():
    if request.method == 'POST':
        ssn = request.form.get('ssn')
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Check if manager already exists
        existing_manager = Manager.query.get(ssn)
        if existing_manager:
            flash('A manager with this SSN already exists.')
            return render_template('manager_register.html')
        
        # Create new manager
        new_manager = Manager(SSN=ssn, name=name, email=email)
        db.session.add(new_manager)
        
        try:
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}')
    
    return render_template('manager_register.html')

@app.route('/client/register', methods=['GET', 'POST'])
def client_register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        
        # Check if client already exists
        existing_client = Client.query.get(email)
        if existing_client:
            flash('A client with this email already exists.')
            return render_template('client_register.html')
        
        # Create new client
        new_client = Client(email=email, name=name)
        db.session.add(new_client)
        
        try:
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}')
    
    return render_template('client_register.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

# Dashboard routes for each user type
@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash('Access denied.')
        return redirect(url_for('home'))
    
    return render_template('manager_dashboard.html')

@app.route('/client/dashboard')
@login_required
def client_dashboard():
    if current_user.role != 'client':
        flash('Access denied.')
        return redirect(url_for('home'))
    
    return render_template('client_dashboard.html')

@app.route('/driver/dashboard')
@login_required
def driver_dashboard():
    if current_user.role != 'driver':
        flash('Access denied.')
        return redirect(url_for('home'))
    
    return render_template('driver_dashboard.html')