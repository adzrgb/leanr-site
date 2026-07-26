// Initialize cart from localStorage
const cart = JSON.parse(localStorage.getItem('leanr-cart')) || [];
let discountApplied = false;
const DISCOUNT_CODE = 'LEANR10';
const DISCOUNT_PERCENT = 10;

// API Base URL - works for both local and production
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000'
  : window.location.origin.replace(/:\d+$/, ':5000'); // Replace port with 5000 for backend

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
      <button class="remove-btn" data-index="${index}">Remove</button>
    `;
    itemsList.appendChild(itemRow);
  });
  
  // Calculate postage
  const postage = subtotal < 100 ? 6 : 0;
  const total = subtotal + postage;
  
  // Update totals
  document.getElementById('subtotal').textContent = `£${subtotal.toFixed(2)}`;
  document.getElementById('delivery').textContent = postage === 0 ? 'FREE' : `£${postage.toFixed(2)}`;
  document.getElementById('total').textContent = `£${total.toFixed(2)}`;
  
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
    const postage = subtotal < 100 ? 6 : 0;
    const total = subtotal + postage;
    
    const orderData = {
      orderNumber: 'ORD-' + Date.now() + '-' + Math.floor(Math.random() * 10000),
      customerName: document.getElementById('name').value,
      customerEmail: document.getElementById('email').value,
      customerPhone: document.getElementById('phone').value,
      deliveryAddress: document.getElementById('address').value,
      postcode: document.getElementById('postcode').value,
      city: document.getElementById('city').value,
      orderNotes: document.getElementById('order-notes').value || '',
      items: cart,
      subtotal: subtotal,
      postage: postage,
      total: total,
      timestamp: new Date().toISOString()
    };
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/send-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'omit',
        body: JSON.stringify(orderData)
      }).catch(e => {
        // Fallback for localhost on different port
        return fetch('http://127.0.0.1:5000/api/send-order', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'omit',
          body: JSON.stringify(orderData)
        });
      });
      
      if (response.ok) {
        alert(`Order confirmed! Order number: ${orderData.orderNumber}\n\nConfirmation email sent to your email address. Payment details will be provided in the email.`);
        localStorage.removeItem('leanr-cart');
        window.location.href = 'index.html';
      } else {
        alert('There was an issue processing your order. Please try again.');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Unable to process order. Please check your connection and try again.');
    }
  });
}

// Signup form handler
document.querySelector('.signup-form')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const input = event.currentTarget.querySelector('input');
  const email = input.value.trim();
  
  if (!email) return;
  
  // Save to backend
  fetch('http://127.0.0.1:5000/api/newsletter/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'omit',
    body: JSON.stringify({ email })
  }).catch(() => {
    return fetch('http://localhost:5000/api/newsletter/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'omit',
      body: JSON.stringify({ email })
    });
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
renderCart();
