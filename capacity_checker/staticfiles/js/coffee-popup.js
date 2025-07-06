/**
 * Coffee Popup - Shows after certain number of page views
 * Tracks page views in localStorage and shows a "Buy me a coffee" popup
 */

(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        pageViewThreshold: 2,         // Show popup after X page views
        storageKey: 'cmr_page_views', // localStorage key
        dismissedKey: 'cmr_coffee_dismissed', // localStorage key for dismissal
        showInterval: 5,              // Show again after X more page views if dismissed
        popupId: 'coffeePopup'
    };
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initCoffeePopup();
    });
    
    function initCoffeePopup() {
        // Don't show on certain pages
        if (shouldSkipPopup()) {
            return;
        }
        
        // Track page view
        const pageViews = trackPageView();
        
        // Check if we should show the popup
        if (shouldShowPopup(pageViews)) {
            createAndShowPopup();
        }
    }
    
    function shouldSkipPopup() {
        const currentPath = window.location.pathname;
        const skipPaths = [
            '/accounts/payment',
            '/accounts/register',
            '/accounts/login',
            '/donate/',
            '/admin/'
        ];
        
        return skipPaths.some(path => currentPath.startsWith(path));
    }
    
    function trackPageView() {
        let pageViews = parseInt(localStorage.getItem(CONFIG.storageKey) || '0');
        pageViews++;
        localStorage.setItem(CONFIG.storageKey, pageViews.toString());
        return pageViews;
    }
    
    function shouldShowPopup(pageViews) {
        // Check if user has dismissed recently
        const dismissed = localStorage.getItem(CONFIG.dismissedKey);
        if (dismissed) {
            const dismissedAt = parseInt(dismissed);
            const showAgainAt = dismissedAt + CONFIG.showInterval;
            
            // Only show if enough page views have passed since dismissal
            return pageViews >= showAgainAt;
        }
        
        // Show if we've reached the threshold
        return pageViews >= CONFIG.pageViewThreshold;
    }
    
    function createAndShowPopup() {
        // Don't show if popup already exists
        if (document.getElementById(CONFIG.popupId)) {
            return;
        }
        
        // Create popup HTML
        const popup = document.createElement('div');
        popup.id = CONFIG.popupId;
        popup.innerHTML = `
            <div class="coffee-popup-overlay">
                <div class="coffee-popup-content">
                    <button class="coffee-popup-close" aria-label="Close">&times;</button>
                    <div class="coffee-popup-body">
                        <div class="coffee-icon">☕</div>
                        <h3>Enjoying the site?</h3>
                        <p>If you find the Capacity Market Search useful, consider buying me a coffee to help keep it running!</p>
                        <div class="coffee-popup-buttons">
                            <a href="/donate/" class="coffee-btn coffee-btn-primary">
                                <i class="bi bi-cup-hot"></i> Buy Me A Coffee
                            </a>
                            <button class="coffee-btn coffee-btn-secondary" onclick="dismissCoffeePopup()">
                                Maybe Later
                            </button>
                        </div>
                        <small class="coffee-popup-note">This helps cover server costs and keeps the site free!</small>
                    </div>
                </div>
            </div>
        `;
        
        // Add CSS styles
        const styles = `
            <style>
                .coffee-popup-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: coffee-fade-in 0.3s ease-out;
                }
                
                .coffee-popup-content {
                    background: white;
                    border-radius: 12px;
                    max-width: 400px;
                    width: 90%;
                    margin: 20px;
                    position: relative;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    animation: coffee-slide-up 0.3s ease-out;
                }
                
                .coffee-popup-close {
                    position: absolute;
                    top: 10px;
                    right: 15px;
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #666;
                    z-index: 1;
                }
                
                .coffee-popup-close:hover {
                    color: #333;
                }
                
                .coffee-popup-body {
                    padding: 30px 25px 25px;
                    text-align: center;
                }
                
                .coffee-icon {
                    font-size: 48px;
                    margin-bottom: 15px;
                    animation: coffee-bounce 2s infinite;
                }
                
                .coffee-popup-body h3 {
                    color: #333;
                    margin-bottom: 15px;
                    font-size: 1.4rem;
                }
                
                .coffee-popup-body p {
                    color: #666;
                    margin-bottom: 20px;
                    line-height: 1.5;
                }
                
                .coffee-popup-buttons {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                }
                
                .coffee-btn {
                    flex: 1;
                    padding: 12px 20px;
                    border: none;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    min-height: 44px;
                }
                
                .coffee-btn-primary {
                    background: #FF813F;
                    color: white;
                }
                
                .coffee-btn-primary:hover {
                    background: #e6732e;
                    color: white;
                    text-decoration: none;
                    transform: translateY(-1px);
                }
                
                .coffee-btn-secondary {
                    background: #f8f9fa;
                    color: #666;
                    border: 1px solid #ddd;
                }
                
                .coffee-btn-secondary:hover {
                    background: #e9ecef;
                    color: #333;
                }
                
                .coffee-popup-note {
                    color: #888;
                    font-size: 0.85rem;
                }
                
                /* Dark mode styles */
                html[data-bs-theme="dark"] .coffee-popup-content {
                    background: #2d3748;
                    color: #e2e8f0;
                }
                
                html[data-bs-theme="dark"] .coffee-popup-body h3 {
                    color: #e2e8f0;
                }
                
                html[data-bs-theme="dark"] .coffee-popup-body p {
                    color: #cbd5e0;
                }
                
                html[data-bs-theme="dark"] .coffee-popup-close {
                    color: #cbd5e0;
                }
                
                html[data-bs-theme="dark"] .coffee-popup-close:hover {
                    color: #e2e8f0;
                }
                
                html[data-bs-theme="dark"] .coffee-btn-secondary {
                    background: #4a5568;
                    color: #e2e8f0;
                    border-color: #718096;
                }
                
                html[data-bs-theme="dark"] .coffee-btn-secondary:hover {
                    background: #718096;
                    color: #f7fafc;
                }
                
                html[data-bs-theme="dark"] .coffee-popup-note {
                    color: #a0aec0;
                }
                
                /* Animations */
                @keyframes coffee-fade-in {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                
                @keyframes coffee-slide-up {
                    from { 
                        transform: translateY(30px);
                        opacity: 0;
                    }
                    to { 
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
                
                @keyframes coffee-bounce {
                    0%, 20%, 50%, 80%, 100% {
                        transform: translateY(0);
                    }
                    40% {
                        transform: translateY(-10px);
                    }
                    60% {
                        transform: translateY(-5px);
                    }
                }
                
                /* Mobile responsive */
                @media (max-width: 480px) {
                    .coffee-popup-content {
                        margin: 10px;
                    }
                    
                    .coffee-popup-body {
                        padding: 25px 20px 20px;
                    }
                    
                    .coffee-popup-buttons {
                        flex-direction: column;
                    }
                    
                    .coffee-btn {
                        width: 100%;
                    }
                }
            </style>
        `;
        
        // Add styles to head
        document.head.insertAdjacentHTML('beforeend', styles);
        
        // Add popup to body
        document.body.appendChild(popup);
        
        // Prevent body scrolling
        document.body.style.overflow = 'hidden';
        
        // Add event listeners
        addPopupEventListeners();
        
        // Auto-dismiss after 15 seconds
        setTimeout(() => {
            dismissCoffeePopup();
        }, 15000);
    }
    
    function addPopupEventListeners() {
        const popup = document.getElementById(CONFIG.popupId);
        if (!popup) return;
        
        // Close button
        const closeBtn = popup.querySelector('.coffee-popup-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', dismissCoffeePopup);
        }
        
        // Maybe later button
        const maybeBtn = popup.querySelector('.coffee-btn-secondary');
        if (maybeBtn) {
            maybeBtn.addEventListener('click', dismissCoffeePopup);
        }
        
        // Overlay click to close
        const overlay = popup.querySelector('.coffee-popup-overlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    dismissCoffeePopup();
                }
            });
        }
        
        // Escape key to close
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                dismissCoffeePopup();
            }
        });
    }
    
    // Global function to dismiss popup
    window.dismissCoffeePopup = function() {
        const popup = document.getElementById(CONFIG.popupId);
        if (popup) {
            // Add fade out animation
            popup.style.animation = 'coffee-fade-out 0.3s ease-out forwards';
            popup.addEventListener('animationend', function() {
                popup.remove();
            });
            
            // Restore body scrolling
            document.body.style.overflow = '';
            
            // Mark as dismissed
            const currentPageViews = parseInt(localStorage.getItem(CONFIG.storageKey) || '0');
            localStorage.setItem(CONFIG.dismissedKey, currentPageViews.toString());
        }
    };
    
    // Global function to manually trigger popup for testing
    window.testCoffeePopup = function() {
        createAndShowPopup();
    };
    
    // Global function to reset page view counter for testing
    window.resetCoffeeCounter = function() {
        localStorage.removeItem(CONFIG.storageKey);
        localStorage.removeItem(CONFIG.dismissedKey);
        console.log('Coffee popup counters reset. Reload page to start fresh.');
    };
    
    // Global function to check current status
    window.coffeePopupStatus = function() {
        const pageViews = parseInt(localStorage.getItem(CONFIG.storageKey) || '0');
        const dismissed = localStorage.getItem(CONFIG.dismissedKey);
        console.log('Coffee Popup Status:');
        console.log('- Page views:', pageViews);
        console.log('- Threshold:', CONFIG.pageViewThreshold);
        console.log('- Dismissed at page view:', dismissed || 'Never');
        console.log('- Will show popup:', shouldShowPopup(pageViews));
    };
    
    // Add fade out animation to existing styles
    document.addEventListener('DOMContentLoaded', function() {
        const fadeOutStyle = `
            <style>
                @keyframes coffee-fade-out {
                    from { opacity: 1; }
                    to { opacity: 0; }
                }
            </style>
        `;
        document.head.insertAdjacentHTML('beforeend', fadeOutStyle);
    });
    
})();