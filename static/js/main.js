// Cafe Next Door - Main JavaScript

// Auto-hide flash messages after 2 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s ease-out';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
                // Also remove the flash-messages container if it's empty
                const flashContainer = document.querySelector('.flash-messages');
                if (flashContainer && flashContainer.querySelectorAll('.flash-message').length === 0) {
                    flashContainer.remove();
                }
            }, 500);
        }, 2000); // 2 seconds
    });
});

// Form validation enhancement
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#dc3545';
                } else {
                    field.style.borderColor = '#ddd';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });
});

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Hamburger menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger-menu');
    const navMenu = document.querySelector('.nav-menu');
    const body = document.body;
    
    if (hamburger && navMenu) {
        function toggleMenu() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
            body.classList.toggle('menu-open');
        }
        
        function closeMenu() {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            body.classList.remove('menu-open');
        }
        
        hamburger.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleMenu();
        });
        
        // Close menu when clicking on a link
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function() {
                closeMenu();
            });
        });
        
        // Close menu when clicking on overlay
        document.addEventListener('click', function(event) {
            if (navMenu.classList.contains('active')) {
                const isClickInsideNav = navMenu.contains(event.target);
                const isClickOnHamburger = hamburger.contains(event.target);
                
                if (!isClickInsideNav && !isClickOnHamburger) {
                    closeMenu();
                }
            }
        });
        
        // Close menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && navMenu.classList.contains('active')) {
                closeMenu();
            }
        });
    }
});

// Nav dropdown toggle
document.addEventListener('DOMContentLoaded', function() {
    const navDropdown = document.querySelector('.nav-dropdown');
    const dropdownToggle = document.querySelector('.nav-dropdown-toggle');
    
    if (navDropdown && dropdownToggle) {
        dropdownToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            navDropdown.classList.toggle('active');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (navDropdown.classList.contains('active')) {
                const isClickInside = navDropdown.contains(event.target);
                if (!isClickInside) {
                    navDropdown.classList.remove('active');
                }
            }
        });
        
        // Close dropdown when clicking on a dropdown link
        const dropdownLinks = navDropdown.querySelectorAll('.nav-dropdown-menu a');
        dropdownLinks.forEach(link => {
            link.addEventListener('click', function() {
                navDropdown.classList.remove('active');
            });
        });
    }
});

// Table sorting functionality
document.addEventListener('DOMContentLoaded', function() {
    const sortableHeaders = document.querySelectorAll('.admin-menu-table .sortable');
    let currentSort = { column: null, direction: 'asc' };
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortColumn = this.getAttribute('data-sort');
            const tbody = this.closest('table').querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const indicator = this.querySelector('.sort-indicator');
            
            // Toggle sort direction if clicking the same column
            if (currentSort.column === sortColumn) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = sortColumn;
                currentSort.direction = 'asc';
            }
            
            // Reset all indicators
            document.querySelectorAll('.sort-indicator').forEach(ind => {
                ind.textContent = '↕';
                ind.style.opacity = '0.5';
            });
            
            // Update current indicator
            indicator.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
            indicator.style.opacity = '1';
            
            // Sort rows
            rows.sort((a, b) => {
                let aValue, bValue;
                
                switch(sortColumn) {
                    case 'id':
                        aValue = parseInt(a.getAttribute('data-id'));
                        bValue = parseInt(b.getAttribute('data-id'));
                        break;
                    case 'name':
                        aValue = a.getAttribute('data-name').toLowerCase();
                        bValue = b.getAttribute('data-name').toLowerCase();
                        break;
                    case 'category':
                        aValue = a.getAttribute('data-category').toLowerCase();
                        bValue = b.getAttribute('data-category').toLowerCase();
                        break;
                    case 'price':
                        aValue = parseFloat(a.getAttribute('data-price'));
                        bValue = parseFloat(b.getAttribute('data-price'));
                        break;
                    default:
                        return 0;
                }
                
                if (aValue < bValue) return currentSort.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return currentSort.direction === 'asc' ? 1 : -1;
                return 0;
            });
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });
        
        // Add hover effect
        header.style.cursor = 'pointer';
    });
});

// Ingredient quantity input toggle
function toggleQuantityInput(checkbox) {
    const ingredientItem = checkbox.closest('.ingredient-item');
    const quantityWrapper = ingredientItem.querySelector('.quantity-input-wrapper');
    const quantityInput = ingredientItem.querySelector('.ingredient-quantity');
    
    if (checkbox.checked) {
        quantityWrapper.style.display = 'block';
        quantityInput.disabled = false;
        quantityInput.focus();
        if (!quantityInput.value) {
            quantityInput.value = '0.01';
        }
    } else {
        quantityWrapper.style.display = 'none';
        quantityInput.disabled = true;
        quantityInput.value = '';
    }
}

