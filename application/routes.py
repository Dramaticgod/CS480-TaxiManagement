from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify
import random
import secrets
import time
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from application import app, db, sha256_crypt, session
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func, and_, desc
from application.models import User, Manager, Client, Driver, Address, Car, Model, Rent, Review, ClientAddress, CreditCard, DriverModel



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
            session['user_id'] = manager.SSN
            session['login_time'] = datetime.utcnow().timestamp()
            # return redirect(url_for('manager_dashboard'))
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
            return jsonify({'success': False, 'message': 'Name is required'})
            
        driver = Driver.query.get(name)
        
        print(f"Driver: {driver}, the name received is {name}")  # Debugging line to check the driver value
        if driver:
            # Create a User object and log in
            user = User(driver.name, 'driver', driver)
            login_user(user)
            session['user_id'] = driver.name
            session['login_time'] = datetime.utcnow().timestamp()
            return jsonify({'success': True, 'redirect': url_for('driver_dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    
    return jsonify({'success': False, 'message': 'Method not allowed'})

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

# Dashboard routes for each user type
@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    total_cars = db.session.query(Car).count()
    total_models = db.session.query(Model).count()
    total_drivers = db.session.query(Driver).count()
    avg_driver_rating = db.session.query(func.avg(Review.rating)).scalar() or 5
    total_rentals = db.session.query(Rent).count()
    last_month_rentals = db.session.query(Rent).filter(Rent.rent_date >= datetime.now() - timedelta(days=30)).count()
    car_brands = db.session.query(Car.brand).distinct().all()
    cars = db.session.query(Car).all()
    driver_cities = db.session.query(Driver.city).distinct().all()
    drivers = db.session.query(Driver).all()
    all_cities = db.session.query(Address.city).distinct().all()
    all_cities = [city[0] for city in all_cities]
    all_cities = list(set(all_cities))

    
    return render_template('manager_dashboard.html',
                            total_cars=total_cars,
                            total_models=total_models,
                            total_drivers=total_drivers,
                            avg_driver_rating=avg_driver_rating,
                            total_rentals=total_rentals,
                            last_month_rentals=last_month_rentals,
                            car_brands=car_brands,
                            cars=cars,
                            driver_cities=driver_cities,
                            drivers=drivers,
                            all_cities=all_cities)

@app.route('/manager/cars/add', methods=['POST'])
@login_required
def add_car():
    data = request.json
    brand = data.get('brand')

    if not brand:
        return jsonify({'success': False, 'message': 'Brand is required'})

    try:
        max_car_id = db.session.query(func.max(Car.CarID)).scalar() or 0
        new_car = Car(brand=brand, CarID=max_car_id + 1)
        db.session.add(new_car)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/models/add', methods=['POST'])
@login_required
def add_model():
    data = request.json
    car_id = data.get('car_id')
    color = data.get('color')
    construction_year = data.get('construction_year')
    transmission = data.get('transmission')
    
    if not all([car_id, color, construction_year, transmission]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        # Find the next available model_id
        max_model_id = db.session.query(func.max(Model.model_id)).scalar() or 0
        new_model = Model(
            model_id=max_model_id + 1,
            CarID=car_id,
            color=color,
            construction_year=construction_year,
            transmission=transmission
        )
        db.session.add(new_model)
        db.session.commit()
        return jsonify({'success': True, 'model_id': new_model.model_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/cars/<int:car_id>/models')
@login_required
def get_models_by_car(car_id):
    try:
        models = db.session.query(Model).filter(Model.CarID == car_id).all()
        models_data = [
                {
                    'model_id': model.model_id,
                    'CarID': model.CarID,
                    'color': model.color,
                    'construction_year': model.construction_year,
                    'transmission': model.transmission
                } for model in models
                ]
        return jsonify({'success': True, 'models': models_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/cars/<int:car_id>/delete', methods=['DELETE'])
@login_required
def delete_car(car_id):
    try:
        # Check if there are any rentals associated with this car's models
        models = Model.query.filter_by(CarID=car_id).all()
        for model in models:
            rent_count = Rent.query.filter_by(model_id=model.model_id, car_id=car_id).count()
            if rent_count > 0:
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete car, it has {rent_count} rentals associated with its models'
                })
        
        # Delete driver model associations first
        driver_models = DriverModel.query.filter_by(car_id=car_id).all()
        for dm in driver_models:
            db.session.delete(dm)
        
        # Delete models
        for model in models:
            db.session.delete(model)
        
        # Delete car
        car = Car.query.get(car_id)
        if car:
            db.session.delete(car)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Car not found'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/models/<int:model_id>/<int:car_id>/delete', methods=['DELETE'])
@login_required
def delete_model(model_id, car_id):
    try:
        # Check if there are any rentals for this model
        rent_count = Rent.query.filter_by(model_id=model_id, car_id=car_id).count()
        if rent_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete model, it has {rent_count} rentals'
            })
        
        # Remove driver model associations
        driver_models = DriverModel.query.filter_by(model_id=model_id, car_id=car_id).all()
        for dm in driver_models:
            db.session.delete(dm)
        
        # Delete model
        model = Model.query.get((model_id, car_id))
        if model:
            db.session.delete(model)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Model not found'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/drivers/add', methods=['POST'])
@login_required
def add_driver():
    data = request.json
    name = data.get('name')
    road_name = data.get('road_name')
    number = data.get('number')
    city = data.get('city')
    
    if not all([name, road_name, number, city]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        # Check if address exists, if not create it
        address = Address.query.filter_by(
            road_name=road_name,
            number=number,
            city=city
        ).first()
        
        if not address:
            address = Address(road_name=road_name, number=number, city=city)
            db.session.add(address)
        
        # Create driver
        new_driver = Driver(
            name=name,
            road_name=road_name,
            number=number,
            city=city
        )
        db.session.add(new_driver)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/drivers/<string:driver_name>/models')
@login_required
def get_driver_models(driver_name):
    try:

        # Get models assigned to the driver
        driver_models = db.session.query(
            Car.brand,
            Model.model_id,
            Model.CarID,
            Model.color,
            Model.construction_year,
            Model.transmission
        ).join(
            Model, Car.CarID == Model.CarID
        ).join(
            DriverModel, and_(
                Model.model_id == DriverModel.model_id,
                Model.CarID == DriverModel.car_id
            )
        ).filter(
            DriverModel.driver_name == driver_name
        ).all()
        
        # Format models data
        models_data = [
            {
                'brand': model[0],
                'model_id': model[1],
                'car_id': model[2],
                'color': model[3],
                'construction_year': model[4],
                'transmission': model[5]
            }
            for model in driver_models
        ]
        
        # Get available models (not assigned to this driver)
        available_models = db.session.query(
            Car.brand,
            Model.model_id,
            Model.CarID,
            Model.color,
            Model.construction_year,
            Model.transmission
        ).join(
            Model, Car.CarID == Model.CarID
        ).outerjoin(
            DriverModel, and_(
                Model.model_id == DriverModel.model_id,
                Model.CarID == DriverModel.car_id,
                DriverModel.driver_name == driver_name
            )
        ).filter(
            DriverModel.driver_name == None
        ).all()
        
        # Format available models data
        available_models_data = [
            {
                'brand': model[0],
                'model_id': model[1],
                'car_id': model[2],
                'color': model[3],
                'construction_year': model[4],
                'transmission': model[5]
            }
            for model in available_models
        ]
       
        return jsonify({
            'success': True,
            'models': models_data,
            'available_models': available_models_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/drivers/add_model', methods=['POST'])
@login_required
def add_driver_model():
    data = request.json
    driver_name = data.get('driver_name')
    model_id = data.get('model_id')
    car_id = data.get('car_id')
    
    if not all([driver_name, model_id, car_id]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        # Check if the driver already has this model
        existing = DriverModel.query.filter_by(
            driver_name=driver_name,
            model_id=model_id,
            car_id=car_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'This model is already assigned to the driver'})
        
        # Add the model to the driver
        new_driver_model = DriverModel(
            driver_name=driver_name,
            model_id=model_id,
            car_id=car_id
        )
        db.session.add(new_driver_model)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/drivers/<string:driver_name>/delete', methods=['DELETE'])
@login_required
def delete_driver(driver_name):
    try:
        # Check if there are any rentals for this driver
        rent_count = Rent.query.filter_by(driver_name=driver_name).count()
        if rent_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete driver, they have {rent_count} rentals'
            })
        
        # Delete reviews for this driver
        reviews = Review.query.filter_by(driver_name=driver_name).all()
        for review in reviews:
            db.session.delete(review)
        
        # Delete driver model associations
        driver_models = DriverModel.query.filter_by(driver_name=driver_name).all()
        for dm in driver_models:
            db.session.delete(dm)
        
        # Delete driver
        driver = Driver.query.get(driver_name)
        if driver:
            db.session.delete(driver)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Driver not found'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/top_clients/<int:count>')
@login_required
def get_top_clients(count):
    try:
        # Get clients with the most rentals
        top_clients = db.session.query(
            Client.name,
            Client.email,
            func.count(Rent.rent_id).label('total_rentals')
        ).join(
            Rent, Client.email == Rent.client_email
        ).group_by(
            Client.email
        ).order_by(
            desc('total_rentals')
        ).limit(count).all()
        
        clients_data = [
            {
                'name': client[0],
                'email': client[1],
                'total_rentals': client[2]
            }
            for client in top_clients
        ]
        
        return jsonify({'success': True, 'clients': clients_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/car_rental_stats')
@login_required
def get_car_rental_stats():
    try:
        brand_filter = request.args.get('brand')
        
        # Base query for car rental statistics
        query = db.session.query(
            Car.brand,
            Model.model_id,
            Model.color,
            Model.construction_year.label('year'),
            func.count(Rent.rent_id).label('rentals')
        ).join(
            Model, Car.CarID == Model.CarID
        ).join(
            Rent, and_(
                Model.model_id == Rent.model_id,
                Model.CarID == Rent.car_id
            )
        ).group_by(
            Car.brand,
            Model.model_id,
            Model.color,
            Model.construction_year
        ).order_by(
            desc('rentals')
        )
        
        # Apply brand filter if provided
        if brand_filter:
            query = query.filter(Car.brand == brand_filter)
        
        results = query.all()
        
        stats_data = [
            {
                'brand': stat[0],
                'model_id': stat[1],
                'color': stat[2],
                'year': stat[3],
                'rentals': stat[4]
            }
            for stat in results
        ]
        
        return jsonify({'success': True, 'stats': stats_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manager/driver_stats')
@login_required
def get_driver_stats():
    try:
        search_term = request.args.get('search', '')
        
        # Query for driver statistics
        query = db.session.query(
            Driver.name,
            func.count(Rent.rent_id).label('total_rentals'),
            func.coalesce(func.avg(Review.rating), 0).label('avg_rating')
        ).outerjoin(
            Rent, Driver.name == Rent.driver_name
        ).outerjoin(
            Review, Driver.name == Review.driver_name
        ).group_by(
            Driver.name
        ).order_by(
            desc('total_rentals')
        )
        
        # Apply search filter if provided
        if search_term:
            query = query.filter(Driver.name.ilike(f'%{search_term}%'))
        
        results = query.all()
        
        stats_data = [
            {
                'name': stat[0],
                'total_rentals': stat[1],
                'avg_rating': float(stat[2])
            }
            for stat in results
        ]
        
        return jsonify({'success': True, 'stats': stats_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


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
    driver = Driver.query.get(current_user.id)
    if current_user.role != 'driver':
        flash('Access denied.')
        return redirect(url_for('home'))
    
    return render_template('driver_dashboard.html', driver=driver)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))