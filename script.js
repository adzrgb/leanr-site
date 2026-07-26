let cart = JSON.parse(localStorage.getItem('leanr-cart')) || [];

// API Base URL - works for both local and production
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000'
  : window.location.origin.replace(/:\d+$/, ':5000'); // Replace port with 5000 for backend

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initBannerClose();
  initStockStatus();
  initDiscountPopup();
  initCookieConsent();
});

// Handle cookie consent
function initCookieConsent() {
  const cookieConsent = document.getElementById('cookie-consent');
  const cookieAccept = document.getElementById('cookie-accept');
  const cookieDecline = document.getElementById('cookie-decline');
  
  if (cookieConsent) {
    // Check if user already accepted
    if (localStorage.getItem('cookie-consent')) {
      cookieConsent.classList.add('hidden');
    }
    
    if (cookieAccept) {
      cookieAccept.addEventListener('click', () => {
        localStorage.setItem('cookie-consent', 'accepted');
        cookieConsent.classList.add('hidden');
      });
    }
    
    if (cookieDecline) {
      cookieDecline.addEventListener('click', () => {
        localStorage.setItem('cookie-consent', 'declined');
        cookieConsent.classList.add('hidden');
      });
    }
  }
}

// Handle discount code popup
function initDiscountPopup() {
  const popup = document.getElementById('discount-popup');
  const popupClose = document.getElementById('popup-close');
  
  if (popup && popupClose) {
    // Check if popup was previously dismissed
    if (!localStorage.getItem('discount-popup-dismissed')) {
      // Show popup after 1 second
      setTimeout(() => {
        popup.classList.add('active');
      }, 1000);
    }
    
    // Close popup on button click
    popupClose.addEventListener('click', () => {
      popup.classList.remove('active');
      localStorage.setItem('discount-popup-dismissed', 'true');
    });
    
    // Close popup on background click
    popup.addEventListener('click', (e) => {
      if (e.target === popup) {
        popup.classList.remove('active');
        localStorage.setItem('discount-popup-dismissed', 'true');
      }
    });
  }
}

// Handle disclaimer banner close
function initBannerClose() {
  const disclaimerBanner = document.getElementById('disclaimer-banner');
  const bannerClose = document.getElementById('banner-close');
  
  if (disclaimerBanner && bannerClose) {
    // Check if banner was previously closed
    if (localStorage.getItem('banner-dismissed')) {
      disclaimerBanner.style.display = 'none';
    }
    
    bannerClose.addEventListener('click', () => {
      disclaimerBanner.style.display = 'none';
      localStorage.setItem('banner-dismissed', 'true');
    });
  }
}

// Global stock data
let globalStockData = {};

// Fetch and update stock status
function initStockStatus() {
  fetch(window.location.origin + '/api/public/stock')
    .then(res => res.json())
    .then(data => {
      globalStockData = data.stock;
      updateProductBadges(data.stock);
    })
    .catch(err => console.log('Stock data unavailable'));
}

function updateProductBadges(stockData) {
  const stockMap = {};
  
  stockData.forEach(item => {
    if (Array.isArray(item.variants)) {
      stockMap[item.name] = item.variants.some(v => v.stock > 0);
    } else {
      stockMap[item.name] = item.stock > 0;
    }
  });
  
  document.querySelectorAll('.product-card').forEach(card => {
    const productName = card.querySelector('h3')?.textContent?.trim();
    const badge = card.querySelector('.product-badge');
    const addBtn = card.querySelector('.add-btn');
    
    if (badge && productName && stockMap.hasOwnProperty(productName)) {
      if (stockMap[productName]) {
        badge.textContent = 'In stock';
        badge.style.backgroundColor = '#10b981';
        badge.style.color = 'white';
        // Enable button for in-stock items
        if (addBtn) {
          addBtn.disabled = false;
          addBtn.style.opacity = '1';
          addBtn.style.cursor = 'pointer';
          // Reset text to 'Add to cart' if it was showing 'Out of Stock'
          if (addBtn.textContent === 'Out of Stock') {
            addBtn.textContent = 'Add to cart';
          }
        }
      } else {
        badge.textContent = 'Out of stock';
        badge.style.backgroundColor = '#dc2626';
        badge.style.color = 'white';
        // Disable button for out-of-stock items
        if (addBtn) {
          addBtn.disabled = true;
          addBtn.style.opacity = '0.5';
          addBtn.style.cursor = 'not-allowed';
          addBtn.textContent = 'Out of Stock';
        }
      }
      
      // Add low stock warning
      const productItem = stockData.find(item => item.name === productName);
      if (productItem) {
        let lowestStock = Infinity;
        
        if (Array.isArray(productItem.variants)) {
          lowestStock = Math.min(...productItem.variants.map(v => v.stock || 0));
        } else {
          lowestStock = productItem.stock || 0;
        }
        
        // Remove old warning if exists
        const oldWarning = card.querySelector('.stock-warning');
        if (oldWarning) oldWarning.remove();
        
        // Add warning if stock low
        if (lowestStock > 0 && lowestStock <= 5) {
          const warning = document.createElement('span');
          warning.className = 'stock-warning';
          warning.textContent = `Only ${lowestStock} left!`;
          card.appendChild(warning);
        }
      }
    }
  });
}

const cartCount = document.getElementById('cart-count');
const addButtons = document.querySelectorAll('.add-btn');
const viewInfoButtons = document.querySelectorAll('.view-info-btn');
const modalCloseButtons = document.querySelectorAll('.modal-close');

function updateCartCount() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  if (cartCount) {
    cartCount.textContent = count;
  }
}

function saveCart() {
  localStorage.setItem('leanr-cart', JSON.stringify(cart));
}

// Modal functionality
viewInfoButtons.forEach((button) => {
  button.addEventListener('click', (e) => {
    e.stopPropagation();
    const modalId = button.closest('.product-card').dataset.modal;
    if (modalId) {
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.classList.add('active');
      }
    }
  });
});

modalCloseButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const modal = button.closest('.modal');
    if (modal) {
      modal.classList.remove('active');
    }
  });
});

// Close modal when clicking outside content
document.querySelectorAll('.modal').forEach((modal) => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('active');
    }
  });
});

// Handle RETATRUTIDE strength selector
const strengthSelect = document.getElementById('strength-select');
const priceDisplay = document.getElementById('price-display');

if (strengthSelect && priceDisplay) {
  strengthSelect.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    priceDisplay.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('.featured-product .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = event.target.options[event.target.selectedIndex].text;
      addButton.textContent = 'Add to cart';
      addButton.disabled = false;
    }
  });
}

// Handle TIRZEPETIDE strength selector
const tirzeSelect = document.getElementById('tirze-select');
const tirzePrice = document.getElementById('tirze-price');

if (tirzeSelect && tirzePrice) {
  tirzeSelect.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    tirzePrice.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-tirzepetide"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = event.target.options[event.target.selectedIndex].text;
    }
  });
}

// Handle MT1 format selector
const mt1Select = document.getElementById('mt1-select');
const mt1Price = document.getElementById('mt1-price');

if (mt1Select && mt1Price) {
  mt1Select.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    mt1Price.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-mt1"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = event.target.options[event.target.selectedIndex].text;
    }
  });
}

// Handle GHK-CU format selector
const ghkSelect = document.getElementById('ghk-select');
const ghkPrice = document.getElementById('ghk-price');

if (ghkSelect && ghkPrice) {
  ghkSelect.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    ghkPrice.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-ghkcu"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = event.target.options[event.target.selectedIndex].text;
    }
  });
}

addButtons.forEach((button) => {
  button.addEventListener('click', (e) => {
    e.stopPropagation();
    
    // Check if item is in stock
    if (button.disabled) {
      alert('This item is currently out of stock');
      return;
    }
    
    const productCard = button.closest('.product-card');
    const productName = productCard.querySelector('h3').textContent.trim();
    
    // Get the selected option if available
    let selectedOption = '';
    let price = parseInt(button.dataset.price) || 0;
    
    if (button.dataset.option) {
      selectedOption = button.dataset.option;
    } else {
      const select = productCard.querySelector('select');
      if (select) {
        selectedOption = select.options[select.selectedIndex].text;
        price = parseInt(select.value);
      }
    }
    
    if (price === 0) {
      const priceText = productCard.querySelector('.product-meta span').textContent;
      price = parseInt(priceText.replace('£', ''));
    }
    
    // Verify item is in stock before adding
    const stockItem = globalStockData.find(item => item.name === productName);
    let isInStock = false;
    
    if (stockItem) {
      if (Array.isArray(stockItem.variants)) {
        // Extract variant name (remove price suffix like " — £130")
        const variantName = selectedOption.split(' — ')[0].trim();
        // Check if the SELECTED variant is in stock
        const selectedVariant = stockItem.variants.find(v => v.name === variantName);
        isInStock = selectedVariant && selectedVariant.stock > 0;
      } else {
        isInStock = stockItem.stock > 0;
      }
    }
    
    if (!isInStock) {
      const displayName = selectedOption.split(' — ')[0].trim() || 'This item';
      alert(`${displayName} is currently out of stock`);
      return;
    }
    
    const product = {
      name: productName,
      price: price,
      option: selectedOption,
      quantity: 1
    };
    
    const existingItem = cart.find(item => item.name === product.name && item.option === product.option);
    
    if (existingItem) {
      existingItem.quantity += 1;
    } else {
      cart.push(product);
    }
    
    saveCart();
    updateCartCount();
    button.textContent = 'Added';
    button.disabled = true;
    setTimeout(() => {
      button.textContent = 'Add to cart';
      button.disabled = false;
    }, 1500);
  });
});

document.querySelector('.signup-form')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const input = event.currentTarget.querySelector('input');
  const email = input.value.trim();
  
  if (!email) return;
  
  // Save to backend
  fetch(window.location.origin + '/api/newsletter/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  }).then(() => {
    input.value = '';
    alert('Thanks for joining LEANr. Check your email for exclusive offers!');
  }).catch(() => {
    alert('Thanks for joining LEANr.');
    input.value = '';
  });
});

// Review carousel functionality
let currentReviewIndex = 0;
const reviewCards = document.querySelectorAll('.review-card');
const totalReviews = reviewCards.length;

function showReview(index) {
  reviewCards.forEach(card => {
    card.style.display = 'none';
  });
  if (reviewCards[index]) {
    reviewCards[index].style.display = 'block';
  }
}

function cycleReview() {
  currentReviewIndex = (currentReviewIndex + 1) % totalReviews;
  showReview(currentReviewIndex);
}

// Cycle through reviews every 4 seconds
if (totalReviews > 1) {
  setInterval(cycleReview, 4000);
}

// Initialize
updateCartCount();
