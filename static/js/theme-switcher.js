// Theme Switcher JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Theme switcher loaded');
    
    // Get stored theme or default to auto
    const storedTheme = localStorage.getItem('theme') || 'auto';
    
    // Function to apply auto theme based on system preference
    function applyAutoTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-bs-theme', 'light');
        }
    }
    
    // Set initial theme
    if (storedTheme === 'auto') {
        applyAutoTheme();
        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAutoTheme);
        }
    } else {
        document.documentElement.setAttribute('data-bs-theme', storedTheme);
    }
    
    // Handle theme cycle button (if exists)
    const themeCycleButton = document.getElementById('themeCycleButton');
    if (themeCycleButton) {
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        // Update button appearance based on current theme
        function updateThemeButton() {
            const currentTheme = localStorage.getItem('theme') || 'auto';
            if (themeIcon && themeText) {
                switch(currentTheme) {
                    case 'light':
                        themeIcon.className = 'bi bi-sun-fill';
                        themeText.textContent = 'Light';
                        break;
                    case 'dark':
                        themeIcon.className = 'bi bi-moon-fill';
                        themeText.textContent = 'Dark';
                        break;
                    default:
                        themeIcon.className = 'bi bi-circle-half';
                        themeText.textContent = 'Auto';
                }
            }
        }
        
        // Cycle through themes: auto -> light -> dark -> auto
        themeCycleButton.addEventListener('click', function() {
            const currentTheme = localStorage.getItem('theme') || 'auto';
            let nextTheme;
            
            switch(currentTheme) {
                case 'auto':
                    nextTheme = 'light';
                    break;
                case 'light':
                    nextTheme = 'dark';
                    break;
                default:
                    nextTheme = 'auto';
            }
            
            // Remove existing system theme change listener
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', applyAutoTheme);
            }
            
            if (nextTheme === 'auto') {
                applyAutoTheme();
                // Re-add system theme change listener for auto mode
                if (window.matchMedia) {
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAutoTheme);
                }
            } else {
                document.documentElement.setAttribute('data-bs-theme', nextTheme);
            }
            
            localStorage.setItem('theme', nextTheme);
            updateThemeButton();
        });
        
        // Set initial button state
        updateThemeButton();
    }
    
    // Handle theme toggles (for dropdown menus)
    const themeToggles = document.querySelectorAll('.theme-toggle');
    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const theme = this.getAttribute('data-bs-theme-value');
            
            // Remove existing system theme change listener
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', applyAutoTheme);
            }
            
            if (theme === 'auto') {
                applyAutoTheme();
                // Re-add system theme change listener for auto mode
                if (window.matchMedia) {
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAutoTheme);
                }
            } else {
                document.documentElement.setAttribute('data-bs-theme', theme);
            }
            
            localStorage.setItem('theme', theme);
            
            // Update active state
            themeToggles.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
        
        // Set initial active state
        if (toggle.getAttribute('data-bs-theme-value') === storedTheme) {
            toggle.classList.add('active');
        }
    });
});