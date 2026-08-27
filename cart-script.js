// Initialize cart from localStorage
const cart = JSON.parse(localStorage.getItem('leanr-cart')) || [];
let discountApplied = false;
let appliedDiscountCode = null;
let appliedDiscountPercent = 0;
let discountConfig = {
  enabled: false,
  code: 'BANKHOLIDAY15',
  percent: 15
};
const PAYPAL_FEE_PERCENT = 2.9;
const SALE_GIFT_ITEMS = {
  mt2: { name: 'MT2', option: 'Nasal - Free bank holiday gift' },
  ghkcu: { name: 'GHK-CU', option: 'Pen - Free bank holiday gift' }
};
let saleGiftStock = { MT2: 0, 'GHK-CU': 0 };
const secretDiscountConfig = {
          localStorage.setItem('leanr-last-order', JSON.stringify(orderData));
  percent: 10
};

const cartCount = document.getElementById('cart-count');

// Handle disclaimer banner close
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

function updateCartCount() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  if (cartCount) {
    cartCount.textContent = count;
  }
}

function saveCart() {
  localStorage.setItem('leanr-cart', JSON.stringify(cart));
}

function addToCart(product) {
  const existingItem = cart.find(item => item.name === product.name && item.option === product.option);
  
  if (existingItem) {
    existingItem.quantity += 1;
  } else {
    cart.push({
      name: product.name,
      price: product.price,
      option: product.option,
      quantity: 1
    });
  }
  
  saveCart();
  updateCartCount();
}

function applyDiscountUiState() {
  const discountSection = document.querySelector('.discount-section');
  const discountRow = document.getElementById('discount-row');
  const discountMessage = document.getElementById('discount-message');

  if (!discountConfig.enabled) {
    discountApplied = false;
    appliedDiscountCode = null;
    appliedDiscountPercent = 0;
    if (discountRow) discountRow.style.display = 'none';
    if (discountSection) discountSection.style.display = 'block';
    if (discountMessage) {
      discountMessage.textContent = 'Discount codes are currently unavailable';
      discountMessage.style.color = '#6b7280';
    }
    return;
  }

  discountApplied = true;
  appliedDiscountCode = discountConfig.code;
  appliedDiscountPercent = discountConfig.percent;
  if (discountSection) discountSection.style.display = 'none';
  if (discountMessage) {
    discountMessage.textContent = `${discountConfig.percent}% bank holiday discount applied automatically`;
    discountMessage.style.color = '#10b981';
  }
}

function initDiscountSettings() {
  return fetch(window.location.origin + '/api/public/discount-settings')
    .then(res => res.json())
    .then(data => {
      const discount = data.discount || {};
      discountConfig = {
        enabled: !!discount.enabled,
        code: (discount.code || 'BANKHOLIDAY15').toString().trim().toUpperCase(),
        percent: Number.isFinite(Number(discount.percent)) ? Number(discount.percent) : 15
      };
      applyDiscountUiState();
      renderCart();
    })
    .catch(() => {
      applyDiscountUiState();
    });
}

function initCheckoutUpsell() {
  const upsellButton = document.getElementById('add-ghkcu-upsell-btn');
  if (!upsellButton) return;

  upsellButton.addEventListener('click', () => {
    addToCart({
      name: 'GHK-CU',
      price: 45,
      option: 'Pen — £45'
    });

    renderCart();
    upsellButton.textContent = 'Added';
    upsellButton.disabled = true;

    setTimeout(() => {
      upsellButton.textContent = 'Add to cart';
      upsellButton.disabled = false;
    }, 1200);
  });
}

function shouldUseRoyalMailQr(subtotal) {
  if (subtotal >= 100) return false;
  const checkbox = document.getElementById('use-royalmail-qr');
  return !!checkbox?.checked;
}

function calculatePostage(subtotal) {
  if (subtotal >= 100) return 0;
  return shouldUseRoyalMailQr(subtotal) ? 0 : 5;
}

function syncSaleGifts(subtotal) {
  const giftNames = new Set(Object.values(SALE_GIFT_ITEMS).map(gift => gift.name));
  for (let index = cart.length - 1; index >= 0; index -= 1) {
    if (giftNames.has(cart[index].name) && cart[index].option?.includes('Free bank holiday gift')) {
      cart.splice(index, 1);
    }
  }

  if (!discountConfig.enabled) return;

  const discountedSubtotal = subtotal * (1 - (discountConfig.percent / 100));
  const mt2Stock = Number(saleGiftStock.MT2 || 0);
  const ghkcuStock = Number(saleGiftStock['GHK-CU'] || 0);

  if (discountedSubtotal >= 200 && ghkcuStock > 0) {
    cart.push({ ...SALE_GIFT_ITEMS.ghkcu, price: 0, quantity: 1 });
  } else if (discountedSubtotal >= 150 && mt2Stock > 0) {
    cart.push({ ...SALE_GIFT_ITEMS.mt2, price: 0, quantity: 1 });
  }
  saveCart();
}

async function loadSaleGiftStock() {
  try {
    const response = await fetch(window.location.origin + '/api/public/stock');
    const data = await response.json();
    const stockList = data.stock || [];
    const stockMap = {};

    stockList.forEach(item => {
      if (item && Array.isArray(item.variants)) {
        const variantMap = {};
        item.variants.forEach(variant => {
          variantMap[variant.name] = Number(variant.stock || 0);
        });
        stockMap[item.name] = variantMap;
      }
    });

    saleGiftStock = {
      MT2: Number(stockMap.MT2?.Nasal || 0),
      'GHK-CU': Number(stockMap['GHK-CU']?.Pen || 0)
    };
  } catch (error) {
    saleGiftStock = { MT2: 0, 'GHK-CU': 0 };
  }
}

function updatePaypalFee(total) {
  const fee = total * (PAYPAL_FEE_PERCENT / 100);
  document.getElementById('paypal-fee').textContent = `£${fee.toFixed(2)}`;
  document.getElementById('paypal-total').textContent = `£${(total + fee).toFixed(2)}`;
}

function renderCart() {
  const cartEmpty = document.getElementById('cart-empty');
  const cartItems = document.getElementById('cart-items');
  const itemsList = document.getElementById('items-list');
  
  if (cart.length === 0) {
    cartEmpty.style.display = 'block';
    cartItems.style.display = 'none';
    return;
  }
  
  cartEmpty.style.display = 'none';
  cartItems.style.display = 'block';

  const merchandiseSubtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  const giftCountBeforeSync = cart.length;
  syncSaleGifts(merchandiseSubtotal);
  if (cart.length !== giftCountBeforeSync) {
    renderCart();
    return;
  }
  
  itemsList.innerHTML = '';
  let subtotal = 0;
  
  cart.forEach((item, index) => {
    const itemTotal = item.price * item.quantity;
    subtotal += itemTotal;
    
    const itemRow = document.createElement('div');
    itemRow.className = 'cart-item-row';
    itemRow.innerHTML = `
      <span>${item.name}${item.option ? ` (${item.option})` : ''}</span>
      <span>£${item.price}</span>
      <span>${item.quantity}</span>
      <span>£${itemTotal.toFixed(2)}</span>
      <button class="remove-btn" data-index="${index}" title="Remove item">&times;</button>
    `;
    itemsList.appendChild(itemRow);
  });
  
  // Calculate discount if applied
  let discountAmount = 0;
  if (discountApplied) {
    discountAmount = subtotal * (appliedDiscountPercent / 100);
  }
  
  // Calculate postage (£5 under £100, but waived when Royal Mail QR option is selected)
  const postage = calculatePostage(subtotal);
  const total = subtotal - discountAmount + postage;
  
  
  // Update totals display
  const discountRow = document.getElementById('discount-row');
  if (discountApplied) {
    discountRow.style.display = 'block';
    document.getElementById('discount-amount').textContent = `-£${discountAmount.toFixed(2)}`;
  } else {
    discountRow.style.display = 'none';
  }
  
  document.getElementById('subtotal').textContent = `£${subtotal.toFixed(2)}`;
  document.getElementById('delivery').textContent = postage === 0 ? 'FREE' : `£${postage.toFixed(2)}`;
  document.getElementById('total').textContent = `£${total.toFixed(2)}`;
  updatePaypalFee(total);
  updateRoyalMailQrSection(subtotal);
  
  // Add remove listeners
  document.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const index = parseInt(e.target.dataset.index);
      cart.splice(index, 1);
      saveCart();
      updateCartCount();
      renderCart();
    });
  });
}

function updateRoyalMailQrSection(subtotal) {
  const wrapper = document.getElementById('royalmail-qr-wrapper');
  const checkbox = document.getElementById('use-royalmail-qr');
  const input = document.getElementById('royalmail-qr-code');
  const photoInput = document.getElementById('royalmail-qr-photo');

  if (!wrapper || !checkbox || !input || !photoInput) return;

  const needsRoyalMailOption = subtotal < 100;
  wrapper.style.display = needsRoyalMailOption ? 'block' : 'none';

  if (!needsRoyalMailOption) {
    checkbox.checked = false;
    input.value = '';
    photoInput.value = '';
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Unable to read selected image'));
    reader.readAsDataURL(file);
  });
}

// Handle checkout form submission
const checkoutForm = document.getElementById('checkout-form');
if (checkoutForm) {
  checkoutForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (cart.length === 0) {
      alert('Your cart is empty');
      return;
    }
    
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    // Calculate discount if applied
    let discountAmount = 0;
    if (discountApplied) {
      discountAmount = subtotal * (appliedDiscountPercent / 100);
    }
    
    const useRoyalMailQr = shouldUseRoyalMailQr(subtotal);
    // Calculate postage (£5 under £100, but waived when Royal Mail QR option is selected)
    const postage = calculatePostage(subtotal);
    const total = subtotal - discountAmount + postage;
    const paypalFee = total * (PAYPAL_FEE_PERCENT / 100);
    const royalMailQrCode = subtotal < 100 ? (document.getElementById('royalmail-qr-code')?.value || '').trim() : '';
    const royalMailQrPhotoFile = subtotal < 100 ? document.getElementById('royalmail-qr-photo')?.files?.[0] : null;

    let royalMailQrImageData = '';
    let royalMailQrImageName = '';

    if (useRoyalMailQr && royalMailQrPhotoFile) {
      if (!royalMailQrPhotoFile.type.startsWith('image/')) {
        alert('Royal Mail QR photo must be an image file.');
        return;
      }
      if (royalMailQrPhotoFile.size > 3 * 1024 * 1024) {
        alert('Royal Mail QR photo must be 3MB or smaller.');
        return;
      }

      try {
        royalMailQrImageData = await readFileAsDataUrl(royalMailQrPhotoFile);
        royalMailQrImageName = royalMailQrPhotoFile.name || 'royalmail-qr-image';
      } catch (fileError) {
        alert(fileError.message);
        return;
      }
    }

    if (useRoyalMailQr && !royalMailQrCode && !royalMailQrImageData) {
      alert('Please add your Royal Mail QR code/reference or upload a QR photo, or untick the Royal Mail QR option.');
      return;
    }
    
    const orderData = {
      orderNumber: 'ORD-' + Date.now() + '-' + Math.floor(Math.random() * 10000),
      customerName: document.getElementById('name').value,
      customerEmail: document.getElementById('email').value,
      customerPhone: document.getElementById('phone').value,
      deliveryAddress: document.getElementById('address').value,
      postcode: document.getElementById('postcode').value,
      city: document.getElementById('city').value,
      orderNotes: document.getElementById('order-notes').value || '',
      useRoyalMailQr: useRoyalMailQr,
      royalMailQrCode: royalMailQrCode,
      royalMailQrImageData: royalMailQrImageData,
      royalMailQrImageName: royalMailQrImageName,
      items: cart,
      subtotal: subtotal,
      discountAmount: discountAmount,
      discountCode: discountApplied ? appliedDiscountCode : null,
      postage: postage,
      total: total,
      paypalFee: paypalFee,
      paypalTotal: total + paypalFee,
      timestamp: new Date().toISOString()
    };
    
    const confirmationTab = window.open('about:blank', '_blank');

    try {
      const response = await fetch(window.location.origin + '/api/send-order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
      });
      
      if (response.ok) {
        localStorage.setItem('leanr-last-order', JSON.stringify(orderData));
        localStorage.setItem('leanr-last-order', JSON.stringify(orderData));         localStorage.removeItem('leanr-cart');
        if (confirmationTab) { confirmationTab.location.href = 'order-confirmation.html'; } else { window.location.href = 'order-confirmation.html'; }
      } else {
        const errData = await response.json().catch(() => ({}));
        console.error('Order error:', errData);
        alert('There was an issue processing your order: ' + (errData.error || response.status));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Unable to process order: ' + error.message);
    }
  });
}

const royalMailCheckbox = document.getElementById('use-royalmail-qr');
if (royalMailCheckbox) {
  royalMailCheckbox.addEventListener('change', () => {
    renderCart();
  });
}

// Signup form handler
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

// Initialize
updateCartCount();
loadSaleGiftStock().finally(() => {
  renderCart();
});
initCheckoutUpsell();
initDiscountSettings();

const paymentWarningPopup = document.getElementById('payment-warning-popup');
const paymentWarningClose = document.getElementById('payment-warning-close');
if (paymentWarningPopup && paymentWarningClose) {
  paymentWarningClose.addEventListener('click', () => {
    paymentWarningPopup.hidden = true;
  });
}

// Setup discount code handler - INLINE to ensure it runs
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOMContentLoaded: Setting up discount handler');
  setupDiscountHandler();
});

function setupDiscountHandler() {
  const discountBtn = document.getElementById('apply-discount-btn');
  const discountInput = document.getElementById('discount-code');
  const discountMessage = document.getElementById('discount-message');
  
  if (!discountBtn) {
    return;
  }
  
  // Remove any previous listeners
  const newBtn = discountBtn.cloneNode(true);
  discountBtn.parentNode.replaceChild(newBtn, discountBtn);
  
  newBtn.addEventListener('click', function(event) {
    event.preventDefault();
    const code = discountInput.value.trim().toUpperCase();
    const isSecretCode = code === secretDiscountConfig.code;

    if (!discountConfig.enabled && !isSecretCode) {
      discountApplied = false;
      appliedDiscountCode = null;
      appliedDiscountPercent = 0;
      discountMessage.textContent = 'Discount is currently unavailable';
      discountMessage.style.color = '#ef4444';
      renderCart();
      return;
    }

    if (code === discountConfig.code || isSecretCode) {
      discountApplied = true;
      appliedDiscountCode = isSecretCode ? secretDiscountConfig.code : discountConfig.code;
      appliedDiscountPercent = isSecretCode ? secretDiscountConfig.percent : discountConfig.percent;
      discountMessage.textContent = `✓ Discount code applied! (${appliedDiscountPercent}% off)`;
      discountMessage.style.color = '#10b981';
      newBtn.textContent = 'Applied';
      newBtn.disabled = true;
      renderCart();
    } else if (code === '') {
      discountApplied = false;
      appliedDiscountCode = null;
      appliedDiscountPercent = 0;
      discountMessage.textContent = 'Please enter a code';
      discountMessage.style.color = '#ef4444';
    } else {
      discountApplied = false;
      appliedDiscountCode = null;
      appliedDiscountPercent = 0;
      discountMessage.textContent = 'Invalid discount code';
      discountMessage.style.color = '#ef4444';
    }
  });
  
  // Allow Enter key
  discountInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      newBtn.click();
    }
  });
  
}

// Also try to set it up immediately in case DOM is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupDiscountHandler);
} else {
  // DOM is already loaded
  setTimeout(setupDiscountHandler, 50);
}
