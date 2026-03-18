-- Create database if not exists
CREATE DATABASE IF NOT EXISTS ledger_db;
USE ledger_db;

-- Set timezone
SET GLOBAL time_zone = '+00:00';

-- Users table will be created by SQLAlchemy
-- This file is for any additional setup or initial data
