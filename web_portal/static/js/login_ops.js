const loginForm = document.getElementById('loginForm');
const loginAlert = document.getElementById('login-alert');

loginForm.addEventListener('submit', async function (e) {
    e.preventDefault(); // Stop standard browser page re-loads

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    // Reset status banner elements visibility states smoothly
    loginAlert.style.display = 'none';
    loginAlert.style.background = '';
    loginAlert.style.color = '';
    loginAlert.style.border = '';

    if (username === '' || password === '') {
        showLoginError("⚠️ Configuration fields cannot be left blank.");
        return;
    }

    try {
        // Stream validation data to Flask login routing path
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            loginAlert.style.display = 'block';
            loginAlert.style.background = '#e6f4ea';
            loginAlert.style.color = '#137333';
            loginAlert.style.border = '1px solid #dadce0';
            loginAlert.innerText = "🚀 Access Granted! Shifting cockpit frames...";
            
            // Redirect the user to the dashboard smoothly
            setTimeout(() => {
                window.location.href = result.redirect;
            }, 800);
        } else {
            // Throw custom messaging coming back directly from our Neon Cloud database checks
            throw new Error(result.message || "Authorization rejected.");
        }

    } catch (error) {
        showLoginError(error.message);
    }
});

function showLoginError(msg) {
    loginAlert.style.display = 'block';
    loginAlert.style.background = '#fce8e6';
    loginAlert.style.color = '#c5221f';
    loginAlert.style.border = '1px solid #fad2cf';
    loginAlert.innerText = msg;
}