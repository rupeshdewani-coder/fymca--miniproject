-- allercheck Database Schema
-- Create database
DROP DATABASE IF EXISTS allercheck;
CREATE DATABASE allercheck;
USE allercheck;

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Allergies table
CREATE TABLE allergies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- User Allergies mapping table
CREATE TABLE user_allergies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    allergy_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (allergy_id) REFERENCES allergies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_allergy (user_id, allergy_id)
);

-- Insert common allergies
INSERT INTO allergies (name, description) VALUES
('peanuts', 'Allergic reaction to peanuts'),
('tree-nuts', 'Allergic reaction to tree nuts like almonds, walnuts, etc.'),
('milk', 'Allergic reaction to cow''s milk and dairy products'),
('eggs', 'Allergic reaction to chicken eggs'),
('fish', 'Allergic reaction to finned fish'),
('shellfish', 'Allergic reaction to crustaceans and mollusks'),
('soy', 'Allergic reaction to soybeans and soy products'),
('wheat', 'Allergic reaction to wheat and gluten-containing products'),
('sesame', 'Allergic reaction to sesame seeds and oil'),
('mustard', 'Allergic reaction to mustard seeds and preparations'),
('celery', 'Allergic reaction to celery and celery salt'),
('sulfites', 'Allergic reaction to sulfur-based preservatives'),
('lupin', 'Allergic reaction to lupin beans and flour'),
('mollusks', 'Allergic reaction to mollusks like clams, oysters, etc.');

-- Analysis history table
CREATE TABLE analysis_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    analysis_type ENUM('manual', 'image') NOT NULL,
    ingredients TEXT,
    result TEXT,
    is_safe BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);