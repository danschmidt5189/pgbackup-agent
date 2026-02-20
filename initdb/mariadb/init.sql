-- Sample databases for MariaDB integration tests.
-- This script is mounted at /docker-entrypoint-initdb.d/ and
-- runs automatically on first container start.

-- Note: MARIADB_DATABASE=testdb creates the first database.
-- We create additional databases here.
-- The init scripts run as root, so we can create and grant.

CREATE DATABASE IF NOT EXISTS racing;
GRANT ALL PRIVILEGES ON racing.* TO 'mdbuser'@'%';

USE racing;
CREATE TABLE circuits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
);
INSERT INTO circuits (name, country) VALUES
    ('Spa-Francorchamps', 'Belgium'),
    ('Monza', 'Italy'),
    ('Suzuka', 'Japan');

CREATE TABLE drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team VARCHAR(100)
);
INSERT INTO drivers (name, team) VALUES
    ('Max Verstappen', 'Red Bull'),
    ('Lewis Hamilton', 'Ferrari'),
    ('Lando Norris', 'McLaren');

-- Add a table with data to the default testdb as well.
USE testdb;
CREATE TABLE widgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    weight DECIMAL(6, 2)
);
INSERT INTO widgets (name, weight) VALUES
    ('Sprocket', 1.25),
    ('Cog', 0.75),
    ('Gear', 2.50);
