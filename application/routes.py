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
from sqlalchemy.exc import SQLAlchemyError
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
        email = request.form.get('email').title()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
            
        client = Client.query.get(email)
        
        if client:
            # Create a User object and log in
            user = User(client.email, 'client', client)
            login_user(user)
            session['user_id'] = client.email
            session['login_time'] = datetime.utcnow().timestamp()
            return jsonify({'success': True, 'redirect': url_for('client_dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405

# Driver login route
@app.route('/driver/login', methods=['POST'])
def driver_login():
    if request.method == 'POST':
        name = request.form.get('name').title()
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'})
            
        driver = Driver.query.get(name)
        
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
        name = request.form.get('name').title()
        email = request.form.get('email').title()
        
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
        email = request.form.get('email').title()
        name = request.form.get('name').title()
        
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
    avg_driver_rating = db.session.query(func.avg(Review.rating)).scalar() or 5.0
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
                            avg_driver_rating=round(avg_driver_rating,2),
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
    brand = data.get('brand').title()

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
    color = data.get('color').title()
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
    name = data.get('name').title()
    road_name = data.get('road_name').title()
    number = data.get('number').title()
    city = data.get('city').title()
    
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
    driver_name = data.get('driver_name').title()
    model_id = data.get('model_id').title()
    car_id = data.get('car_id').title()
    
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
                'email': client[1].lower(),
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

@app.route('/manager/client_search')
@login_required
def client_search():

    city_client = request.args.get('city_client', '')
    city_driver = request.args.get('city_driver', '')

    client = db.session.query(Client).join(ClientAddress).filter(
        ClientAddress.city == city_client
    ).all()

    driver = db.session.query(Driver).join(DriverModel).join(Rent).filter(
        Driver.city == city_driver
    ).all()

    merge = db.session.query(Client, func.count(Rent.rent_id).label('total_rides')).join(
        Rent, Client.email == Rent.client_email
    ).filter(
        Rent.driver_name == Driver.name,
        Driver.city == city_driver
    ).group_by(Client.email).distinct().all()

    return jsonify({
        'success': True,
        'clients': [{'name': c.name, 'email': c.email.lower(), 'address': f"{ca.road_name} {ca.number}, {ca.city}", 'total_rides': m.total_rides} for c in client for ca in c.addresses for m in merge if m[0].email == c.email]
    })

@app.route('/client/dashboard')
@login_required
def client_dashboard():
    if current_user.role != 'client':
        return redirect(url_for('login'))
    
    client = current_user.user_obj
    
    # Get addresses
    addresses = db.session.query(Address).join(
        ClientAddress, 
        (ClientAddress.road_name == Address.road_name) & 
        (ClientAddress.number == Address.number) & 
        (ClientAddress.city == Address.city)
    ).filter(ClientAddress.client_email == client.email).all()
    
    # Get credit cards
    credit_cards = CreditCard.query.filter_by(client_email=client.email).all()
    
    # Get rents/bookings
    rents = Rent.query.filter_by(client_email=client.email).all()
    
    # Process rents to include car information and review status
    for rent in rents:
        # Check if this rent has a review
        rent.has_review = Review.query.filter_by(
            client_email=client.email,
            driver_name=rent.driver_name
        ).first() is not None
    
    return render_template('client_dashboard.html', 
                           client=client,
                           addresses=addresses,
                           credit_cards=credit_cards,
                           rents=rents,
                           today_date=datetime.today().strftime('%Y-%m-%d'))

@app.route('/client/available-cars', methods=['GET'])
@login_required
def available_cars():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    rent_date_str = request.args.get('date')
    
    try:
        rent_date = datetime.strptime(rent_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get all models
    available_cars = []
    
    try:
        # Find models with available cars on the specified date
        # 1. Gets all models
        # 2. Checks if the model has at least one driver qualified to drive it
        # 3. Checks if the model is not already rented on the specified date
        
        subquery = db.session.query(Rent.model_id, Rent.car_id).\
            filter(Rent.rent_date == rent_date).subquery()
        
        available_models = db.session.query(
            Model.model_id,
            Model.CarID,
            Car.brand,
            Model.color,
            Model.construction_year,
            Model.transmission
        ).join(Car).\
        join(DriverModel, (DriverModel.model_id == Model.model_id) & 
                          (DriverModel.car_id == Model.CarID)).\
        outerjoin(subquery, (subquery.c.model_id == Model.model_id) & 
                           (subquery.c.car_id == Model.CarID)).\
        filter(subquery.c.model_id.is_(None)).\
        distinct().all()
        
        for model in available_models:
            available_cars.append({
                'model_id': model.model_id,
                'car_id': model.CarID,
                'brand': model.brand,
                'color': model.color,
                'year': model.construction_year,
                'transmission': model.transmission
            })
        
        return jsonify({'cars': available_cars})
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/client/my-rents', methods=['GET'])
@login_required
def my_rents():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    client = current_user.user_obj
    
    try:
        # Get all rents with related information
        rents_data = db.session.query(
            Rent.rent_id,
            Rent.rent_date,
            Rent.driver_name,
            Rent.model_id,
            Car.brand,
            Model.color
        ).join(Model, (Model.model_id == Rent.model_id) & (Model.CarID == Rent.car_id)).\
        join(Car, Car.CarID == Model.CarID).\
        filter(Rent.client_email == client.email).\
        order_by(Rent.rent_date.desc()).\
        all()
        
      
        rents = []
        for rent in rents_data:
            # Check if this rent has a review
            has_review = Review.query.filter_by(
                client_email=client.email,
                driver_name=rent.driver_name
            ).first() is not None
            
            rents.append({
                'rent_id': rent.rent_id,
                'rent_date': rent.rent_date.strftime('%Y-%m-%d') if rent.rent_date else None,
                'driver_name': rent.driver_name,
                'model_id': rent.model_id,
                'brand': rent.brand,
                'color': rent.color,
                'has_review': has_review
            })
        
        return jsonify({'rents': rents})
        
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/client/add-address', methods=['POST'])
@login_required
def add_address():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    client = current_user.user_obj
    
    road_name = request.form.get('road_name').title()
    number = request.form.get('number')
    city = request.form.get('city').title()
    
    if not road_name or not number or not city:
        return jsonify({'success': False, 'message': 'All address fields are required'}), 400
    
    try:

        address = Address.query.filter_by(
            road_name=road_name,
            number=number,
            city=city
        ).first()
        
        if not address:
            address = Address(
                road_name=road_name,
                number=number,
                city=city
            )
            db.session.add(address)
        
        existing_client_address = ClientAddress.query.filter_by(
            client_email=client.email,
            road_name=road_name,
            number=number,
            city=city
        ).first()
        
        if existing_client_address:
            return jsonify({'success': False, 'message': 'You already have this address'}), 400
        
        client_address = ClientAddress(
            client_email=client.email,
            road_name=road_name,
            number=number,
            city=city
        )
        
        db.session.add(client_address)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500

@app.route('/client/add-credit-card', methods=['POST'])
@login_required
def add_credit_card():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    client = current_user.user_obj
    
    card_number = request.form.get('card_number')
    billing_address = request.form.get('billing_address')
    
    if not card_number or not billing_address:
        return jsonify({'success': False, 'message': 'Card number and billing address are required'}), 400
    
    try:
        address_parts = billing_address.split(',')
        if len(address_parts) != 3:
            return jsonify({'success': False, 'message': 'Invalid billing address format'}), 400
        
        road_name, number, city = address_parts
        

        client_address = ClientAddress.query.filter_by(
            client_email=client.email,
            road_name=road_name,
            number=number,
            city=city
        ).first()
        
        if not client_address:
            return jsonify({'success': False, 'message': 'Invalid billing address'}), 400
        
        # Check if card already exists
        existing_card = CreditCard.query.filter_by(card_number=card_number).first()
        if existing_card:
            return jsonify({'success': False, 'message': 'This credit card already exists'}), 400
        
        # Create new credit card
        credit_card = CreditCard(
            card_number=card_number,
            client_email=client.email,
            road_name=road_name,
            number=number,
            city=city
        )
        
        db.session.add(credit_card)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500

@app.route('/client/add-review', methods=['POST'])
@login_required
def add_review():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    client = current_user.user_obj
    
    driver_name = request.form.get('driver_name')
    rating = request.form.get('rating')
    message = request.form.get('message')
    rent_id = request.form.get('rent_id')
    
    if not driver_name or not rating or not rent_id:
        return jsonify({'success': False, 'message': 'Driver name, rating, and rent ID are required'}), 400
    

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400
        
        # Verify the rent exists and belongs to this client and driver
        rent = Rent.query.filter_by(
            rent_id=rent_id,
            client_email=client.email,
            driver_name=driver_name
        ).first()
        
        if not rent:
            return jsonify({'success': False, 'message': 'Invalid rent ID or driver'}), 400
        
        # Check if review already exists
        existing_review = Review.query.filter_by(
            client_email=client.email,
            driver_name=driver_name
        ).first()
        
        if existing_review:
            return jsonify({'success': False, 'message': 'You have already reviewed this driver'}), 400
        
        max_review_id = db.session.query(func.max(Review.review_id)).scalar() or 0
        # Create new review
        review = Review(
            review_id=max_review_id + 1,
            driver_name=driver_name,
            client_email=client.email,
            rating=rating,
            message=message
        )
        
        db.session.add(review)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid rating value'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500

@app.route('/client/book-rent', methods=['POST'])
@login_required
def book_rent():
    if current_user.role != 'client':
        return jsonify({'error': 'Unauthorized'}), 403
    
    client = current_user.user_obj
    data = request.json
    
    model_id = data.get('model_id')
    car_id = data.get('car_id')
    rent_date_str = data.get('rent_date')
    best_driver = data.get('best_driver', False)
    
    try:
        rent_date = datetime.strptime(rent_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    
    # Check if the model is available on this date
    existing_rent = Rent.query.filter_by(
        model_id=model_id,
        car_id=car_id,
        rent_date=rent_date
    ).first()
    
    if existing_rent:
        return jsonify({'success': False, 'message': 'This car is no longer available for the selected date'}), 400
    
    try:
        # ATTEMPT FOR 4 PERSON GROUP
        if best_driver:
            # Find the highest-rated driver for this model
            driver_query = db.session.query(
                Driver.name,
                func.avg(Review.rating).label('avg_rating')
            ).outerjoin(Review).\
            join(DriverModel, DriverModel.driver_name == Driver.name).\
            filter(
                DriverModel.model_id == model_id,
                DriverModel.car_id == car_id
            ).\
            group_by(Driver.name).\
            order_by(desc('avg_rating')).\
            first()
            
            if not driver_query or not driver_query.name:
                return jsonify({'success': False, 'message': 'No qualified drivers available for this model'}), 400
            
            driver_name = driver_query.name
        else:
            # Just get any qualified driver
            driver_model = DriverModel.query.filter_by(
                model_id=model_id,
                car_id=car_id
            ).first()
            
            if not driver_model:
                return jsonify({'success': False, 'message': 'No qualified drivers available for this model'}), 400
            
            driver_name = driver_model.driver_name
        
        # Create the new rent record
        max_rent_id = db.session.query(func.max(Rent.rent_id)).scalar() or 0
        new_rent = Rent(
            rent_id=max_rent_id + 1,
            rent_date=rent_date,
            client_email=client.email,
            driver_name=driver_name,
            model_id=model_id,
            car_id=car_id
        )
        
        db.session.add(new_rent)
        db.session.commit()
        
        return jsonify({'success': True, 'rent_id': new_rent.rent_id})
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500

@app.route('/driver/dashboard')
@login_required
def driver_dashboard():
    driver = Driver.query.get(current_user.id)
    if current_user.role != 'driver':
        flash('Access denied.')
        return redirect(url_for('home'))
    # Get the driver's models they can drive
    driver_models = (
        Model.query
        .join(DriverModel, and_(Model.model_id == DriverModel.model_id, Model.CarID == DriverModel.car_id))
        .filter(DriverModel.driver_name == current_user.user_obj.name)
        .all()
    )
    
    # Get all car models
    all_models = Model.query.all()
    
    return render_template(
        "driver_dashboard.html", 
        driver=current_user.user_obj,
        driver_models=driver_models,
        all_models=all_models
    )

@app.route("/driver/update-address", methods=["POST"])
@login_required
def update_driver_address():
    if current_user.role != "driver":
        return jsonify({"success": False, "message": "Access denied."})
    
    try:
        road_name = request.form.get("road_name")
        number = request.form.get("number")
        city = request.form.get("city")
        
        if not all([road_name, number, city]):
            return jsonify({"success": False, "message": "All address fields are required."})
        
        # Check if address exists, if not create it
        address = Address.query.filter_by(road_name=road_name, number=number, city=city).first()
        if not address:
            address = Address(road_name=road_name, number=number, city=city)
            db.session.add(address)
            db.session.commit()
        
        # Update driver's address
        driver = current_user.user_obj
        driver.road_name = road_name
        driver.number = number
        driver.city = city
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating driver address: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred. Please try again."})

@app.route("/driver/add-model", methods=["POST"])
@login_required
def _add_driver_model():
    if current_user.role != "driver":
        return jsonify({"success": False, "message": "Access denied."})
    
    try:
        data = request.json
        model_id = data.get("model_id")
        car_id = data.get("car_id")
        
        if not all([model_id, car_id]):
            return jsonify({"success": False, "message": "Model ID and Car ID are required."})
        
        # Check if driver-model relation exists
        driver_model = DriverModel.query.filter_by(
            driver_name=current_user.user_obj.name,
            model_id=model_id,
            car_id=car_id
        ).first()
        
        if driver_model:
            return jsonify({"success": False, "message": "You already declared you can drive this model."})
        
        # Add new driver-model relation
        new_driver_model = DriverModel(
            driver_name=current_user.user_obj.name,
            model_id=model_id,
            car_id=car_id
        )
        db.session.add(new_driver_model)
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding driver model: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred. Please try again."})

@app.route("/driver/remove-model", methods=["POST"])
@login_required
def remove_driver_model():
    if current_user.role != "driver":
        return jsonify({"success": False, "message": "Access denied."})
    
    try:
        data = request.json
        model_id = data.get("model_id")
        car_id = data.get("car_id")
        
        if not all([model_id, car_id]):
            return jsonify({"success": False, "message": "Model ID and Car ID are required."})
        
        # Find and delete driver-model relation
        driver_model = DriverModel.query.filter_by(
            driver_name=current_user.user_obj.name,
            model_id=model_id,
            car_id=car_id
        ).first()
        
        if not driver_model:
            return jsonify({"success": False, "message": "You haven't declared you can drive this model."})
        
        db.session.delete(driver_model)
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error removing driver model: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred. Please try again."})

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))