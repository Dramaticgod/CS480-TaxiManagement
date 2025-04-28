from flask import url_for, redirect
from application import db, login_manager, ModelView, app
from datetime import datetime
from flask_login import UserMixin, current_user

# Define a User class that combines all user types for login purposes
class User(UserMixin):
    def __init__(self, id, role, user_obj):
        self.id = id
        self.role = role  # 'manager', 'client', or 'driver'
        self.user_obj = user_obj

    def get_id(self):
        return f"{self.role}_{self.id}"

@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    
    try:
        # User ID format is "role_actual_id"
        role, actual_id = user_id.split('_', 1)
        
        if role == 'manager':
            user_obj = Manager.query.get(actual_id)
        elif role == 'client':
            user_obj = Client.query.get(actual_id)
        elif role == 'driver':
            user_obj = Driver.query.get(actual_id)
        else:
            return None
            
        if user_obj:
            return User(actual_id, role, user_obj)
        
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

# Models (matching our SQL schema exactly)
class Manager(db.Model):
    __tablename__ = 'manager'
    SSN = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))

class Address(db.Model):
    __tablename__ = 'address'
    road_name = db.Column(db.String(100), primary_key=True)
    number = db.Column(db.String(10), primary_key=True)
    city = db.Column(db.String(100), primary_key=True)

class Client(db.Model):
    __tablename__ = 'client'
    email = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))
    
    addresses = db.relationship('ClientAddress', backref='client')
    credit_cards = db.relationship('CreditCard', backref='client')
    rents = db.relationship('Rent', backref='client')
    reviews = db.relationship('Review', backref='client')

class Driver(db.Model):
    __tablename__ = 'driver'
    name = db.Column(db.String(100), primary_key=True)
    road_name = db.Column(db.String(100))
    number = db.Column(db.String(10))
    city = db.Column(db.String(100))
    
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['road_name', 'number', 'city'],
            ['address.road_name', 'address.number', 'address.city']
        ),
    )
    
    models = db.relationship('DriverModel', backref='driver')
    rents = db.relationship('Rent', backref='driver')
    reviews = db.relationship('Review', backref='driver')

class Car(db.Model):
    __tablename__ = 'car'
    CarID = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50))
    
    models = db.relationship('Model', backref='car')

class Model(db.Model):
    __tablename__ = 'model'
    model_id = db.Column(db.Integer, primary_key=True)
    CarID = db.Column(db.Integer, db.ForeignKey('car.CarID'), primary_key=True)
    color = db.Column(db.String(30))
    construction_year = db.Column(db.Integer)
    transmission = db.Column(db.String(20))
    
    driver_models = db.relationship('DriverModel', backref='model')
    rents = db.relationship('Rent', backref='model')

class CreditCard(db.Model):
    __tablename__ = 'creditcard'
    card_number = db.Column(db.String(20), primary_key=True)
    client_email = db.Column(db.String(100), db.ForeignKey('client.email'), nullable=False)
    road_name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['road_name', 'number', 'city'],
            ['address.road_name', 'address.number', 'address.city']
        ),
    )

class ClientAddress(db.Model):
    __tablename__ = 'clientaddress'
    client_email = db.Column(db.String(100), db.ForeignKey('client.email'), primary_key=True)
    road_name = db.Column(db.String(100), primary_key=True)
    number = db.Column(db.String(10), primary_key=True)
    city = db.Column(db.String(100), primary_key=True)
    
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['road_name', 'number', 'city'],
            ['address.road_name', 'address.number', 'address.city']
        ),
    )

class Rent(db.Model):
    __tablename__ = 'rent'
    rent_id = db.Column(db.Integer, primary_key=True)
    rent_date = db.Column(db.Date, nullable=False)
    client_email = db.Column(db.String(100), db.ForeignKey('client.email'), nullable=False)
    driver_name = db.Column(db.String(100), db.ForeignKey('driver.name'), nullable=False)
    model_id = db.Column(db.Integer, nullable=False)
    car_id = db.Column(db.Integer, nullable=False)
    
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['model_id', 'car_id'],
            ['model.model_id', 'model.CarID']
        ),
    )

class DriverModel(db.Model):
    __tablename__ = 'drivermodel'
    driver_name = db.Column(db.String(100), db.ForeignKey('driver.name'), primary_key=True)
    model_id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, primary_key=True)
    
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['model_id', 'car_id'],
            ['model.model_id', 'model.CarID']
        ),
    )

class Review(db.Model):
    __tablename__ = 'review'
    review_id = db.Column(db.Integer, primary_key=True)
    driver_name = db.Column(db.String(100), db.ForeignKey('driver.name'), nullable=False)
    client_email = db.Column(db.String(100), db.ForeignKey('client.email'), nullable=False)
    rating = db.Column(db.Integer, db.CheckConstraint('rating BETWEEN 0 AND 5'))
    message = db.Column(db.Text)