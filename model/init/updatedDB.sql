-- STEP 1: ENTITIES WITH ATTRIBUTES
-- Manager entity
CREATE TABLE Manager (
    SSN VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);

-- Address entity
CREATE TABLE Address (
    road_name VARCHAR(100),
    number VARCHAR(10),
    city VARCHAR(100),
    PRIMARY KEY (road_name, number, city)
);

-- Client entity
CREATE TABLE Client (
    email VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100)
);

-- Driver entity
CREATE TABLE Driver (
    name VARCHAR(100) PRIMARY KEY,
    road_name VARCHAR(100),
    number VARCHAR(10),
    city VARCHAR(100),
    FOREIGN KEY (road_name, number, city) REFERENCES Address(road_name, number, city)
);

-- Car entity
CREATE TABLE Car (
    CarID SERIAL PRIMARY KEY,
    brand VARCHAR(50)
);

-- Model entity (weak entity of Car)
CREATE TABLE Model (
    model_id INT,
    CarID INT,
    color VARCHAR(30),
    construction_year INT,
    transmission VARCHAR(20),
    PRIMARY KEY (model_id, CarID),
    FOREIGN KEY (CarID) REFERENCES Car(CarID)
);

-- Credit Card entity (belongs to one client)
CREATE TABLE CreditCard (
    card_number VARCHAR(20) PRIMARY KEY,
    client_email VARCHAR(100) NOT NULL,
    road_name VARCHAR(100) NOT NULL,
    number VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (road_name, number, city) REFERENCES Address(road_name, number, city)
);

-- Client addresses (relationship between Client and Address)
CREATE TABLE ClientAddress (
    client_email VARCHAR(100),
    road_name VARCHAR(100),
    number VARCHAR(10),
    city VARCHAR(100),
    PRIMARY KEY (client_email, road_name, number, city),
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (road_name, number, city) REFERENCES Address(road_name, number, city)
);

-- Rent entity with all relationships
CREATE TABLE Rent (
    rent_id SERIAL PRIMARY KEY,
    rent_date DATE NOT NULL,
    client_email VARCHAR(100) NOT NULL,
    driver_name VARCHAR(100) NOT NULL,
    model_id INT NOT NULL,
    car_id INT NOT NULL,
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (driver_name) REFERENCES Driver(name),
    FOREIGN KEY (model_id, car_id) REFERENCES Model(model_id, CarID)
);

-- Driver-Model relationship (what models a driver can drive)
CREATE TABLE DriverModel (
    driver_name VARCHAR(100),
    model_id INT,
    car_id INT,
    PRIMARY KEY (driver_name, model_id, car_id),
    FOREIGN KEY (driver_name) REFERENCES Driver(name),
    FOREIGN KEY (model_id, car_id) REFERENCES Model(model_id, CarID)
);

-- Review entity with relationships
CREATE TABLE Review (
    review_id SERIAL PRIMARY KEY,
    driver_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(100) NOT NULL,
    rating INT CHECK (rating BETWEEN 0 AND 5),
    message TEXT,
    FOREIGN KEY (driver_name) REFERENCES Driver(name),
    FOREIGN KEY (client_email) REFERENCES Client(email)
);