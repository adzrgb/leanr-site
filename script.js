let cart = JSON.parse(localStorage.getItem('leanr-cart')) || [];

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
  const codeDisplay = document.querySelector('.discount-code-display');
  const popupText = document.querySelector('.popup-text');
  
  if (popup && popupClose) {
    fetch(window.location.origin + '/api/public/discount-settings')
      .then(res => res.json())
      .then(data => {
        const discount = data.discount || {};
        if (!discount.enabled) {
          popup.classList.remove('active');
          popup.style.display = 'none';
          return;
        }

        if (codeDisplay && discount.code) {
          codeDisplay.textContent = discount.code;
        }

        if (popupText && Number.isFinite(Number(discount.percent))) {
          popupText.innerHTML = `Get <strong>${discount.percent}% OFF</strong> all orders on LEANr`;
        }

        // Check if popup was previously dismissed
        if (!localStorage.getItem('discount-popup-dismissed')) {
          // Show popup after 1 second
          setTimeout(() => {
            popup.classList.add('active');
          }, 1000);
        }
      })
      .catch(() => {
        // Fallback: keep current popup behavior if settings request fails.
        if (!localStorage.getItem('discount-popup-dismissed')) {
          setTimeout(() => {
            popup.classList.add('active');
          }, 1000);
        }
      });
    
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
          warning.textContent = `${lowestStock} left`;
          card.appendChild(warning);
        }
        
        // For products with variants, check the currently selected variant
        if (Array.isArray(productItem.variants) && addBtn) {
          const select = card.querySelector('select');
          if (select) {
            const selectedText = select.options[select.selectedIndex].text;
            const variantName = selectedText.split(' — ')[0].trim();
            updateButtonForVariant(productName, selectedText, addBtn);
            
            // Update stock info based on product type
            if (productName === 'RETATRUTIDE') {
              updateVariantStockInfo('RETATRUTIDE', 'reta-stock-info', variantName);
            } else if (productName === 'TIRZEPETIDE') {
              updateVariantStockInfo('TIRZEPETIDE', 'tirze-stock-info', variantName);
            } else if (productName === 'MT1') {
              updateVariantStockInfo('MT1', 'mt1-stock-info', variantName);
            } else if (productName === 'MT2') {
              updateVariantStockInfo('MT2', 'mt2-stock-info', variantName);
            } else if (productName === 'GHK-CU') {
              updateVariantStockInfo('GHK-CU', 'ghk-stock-info', variantName);
            }
          }
        } else if (!Array.isArray(productItem.variants)) {
          // Non-variant products: update stock info display
          if (productName === 'KLOW PEN') {
            updateNonVariantStockInfo('KLOW PEN', 'klow-stock-info');
          } else if (productName === 'CAGRI') {
            updateNonVariantStockInfo('CAGRI', 'cagri-stock-info');
          }
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

// Helper function to check variant stock and update button state
function updateButtonForVariant(productName, selectedText, addButton) {
  if (!addButton || !globalStockData || !Array.isArray(globalStockData)) {
    return;
  }
  
  const variantName = selectedText.split(' — ')[0].trim();
  const productData = globalStockData.find(item => item.name === productName);
  
  if (productData && Array.isArray(productData.variants)) {
    const selectedVariant = productData.variants.find(v => v.name === variantName);
    if (selectedVariant && selectedVariant.stock > 0) {
      addButton.disabled = false;
      addButton.style.opacity = '1';
      addButton.style.cursor = 'pointer';
      addButton.textContent = 'Add to cart';
    } else {
      addButton.disabled = true;
      addButton.style.opacity = '0.5';
      addButton.style.cursor = 'not-allowed';
      addButton.textContent = 'Out of Stock';
    }
  }
}

// Update stock info display for the currently selected variant
function updateVariantStockInfo(productName, infoElementId, selectedVariantName) {
  const infoEl = document.getElementById(infoElementId);
  if (!infoEl || !globalStockData || !Array.isArray(globalStockData)) {
    return;
  }
  
  // globalStockData is an array of objects with name and variants properties
  const productData = globalStockData.find(item => item.name === productName);
  if (!productData || !Array.isArray(productData.variants)) {
    return;
  }
  
  // Find the stock count for the selected variant
  const selectedVariant = productData.variants.find(v => v.name === selectedVariantName);
  
  if (selectedVariant) {
    // Only display stock count for low stock items (5 or fewer)
    if (selectedVariant.stock > 0 && selectedVariant.stock <= 5) {
      infoEl.textContent = `${selectedVariantName}: ${selectedVariant.stock} left`;
    } else {
      infoEl.textContent = '';
    }
  }
}

// Update stock info display for non-variant products
function updateNonVariantStockInfo(productName, infoElementId) {
  const infoEl = document.getElementById(infoElementId);
  if (!infoEl || !globalStockData || !Array.isArray(globalStockData)) {
    return;
  }
  
  // Find the product in globalStockData
  const productData = globalStockData.find(item => item.name === productName);
  if (!productData || Array.isArray(productData.variants) || !productData.stock) {
    return;
  }
  
  // Only display stock count for low stock items (5 or fewer)
  if (productData.stock > 0 && productData.stock <= 5) {
    infoEl.textContent = `${productData.stock} left`;
  } else {
    infoEl.textContent = '';
  }
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
    const selectedText = event.target.options[event.target.selectedIndex].text;
    const variantName = selectedText.split(' — ')[0].trim();
    priceDisplay.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('.featured-product .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = selectedText;
      updateButtonForVariant('RETATRUTIDE', selectedText, addButton);
      updateVariantStockInfo('RETATRUTIDE', 'reta-stock-info', variantName);
    }
  });
}

// Handle TIRZEPETIDE strength selector
const tirzeSelect = document.getElementById('tirze-select');
const tirzePrice = document.getElementById('tirze-price');

if (tirzeSelect && tirzePrice) {
  tirzeSelect.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    const selectedText = event.target.options[event.target.selectedIndex].text;
    const variantName = selectedText.split(' — ')[0].trim();
    tirzePrice.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-tirzepetide"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = selectedText;
      updateButtonForVariant('TIRZEPETIDE', selectedText, addButton);
      updateVariantStockInfo('TIRZEPETIDE', 'tirze-stock-info', variantName);
    }
  });
}

// Handle MT1 format selector
const mt1Select = document.getElementById('mt1-select');
const mt1Price = document.getElementById('mt1-price');

if (mt1Select && mt1Price) {
  mt1Select.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    const selectedText = event.target.options[event.target.selectedIndex].text;
    const variantName = selectedText.split(' — ')[0].trim();
    mt1Price.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-mt1"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = selectedText;
      updateButtonForVariant('MT1', selectedText, addButton);
      updateVariantStockInfo('MT1', 'mt1-stock-info', variantName);
    }
  });
}

// Handle MT2 format selector
const mt2Select = document.getElementById('mt2-select');
const mt2Price = document.getElementById('mt2-price');

if (mt2Select && mt2Price) {
  mt2Select.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    const selectedText = event.target.options[event.target.selectedIndex].text;
    const variantName = selectedText.split(' — ')[0].trim();
    mt2Price.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-mt2"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = selectedText;
      updateButtonForVariant('MT2', selectedText, addButton);
      updateVariantStockInfo('MT2', 'mt2-stock-info', variantName);
    }
  });
}

// Handle GHK-CU format selector
const ghkSelect = document.getElementById('ghk-select');
const ghkPrice = document.getElementById('ghk-price');

if (ghkSelect && ghkPrice) {
  ghkSelect.addEventListener('change', (event) => {
    const selectedValue = event.target.value;
    const selectedText = event.target.options[event.target.selectedIndex].text;
    const variantName = selectedText.split(' — ')[0].trim();
    ghkPrice.textContent = `£${selectedValue}`;
    const addButton = document.querySelector('[data-modal="modal-ghkcu"] .add-btn');
    if (addButton) {
      addButton.dataset.price = selectedValue;
      addButton.dataset.option = selectedText;
      updateButtonForVariant('GHK-CU', selectedText, addButton);
      updateVariantStockInfo('GHK-CU', 'ghk-stock-info', variantName);
    }
  });
}

addButtons.forEach((button) => {
  button.addEventListener('click', (e) => {
    e.stopPropagation();
    
    // If button is disabled, do nothing (item is out of stock)
    if (button.disabled) {
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
