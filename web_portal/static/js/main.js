// Ensure the browser finishes mapping the entire HTML document tree before processing
document.addEventListener('DOMContentLoaded', () => {
    
    // 🧭 1. LAYOUT TOGGLE COMPONENT BINDINGS
    const container = document.querySelector('.container');
    const registerBtn = document.querySelector('.register-btn');
    const loginBtn = document.querySelector('.login-btn');

    // Safe Defensive Execution Gate: Only slide if the target button physically exists
    if (registerBtn && container) {
        registerBtn.addEventListener('click', () => {
            container.classList.add('active');
            console.log("🔄 Portal state shifted: Displaying Registration Layer.");
        });
    } else {
        console.warn("⚠️ Layout Selector Missing: '.register-btn' or '.container' could not be mapped.");
    }

    if (loginBtn && container) {
        loginBtn.addEventListener('click', () => {
            container.classList.remove('active');
            console.log("🔄 Portal state shifted: Displaying Login Layer.");
        });
    }
});