-- STEP 1: STRONG ENTITIES & COMPOSITE ATTRIBUTES
-- Manager entity
CREATE TABLE Manager (
    SSN VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);

-- Address (composite PK)
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

-- CreditCard entity
CREATE TABLE CreditCard (
    card_number VARCHAR(20) PRIMARY KEY
);

-- Rent entity
CREATE TABLE Rent (
    rent_id SERIAL PRIMARY KEY,
    rent_date DATE NOT NULL
);

-- Driver entity
CREATE TABLE Driver (
    name VARCHAR(100) PRIMARY KEY
);

-- Car entity
CREATE TABLE Car (
    CarID SERIAL PRIMARY KEY,
    brand VARCHAR(50)
);

-- STEP 2: WEAK ENTITIES
-- Model (weak entity)
CREATE TABLE Model (
    model_id INT,
    CarID INT,
    color VARCHAR(30),
    construction_year INT,
    transmission VARCHAR(20),
    PRIMARY KEY (model_id, CarID),
    FOREIGN KEY (CarID) REFERENCES Car(CarID)
);

-- Review (weak entity)
CREATE TABLE Review (
    review_id INT,
    driver_name VARCHAR(100),
    rating INT CHECK (rating BETWEEN 0 AND 5),
    message TEXT,
    PRIMARY KEY (review_id, driver_name),
    FOREIGN KEY (driver_name) REFERENCES Driver(name)
);


-- STEP 3: MULTI-VALUED ATTRIBUTES
-- Clients can have multiple addresses
CREATE TABLE ClientAddress (
    client_email VARCHAR(100),
    road_name VARCHAR(100),
    number VARCHAR(10),
    city VARCHAR(100),
    PRIMARY KEY (client_email, road_name, number, city),
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (road_name, number, city) REFERENCES Address(road_name, number, city)
);

-- Clients can have multiple credit cards
CREATE TABLE ClientCreditCard (
    client_email VARCHAR(100),
    card_number VARCHAR(20),
    PRIMARY KEY (client_email, card_number),
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (card_number) REFERENCES CreditCard(card_number)
);


-- STEP 4: RELATIONSHIPS
-- Client → Rent (0:N : 1:1) — Separate table
CREATE TABLE ClientRent (
    client_email VARCHAR(100),
    rent_id INT PRIMARY KEY,
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (rent_id) REFERENCES Rent(rent_id)
);

-- Driver → Rent (0:N : 1:1) — Separate table
CREATE TABLE RentDriver (
    rent_id INT PRIMARY KEY,
    driver_name VARCHAR(100),
    FOREIGN KEY (rent_id) REFERENCES Rent(rent_id),
    FOREIGN KEY (driver_name) REFERENCES Driver(name)
);

-- Rent → Model (1:1 : 0:1) — Separate table
CREATE TABLE RentModel (
    rent_id INT PRIMARY KEY,
    model_id INT,
    car_id INT,
    FOREIGN KEY (rent_id) REFERENCES Rent(rent_id),
    FOREIGN KEY (model_id, car_id) REFERENCES Model(model_id, CarID)
);

-- Driver → Address (1:1 : 0:1) — Separate table
CREATE TABLE DriverAddress (
    driver_name VARCHAR(100) PRIMARY KEY,
    road_name VARCHAR(100),
    number VARCHAR(10),
    city VARCHAR(100),
    FOREIGN KEY (driver_name) REFERENCES Driver(name),
    FOREIGN KEY (road_name, number, city) REFERENCES Address(road_name, number, city)
);

-- Driver → Model (0:N) — Separate table
CREATE TABLE DriverModel (
    driver_name VARCHAR(100),
    model_id INT,
    car_id INT,
    PRIMARY KEY (driver_name, model_id, car_id),
    FOREIGN KEY (driver_name) REFERENCES Driver(name),
    FOREIGN KEY (model_id, car_id) REFERENCES Model(model_id, CarID)
);

-- CreditCard → Address (1:1) — Merge]ing into CreditCard
ALTER TABLE CreditCard
ADD COLUMN road_name VARCHAR(100),
ADD COLUMN number VARCHAR(10),
ADD COLUMN city VARCHAR(100),
ADD CONSTRAINT fk_card_address FOREIGN KEY (road_name, number, city)
    REFERENCES Address(road_name, number, city);

-- Client → Review (0:N : 0:1) — Separate table
CREATE TABLE ClientReview (
    client_email VARCHAR(100),
    review_id INT,
    driver_name VARCHAR(100),
    PRIMARY KEY (client_email, review_id, driver_name),
    FOREIGN KEY (client_email) REFERENCES Client(email),
    FOREIGN KEY (review_id, driver_name) REFERENCES Review(review_id, driver_name)
);
