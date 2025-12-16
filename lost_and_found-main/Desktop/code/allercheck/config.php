<?php
// Database configuration for allercheck with XAMPP
// Configured to work with MySQL on port 3306
define('DB_HOST', 'localhost');
define('DB_USER', 'root');
define('DB_PASS', '');
define('DB_NAME', 'allercheck');
define('DB_PORT', '3306'); // Using port 3306 as requested

// Create connection
function getDBConnection() {
    try {
        $pdo = new PDO("mysql:host=" . DB_HOST . ";port=" . DB_PORT . ";dbname=" . DB_NAME . ";charset=utf8", DB_USER, DB_PASS);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        return $pdo;
    } catch(PDOException $e) {
        // Log the error for debugging
        error_log("Database connection failed: " . $e->getMessage());
        // For XAMPP-only version, we want to show the error
        throw new Exception("Unable to connect to database. Please ensure MySQL is running on port 3306.");
    }
}
?>