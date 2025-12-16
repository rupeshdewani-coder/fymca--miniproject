<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

require_once '../config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Invalid request method']);
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['full_name']) || !isset($data['email']) || !isset($data['password']) || !isset($data['allergies'])) {
    echo json_encode(['success' => false, 'message' => 'Missing required fields']);
    exit;
}

// Get database connection
$pdo = getDBConnection();

$full_name = trim($data['full_name']);
$email = trim($data['email']);
$password = password_hash($data['password'], PASSWORD_DEFAULT);
$allergies = $data['allergies'];

try {
    // Check if user already exists
    $stmt = $pdo->prepare("SELECT id FROM users WHERE email = ?");
    $stmt->execute([$email]);
    
    if ($stmt->rowCount() > 0) {
        echo json_encode(['success' => false, 'message' => 'User with this email already exists. Please use a different email or login instead.']);
        exit;
    }
    
    // Validate email format
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo json_encode(['success' => false, 'message' => 'Please provide a valid email address']);
        exit;
    }
    
    // Validate password strength (at least 6 characters)
    if (strlen($data['password']) < 6) {
        echo json_encode(['success' => false, 'message' => 'Password must be at least 6 characters long']);
        exit;
    }
    
    // Validate that allergies array is not empty
    if (empty($allergies) || !is_array($allergies)) {
        echo json_encode(['success' => false, 'message' => 'Please select at least one allergy']);
        exit;
    }
    
    // Insert user
    $stmt = $pdo->prepare("INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)");
    $result = $stmt->execute([$full_name, $email, $password]);
    
    if (!$result) {
        echo json_encode(['success' => false, 'message' => 'Failed to create user account. Please try again.']);
        exit;
    }
    
    $user_id = $pdo->lastInsertId();
    
    // Insert user allergies
    $allergyInsertSuccess = true;
    $allergyInsertError = "";
    
    foreach ($allergies as $allergy) {
        // Get allergy ID
        $stmt = $pdo->prepare("SELECT id FROM allergies WHERE name = ?");
        $stmt->execute([$allergy]);
        $allergy_data = $stmt->fetch();
        
        if ($allergy_data) {
            $stmt = $pdo->prepare("INSERT INTO user_allergies (user_id, allergy_id) VALUES (?, ?)");
            $result = $stmt->execute([$user_id, $allergy_data['id']]);
            
            if (!$result) {
                $allergyInsertSuccess = false;
                $allergyInsertError = "Failed to save allergy information";
                break;
            }
        }
    }
    
    if ($allergyInsertSuccess) {
        echo json_encode(['success' => true, 'message' => 'User registered successfully! You can now login.', 'user_id' => $user_id]);
    } else {
        // Try to clean up by deleting the user if allergy insertion failed
        $stmt = $pdo->prepare("DELETE FROM users WHERE id = ?");
        $stmt->execute([$user_id]);
        
        echo json_encode(['success' => false, 'message' => $allergyInsertError]);
    }
} catch (PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => 'Registration failed: ' . $e->getMessage()]);
}
?>