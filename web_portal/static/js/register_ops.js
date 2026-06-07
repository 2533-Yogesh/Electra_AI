const regForm = document.getElementById('registerForm');
const registerAlert = document.getElementById('register-alert');

if (regForm) {
    regForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        // 🌟 FIXED: Only target elements that are active inside your register.html code
        const username = document.getElementById('regUsername').value.trim();
        const role = document.getElementById('regRole').value;
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regConfirmPassword').value;

        // Reset status banner visibility elements smoothly
        registerAlert.style.display = 'none';
        registerAlert.style.background = '';
        registerAlert.style.color = '';
        registerAlert.style.border = '';

        let errors = [];

        // 🌟 FIXED: Adjusted boundaries to accept classic 4-to-5 character names safely
        if (username.length < 4) {
            errors.push("Username must be at least 4 characters long.");
        }

        if (!role) {
            errors.push("Please select a designated Grid Operational Scope.");
        }

        if (password.length < 6) {
            errors.push("Security Alert: Created password profile is too weak (min 6 characters).");
        }

        if (password !== confirmPassword) {
            errors.push("Password confirmation coordinates do not match.");
        }

        if (errors.length > 0) {
            showRegisterStatus(errors.join(' | '), 'error');
            return;
        }

        try {
            showRegisterStatus("⏳ Registering profile with cloud system core...", "info");

            // Post the registration data over the local loop to your Python server
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    role: role,
                    password: password
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showRegisterStatus(result.message, 'success');
                regForm.reset();
                
                // Smoothly slide back to the login window pane after a successful registration
                setTimeout(() => {
                    const container = document.getElementById('container');
                    if (container) container.classList.remove('active');
                }, 2200);
            } else {
                throw new Error(result.message || "Registration provisioning processing failed.");
            }

        } catch (error) {
            showRegisterStatus(error.message, 'error');
        }
    });
}

function showRegisterStatus(msg, type) {
    registerAlert.style.display = 'block';
    if (type === 'error') {
        registerAlert.style.background = '#fce8e6';
        registerAlert.style.color = '#c5221f';
        registerAlert.style.border = '1px solid #fad2cf';
    } else if (type === 'info') {
        registerAlert.style.background = '#e8f0fe';
        registerAlert.style.color = '#1a73e8';
        registerAlert.style.border = '1px solid #d2e3fc';
    } else {
        registerAlert.style.background = '#e6f4ea';
        registerAlert.style.color = '#137333';
        registerAlert.style.border = '1px solid #ceead6';
    }
    registerAlert.innerText = msg;
}