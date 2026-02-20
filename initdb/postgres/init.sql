-- Sample databases for Postgres integration tests.
-- This script is mounted at /docker-entrypoint-initdb.d/ and
-- runs automatically on first container start.

-- Database: climbers
CREATE DATABASE climbers;
\c climbers
CREATE TABLE routes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(10) NOT NULL,
    location VARCHAR(100)
);
INSERT INTO routes (name, grade, location) VALUES
    ('The Nose', '5.14a', 'Yosemite'),
    ('Moonlight Buttress', '5.12d', 'Zion'),
    ('Midnight Lightning', 'V8', 'Yosemite');

CREATE TABLE climbers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50)
);
INSERT INTO climbers (name, country) VALUES
    ('Alex Honnold', 'USA'),
    ('Adam Ondra', 'Czech Republic'),
    ('Janja Garnbret', 'Slovenia');

-- Database: athletes
\c postgres
CREATE DATABASE athletes;
\c athletes
CREATE TABLE sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
INSERT INTO sports (name) VALUES
    ('Climbing'),
    ('Trail Running'),
    ('Cycling');

CREATE TABLE competitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sport_id INTEGER REFERENCES sports(id)
);
INSERT INTO competitors (name, sport_id) VALUES
    ('Kilian Jornet', 2),
    ('Courtney Dauwalter', 2),
    ('Tadej Pogacar', 3);
