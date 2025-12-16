// Global variables
let currentUser = null;
let userAllergies = [];

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in
    checkUserLogin();
    
    // Event listeners for dashboard options
    document.getElementById('manual-check-btn').addEventListener('click', function() {
        const manualModal = new bootstrap.Modal(document.getElementById('manualEntryModal'));
        manualModal.show();
    });
    
    document.getElementById('image-upload-btn').addEventListener('click', function() {
        const imageModal = new bootstrap.Modal(document.getElementById('imageUploadModal'));
        imageModal.show();
    });
    
    // Event listener for manual ingredient check
    document.getElementById('check-ingredients-btn').addEventListener('click', checkManualIngredients);
    
    // Event listener for image analysis
    document.getElementById('analyze-image-btn').addEventListener('click', analyzeFoodImage);
    
    // Event listener for file input change
    document.getElementById('food-image').addEventListener('change', handleImagePreview);
    
    // Navigation event listeners
    document.getElementById('dashboard-link').addEventListener('click', function(e) {
        e.preventDefault();
        // Already on dashboard
    });
    
    document.getElementById('profile-link').addEventListener('click', function(e) {
        e.preventDefault();
        alert('Profile management feature coming soon!');
    });
    
    document.getElementById('logout-link').addEventListener('click', function(e) {
        e.preventDefault();
        logoutUser();
    });
});

// Check if user is logged in
function checkUserLogin() {
    // Get user data from session (in a real app, this would come from the server)
    const userData = sessionStorage.getItem('allercheckUser');
    if (userData) {
        currentUser = JSON.parse(userData);
        userAllergies = currentUser.allergies || [];
        showDashboard();
    } else {
        // Redirect to landing page if not logged in
        window.location.href = 'landing.html';
    }
}

// Show dashboard with user information
function showDashboard() {
    // Update user information
    document.getElementById('user-name').textContent = currentUser.name || 'User';
    document.getElementById('user-allergies').textContent = userAllergies.join(', ');
}

// Check manual ingredients for allergens
function checkManualIngredients() {
    const ingredientsInput = document.getElementById('ingredients-input').value;
    
    if (!ingredientsInput.trim()) {
        alert('Please enter some ingredients to check');
        return;
    }
    
    // Split ingredients by commas or new lines
    const ingredients = ingredientsInput.split(/[,|\n]+/).map(item => item.trim()).filter(item => item);
    
    // Analyze ingredients
    const analysisResult = analyzeIngredientsLocally(ingredients, userAllergies);
    
    // Display results
    displayResults(analysisResult);
    
    // Close modal
    const manualModal = bootstrap.Modal.getInstance(document.getElementById('manualEntryModal'));
    manualModal.hide();
}

// Analyze ingredients against user allergies (client-side version)
function analyzeIngredientsLocally(ingredients, allergies) {
    // Common allergens and their variations
    const allergenDatabase = {
        'peanuts': ['peanut', 'peanuts', 'groundnut', 'groundnuts'],
        'tree-nuts': ['almond', 'almonds', 'walnut', 'walnuts', 'cashew', 'cashews', 'pecan', 'pecans', 'pistachio', 'pistachios', 'hazelnut', 'hazelnuts', 'brazil nut', 'brazil nuts', 'macadamia nut', 'macadamia nuts'],
        'milk': ['milk', 'dairy', 'cheese', 'cheeses', 'butter', 'cream', 'yogurt', 'yoghurt', 'casein', 'whey', 'lactose'],
        'eggs': ['egg', 'eggs', 'albumin'],
        'fish': ['fish', 'fishes', 'salmon', 'tuna', 'cod', 'trout', 'bass', 'anchovy', 'herring', 'mackerel', 'sardine'],
        'shellfish': ['shrimp', 'prawn', 'crab', 'lobster', 'scallops', 'mussels', 'oysters', 'clams', 'squid', 'octopus'],
        'soy': ['soy', 'soya', 'soybean', 'soybeans', 'tofu', 'tempeh', 'edamame', 'miso', 'natto'],
        'wheat': ['wheat', 'gluten', 'flour', 'bread', 'pasta', 'noodles', 'semolina', 'bulgur', 'couscous'],
        'sesame': ['sesame', 'tahini', 'halvah', 'gingelly'],
        'mustard': ['mustard', 'mustard seed', 'mustard greens'],
        'celery': ['celery', 'celeriac', 'celery root'],
        'sulfites': ['sulfite', 'sulfur dioxide', 'sodium bisulfite', 'potassium bisulfite'],
        'lupin': ['lupin', 'lupini beans'],
        'mollusks': ['mollusk', 'mollusks', 'snail', 'snails', 'slug', 'slugs']
    };
    
    // Check against user allergies
    const detectedAllergens = [];
    
    for (const ingredient of ingredients) {
        for (const userAllergy of allergies) {
            // Check direct match
            if (ingredient.toLowerCase().includes(userAllergy.toLowerCase())) {
                detectedAllergens.push({
                    allergen: userAllergy,
                    ingredient: ingredient,
                    matchType: 'direct'
                });
                continue;
            }
            
            // Check against allergen database variations
            if (allergenDatabase[userAllergy]) {
                for (const variation of allergenDatabase[userAllergy]) {
                    if (ingredient.toLowerCase().includes(variation.toLowerCase())) {
                        detectedAllergens.push({
                            allergen: userAllergy,
                            ingredient: ingredient,
                            matchType: 'variation',
                            variation: variation
                        });
                        break;
                    }
                }
            }
        }
    }
    
    return {
        ingredientsChecked: ingredients.length,
        allergensDetected: detectedAllergens,
        isSafe: detectedAllergens.length === 0,
        detectedIngredients: ingredients
    };
}

// Analyze food image with AI
function analyzeFoodImage() {
    // Check if an image was selected
    const imageInput = document.getElementById('food-image');
    if (!imageInput.files || imageInput.files.length === 0) {
        alert('Please select an image to analyze');
        return;
    }
    
    const file = imageInput.files[0];
    
    // Show loading state
    const analyzeBtn = document.getElementById('analyze-image-btn');
    const originalText = analyzeBtn.innerHTML;
    analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing with AI...';
    analyzeBtn.disabled = true;
    
    // Read the image file
    const reader = new FileReader();
    reader.onload = function(e) {
        const imageData = e.target.result;
        
        // Prepare data for API call
        const requestData = {
            allergies: userAllergies,
            image: imageData
        };
        
        // If user is logged in, include user ID for history tracking
        if (currentUser && currentUser.id) {
            requestData.user_id = currentUser.id;
        }
        
        // Call AI analysis API
        fetch('api/analyze-image.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Display results
                displayResults(data.data);
                
                // Close modal
                const imageModal = bootstrap.Modal.getInstance(document.getElementById('imageUploadModal'));
                imageModal.hide();
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during image analysis. Please try again.');
        })
        .finally(() => {
            // Restore button state
            analyzeBtn.innerHTML = originalText;
            analyzeBtn.disabled = false;
        });
    };
    
    reader.readAsDataURL(file);
}

// Handle image preview
function handleImagePreview(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            const previewImage = document.getElementById('preview-image');
            previewImage.src = event.target.result;
            previewImage.style.display = 'block';
            
            // Hide placeholder
            document.getElementById('upload-placeholder').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

// Display analysis results
function displayResults(result) {
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('analysis-results');
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
    
    // Generate results HTML
    let resultsHTML = '';
    
    if (result.isSafe) {
        resultsHTML = `
            <div class="alert alert-success text-center">
                <h4><i class="fas fa-check-circle"></i> Safe to Eat!</h4>
                <p>No allergens detected in the analyzed ingredients.</p>
            </div>
        `;
    } else {
        resultsHTML = `
            <div class="alert alert-danger text-center">
                <h4><i class="fas fa-exclamation-triangle"></i> Allergen Alert!</h4>
                <p>Potential allergens detected. Please review the details below.</p>
            </div>
        `;
    }
    
    resultsHTML += `
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list"></i> Analysis Summary</h5>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Ingredients Checked
                                <span class="badge bg-primary rounded-pill">${result.ingredientsChecked}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Allergens Detected
                                <span class="badge bg-danger rounded-pill">${result.allergensDetected.length}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Status
                                <span class="badge ${result.isSafe ? 'bg-success' : 'bg-danger'} rounded-pill">
                                    ${result.isSafe ? 'Safe' : 'Unsafe'}
                                </span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-allergies"></i> Detected Allergens</h5>
                    </div>
                    <div class="card-body">
    `;
    
    if (result.allergensDetected.length > 0) {
        resultsHTML += '<ul class="list-group list-group-flush">';
        result.allergensDetected.forEach(allergen => {
            resultsHTML += `
                <li class="list-group-item">
                    <strong>${allergen.allergen}</strong> detected in <em>${allergen.ingredient}</em>
                    ${allergen.matchType === 'variation' ? `<br><small class="text-muted">Matched variation: ${allergen.variation}</small>` : ''}
                </li>
            `;
        });
        resultsHTML += '</ul>';
    } else {
        resultsHTML += '<p class="text-muted">No allergens detected.</p>';
    }
    
    resultsHTML += `
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mt-3">
            <div class="card-header">
                <h5><i class="fas fa-clipboard-list"></i> Detected Ingredients</h5>
            </div>
            <div class="card-body">
                <p>${result.detectedIngredients.join(', ')}</p>
            </div>
        </div>
    `;
    
    resultsContainer.innerHTML = resultsHTML;
}

// Logout user
function logoutUser() {
    // Clear user data from session storage
    sessionStorage.removeItem('allercheckUser');
    
    // Redirect to landing page
    window.location.href = 'landing.html';
}