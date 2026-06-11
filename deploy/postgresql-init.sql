CREATE USER stocktracker WITH PASSWORD 'change_me_strong_password';
CREATE DATABASE stocktracker OWNER stocktracker;
GRANT ALL PRIVILEGES ON DATABASE stocktracker TO stocktracker;
