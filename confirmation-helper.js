(() => {
  const originalAlert = window.alert.bind(window);
  window.alert = message => {
    if (!String(message).startsWith('Order confirmed!')) originalAlert(message);
  };

  document.addEventListener('submit', event => {
    if (event.target.id !== 'checkout-form') return;

    const items = JSON.parse(localStorage.getItem('leanr-cart') || '[]');
    const subtotal = items.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0);
    const discountText = document.getElementById('discount-amount')?.textContent || '';
    const discountAmount = Number(discountText.replace(/[^0-9.]/g, '')) || 0;
    const postageText = document.getElementById('delivery')?.textContent || '';
    const postage = postageText === 'FREE' ? 0 : Number(postageText.replace(/[^0-9.]/g, '')) || 0;
    const total = subtotal - discountAmount + postage;
    const paypalFee = total * 0.029;
    const orderNumber = `ORD-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

    localStorage.setItem('leanr-last-order', JSON.stringify({
      orderNumber,
      customerName: document.getElementById('name')?.value || '',
      customerEmail: document.getElementById('email')?.value || '',
      customerPhone: document.getElementById('phone')?.value || '',
      deliveryAddress: document.getElementById('address')?.value || '',
      postcode: document.getElementById('postcode')?.value || '',
      city: document.getElementById('city')?.value || '',
      items,
      subtotal,
      discountAmount,
      postage,
      total,
      paypalFee,
      paypalTotal: total + paypalFee,
      useRoyalMailQr: !!document.getElementById('use-royalmail-qr')?.checked
    }));
  }, true);
})();
