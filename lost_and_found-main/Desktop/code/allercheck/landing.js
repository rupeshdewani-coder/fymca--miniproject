// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    // Navigation buttons
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    const heroRegisterBtn = document.getElementById('hero-register-btn');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    
    // Modals
    const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
    const registerModal = new bootstrap.Modal(document.getElementById('registerModal'));
    
    // Forms
    const loginForm = document.getElementById('login-form');
    const registrationForm = document.getElementById('registration-form');
    const registrationError = document.getElementById('registration-error');
    
    // Event listeners
    loginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        loginModal.show();
    });
    
    registerBtn.addEventListener('click', (e) => {
        e.preventDefault();
        registerModal.show();
    });
    
    heroRegisterBtn.addEventListener('click', (e) => {
        e.preventDefault();
        registerModal.show();
    });
    
    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginModal.hide();
        setTimeout(() => {
            registerModal.show();
        }, 300);
    });
    
    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerModal.hide();
        setTimeout(() => {
            loginModal.show();
        }, 300);
    });
    
    // Login form submission
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        // Simple validation
        if (!email || !password) {
            alert('Please fill in all fields');
            return;
        }
        
        // Prepare data for API call
        const loginData = {
            email: email,
            password: password
        };
        
        // Show loading state
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Logging in...';
        submitBtn.disabled = true;
        
        // Call login API
        fetch('api/login.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(loginData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Store user data in sessionStorage
                sessionStorage.setItem('allercheckUser', JSON.stringify(data.user));
                
                // Hide modal and redirect to dashboard
                loginModal.hide();
                window.location.href = 'index.html';
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during login. Please try again.');
        })
        .finally(() => {
            // Restore button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    });
    
    // Registration form submission
    registrationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Hide any previous error messages
        registrationError.style.display = 'none';
        
        const fullName = document.getElementById('full-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const selectedAllergies = Array.from(document.getElementById('allergies').selectedOptions).map(option => option.value);
        const otherAllergies = document.getElementById('other-allergies').value.split(',').map(a => a.trim()).filter(a => a);
        
        // Combine selected allergies with other allergies
        const allAllergies = [...selectedAllergies, ...otherAllergies];
        
        // Simple validation
        if (!fullName || !email || !password) {
            showError('Please fill in all required fields');
            return;
        }
        
        if (allAllergies.length === 0) {
            showError('Please select at least one allergy');
            return;
        }
        
        // Prepare data for API call
        const registrationData = {
            full_name: fullName,
            email: email,
            password: password,
            allergies: allAllergies
        };
        
        // Show loading state
        const submitBtn = registrationForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Registering...';
        submitBtn.disabled = true;
        
        // Call registration API
        fetch('api/register.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(registrationData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Registration successful! You can now login.');
                registerModal.hide();
                
                // Clear form
                registrationForm.reset();
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('An error occurred during registration. Please try again.');
        })
        .finally(() => {
            // Restore button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    });
    
    // Function to show error messages
    function showError(message) {
        registrationError.textContent = message;
        registrationError.style.display = 'block';
        
        // Scroll to error message
        registrationError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});