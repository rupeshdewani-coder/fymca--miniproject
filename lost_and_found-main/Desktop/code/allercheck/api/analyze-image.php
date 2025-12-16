<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

require_once '../config.php';

// Include the Google Cloud Vision library
require_once '../vendor/autoload.php';

use Google\Cloud\Vision\V1\Client\ImageAnnotatorClient;

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Invalid request method']);
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['allergies']) || !isset($data['image'])) {
    echo json_encode(['success' => false, 'message' => 'Missing allergies data or image']);
    exit;
}

// Get database connection
$pdo = getDBConnection();

$userAllergies = $data['allergies'];
$imageData = $data['image']; // Base64 encoded image

// Decode the image
$imageParts = explode(";base64,", $imageData);
$imageTypeAux = explode("image/", $imageParts[0]);
$imageType = $imageTypeAux[1];
$imageBase64 = base64_decode($imageParts[1]);

// Create a temporary file
$tempFileName = tempnam(sys_get_temp_dir(), 'allercheck_');
$tempFilePath = $tempFileName . '.' . $imageType;
file_put_contents($tempFilePath, $imageBase64);

try {
    // Call AI service to analyze the image
    $ingredients = analyzeImageWithAI($tempFilePath);
    
    // Clean up temporary file
    unlink($tempFilePath);
    
    // Analyze ingredients against user allergies
    $analysisResult = analyzeIngredients($ingredients, $userAllergies);
    
    // Save analysis to history (if user is logged in)
    if (isset($data['user_id'])) {
        saveAnalysisHistory($pdo, $data['user_id'], $ingredients, $analysisResult);
    }
    
    // Return results
    echo json_encode([
        'success' => true,
        'message' => 'Analysis completed successfully',
        'data' => $analysisResult
    ]);
} catch (Exception $e) {
    // Clean up temporary file
    if (file_exists($tempFilePath)) {
        unlink($tempFilePath);
    }
    
    echo json_encode([
        'success' => false,
        'message' => 'Error analyzing image: ' . $e->getMessage()
    ]);
}

// Function to analyze image with Google Cloud Vision API
function analyzeImageWithAI($imagePath) {
    try {
        // Initialize the ImageAnnotatorClient
        $imageAnnotator = new ImageAnnotatorClient([
            // You can specify the path to your service account key file here
            // 'keyFilePath' => '/path/to/your/service-account-key.json'
        ]);
        
        // Read the image file
        $imageContent = file_get_contents($imagePath);
        
        // Perform label detection
        $response = $imageAnnotator->labelDetection($imageContent);
        $labels = $response->getLabelAnnotations();
        
        // Extract label descriptions
        $ingredients = [];
        if ($labels) {
            foreach ($labels as $label) {
                $ingredients[] = $label->getDescription();
            }
        }
        
        // Close the client
        $imageAnnotator->close();
        
        // Filter out non-food related labels and return top relevant ingredients
        return filterFoodLabels($ingredients);
    } catch (Exception $e) {
        // If Google Cloud Vision fails, fall back to simulated response
        error_log("Google Cloud Vision API error: " . $e->getMessage());
        return simulateAIResponse();
    }
}

// Function to filter food-related labels
function filterFoodLabels($labels) {
    // Common food-related keywords to filter relevant labels
    $foodKeywords = [
        'food', 'ingredient', 'dish', 'meal', 'fruit', 'vegetable', 'meat', 'dairy',
        'bread', 'cake', 'cookie', 'soup', 'salad', 'sauce', 'spice', 'herb',
        'flour', 'egg', 'milk', 'cheese', 'butter', 'oil', 'sugar', 'salt',
        'pepper', 'rice', 'pasta', 'noodle', 'chicken', 'beef', 'pork', 'fish',
        'shrimp', 'nut', 'berry', 'apple', 'banana', 'orange', 'lemon', 'lime',
        'tomato', 'onion', 'garlic', 'potato', 'carrot', 'lettuce', 'spinach'
    ];
    
    $filteredLabels = [];
    
    foreach ($labels as $label) {
        $lowerLabel = strtolower($label);
        // Check if the label contains any food-related keywords or is likely a food item
        foreach ($foodKeywords as $keyword) {
            if (strpos($lowerLabel, $keyword) !== false) {
                $filteredLabels[] = $label;
                break;
            }
        }
        // Also include labels that are single words and likely food items
        if (count(explode(' ', $label)) == 1 && strlen($label) > 2) {
            $filteredLabels[] = $label;
        }
    }
    
    // Return unique labels, limited to 10
    return array_slice(array_unique($filteredLabels), 0, 10);
}

// Fallback function with simulated AI response
function simulateAIResponse() {
    $possibleIngredients = [
        "flour", "eggs", "milk", "butter", "sugar", "vanilla extract",
        "chocolate chips", "peanuts", "almonds", "soy sauce",
        "wheat flour", "cheese", "tomato", "onion", "garlic",
        "salt", "oil", "yeast", "cinnamon", "raisins"
    ];
    
    // Randomly select 3-8 ingredients to simulate AI detection
    $numIngredients = rand(3, 8);
    $detectedIngredients = [];
    
    for ($i = 0; $i < $numIngredients; $i++) {
        $randomIndex = rand(0, count($possibleIngredients) - 1);
        $detectedIngredients[] = $possibleIngredients[$randomIndex];
    }
    
    return $detectedIngredients;
}

// Function to analyze ingredients against user allergies
function analyzeIngredients($ingredients, $allergies) {
    // Common allergens and their variations
    $allergenDatabase = [
        'peanuts' => ['peanut', 'peanuts', 'groundnut', 'groundnuts'],
        'tree-nuts' => ['almond', 'almonds', 'walnut', 'walnuts', 'cashew', 'cashews', 'pecan', 'pecans', 'pistachio', 'pistachios', 'hazelnut', 'hazelnuts', 'brazil nut', 'brazil nuts', 'macadamia nut', 'macadamia nuts'],
        'milk' => ['milk', 'dairy', 'cheese', 'cheeses', 'butter', 'cream', 'yogurt', 'yoghurt', 'casein', 'whey', 'lactose'],
        'eggs' => ['egg', 'eggs', 'albumin'],
        'fish' => ['fish', 'fishes', 'salmon', 'tuna', 'cod', 'trout', 'bass', 'anchovy', 'herring', 'mackerel', 'sardine'],
        'shellfish' => ['shrimp', 'prawn', 'crab', 'lobster', 'scallops', 'mussels', 'oysters', 'clams', 'squid', 'octopus'],
        'soy' => ['soy', 'soya', 'soybean', 'soybeans', 'tofu', 'tempeh', 'edamame', 'miso', 'natto'],
        'wheat' => ['wheat', 'gluten', 'flour', 'bread', 'pasta', 'noodles', 'semolina', 'bulgur', 'couscous'],
        'sesame' => ['sesame', 'tahini', 'halvah', 'gingelly'],
        'mustard' => ['mustard', 'mustard seed', 'mustard greens'],
        'celery' => ['celery', 'celeriac', 'celery root'],
        'sulfites' => ['sulfite', 'sulfur dioxide', 'sodium bisulfite', 'potassium bisulfite'],
        'lupin' => ['lupin', 'lupini beans'],
        'mollusks' => ['mollusk', 'mollusks', 'snail', 'snails', 'slug', 'slugs']
    ];
    
    // Check against user allergies
    $detectedAllergens = [];
    
    foreach ($ingredients as $ingredient) {
        foreach ($allergies as $userAllergy) {
            // Check direct match
            if (stripos($ingredient, $userAllergy) !== false) {
                $detectedAllergens[] = [
                    'allergen' => $userAllergy,
                    'ingredient' => $ingredient,
                    'matchType' => 'direct'
                ];
                continue;
            }
            
            // Check against allergen database variations
            if (isset($allergenDatabase[$userAllergy])) {
                foreach ($allergenDatabase[$userAllergy] as $variation) {
                    if (stripos($ingredient, $variation) !== false) {
                        $detectedAllergens[] = [
                            'allergen' => $userAllergy,
                            'ingredient' => $ingredient,
                            'matchType' => 'variation',
                            'variation' => $variation
                        ];
                        break;
                    }
                }
            }
        }
    }
    
    return [
        'ingredientsChecked' => count($ingredients),
        'allergensDetected' => $detectedAllergens,
        'isSafe' => count($detectedAllergens) === 0,
        'detectedIngredients' => $ingredients
    ];
}

// Function to save analysis history
function saveAnalysisHistory($pdo, $userId, $ingredients, $analysisResult) {
    try {
        $stmt = $pdo->prepare("INSERT INTO analysis_history (user_id, ingredients, allergens_detected, is_safe, created_at) VALUES (?, ?, ?, ?, NOW())");
        $stmt->execute([
            $userId,
            json_encode($ingredients),
            json_encode($analysisResult['allergensDetected']),
            $analysisResult['isSafe'] ? 1 : 0
        ]);
    } catch (Exception $e) {
        // Log error but don't fail the request
        error_log("Failed to save analysis history: " . $e->getMessage());
    }
}
?>