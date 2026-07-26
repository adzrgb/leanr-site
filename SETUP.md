# LEANr E-Commerce Site - Setup & Deployment Guide

Your LEANr e-commerce site is complete and ready to deploy! Follow these steps to get it running.

## 📋 Prerequisites

- Python 3.x installed on your system
- Access to your business email (Gmail recommended)
- The ability to generate a Gmail app-specific password

## 🔧 Configuration Step 1: Gmail Setup

To enable email notifications for orders, you need to set up Gmail app-specific password:

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to **Security** in the left menu
3. Enable **2-Step Verification** (if not already enabled)
4. Go back to Security and find **App passwords**
5. Select Mail and Windows Computer (or your OS)
6. Google will generate a 16-character app-specific password
7. **Copy this password** - you'll need it in the next step

## ⚙️ Configuration Step 2: Update Email Credentials

Edit the `app.py` file and update these lines (around line 10-11):

```python
BUSINESS_EMAIL = "your-business-email@gmail.com"  # ← Change this
BUSINESS_EMAIL_PASSWORD = "your-app-password"      # ← Change this
```

Replace with:
- Your business email address
- The 16-character app password from Gmail (without spaces)

## 📦 Installation Step 1: Install Python Dependencies

Open a terminal/command prompt in your leanr-site folder and run:

```bash
pip install flask
pip install flask-cors
```

Or install both at once:
```bash
pip install flask flask-cors
```

## 🚀 Running the Server

### Step 1: Start the Static File Server

Keep your existing Python HTTP server running:

```bash
# In a terminal, in C:\Users\adamw\leanr-site\
python -m http.server 3000
```

### Step 2: Start the Order Processing Server (New Terminal)

In a **new terminal window**, run:

```bash
# In C:\Users\adamw\leanr-site\
python app.py
```

You should see:
```
LEANr Order Processing Server
==================================================
IMPORTANT: Update the following in this file:
  - BUSINESS_EMAIL: leanrwellness@gmail.com
  - BUSINESS_EMAIL_PASSWORD: Adamwhalen123

==================================================
 * Running on http://127.0.0.1:5000
```

## ✅ Testing the System

1. Open your browser to `http://localhost:3000/`
2. Select some products and add them to cart
3. Click the **Cart** badge to go to the cart page
4. Fill out the checkout form
5. Click **Complete Order**
6. You should see: `Order confirmed! Order number: ORD-xxx`
7. Check your business email - you should receive an order notification
8. Check the customer email - they should receive a confirmation

## 📧 What Customers Will See

**When placing an order, customers receive:**
- Order confirmation email with order number
- List of items ordered
- Delivery address confirmation
- Notice that payment details will be sent separately

**You (business) receive:**
- New order notification email
- Customer contact information
- Complete order details with pricing
- Request to send payment details separately

## 🌐 Going Live (Production Deployment)

When you're ready to deploy to a live domain:

1. **Host static files** (HTML/CSS/JS) on a web server:
   - Simple: Use a service like Netlify, Vercel, or GitHub Pages
   - Advanced: Use your own web server

2. **Deploy the Python backend** (app.py):
   - Recommended services: Heroku, AWS, DigitalOcean, PythonAnywhere
   - Keep your email credentials secure using environment variables

3. **Update the API endpoint** in `cart-script.js` (line ~62):
   - Change: `fetch('/api/send-order', ...)`
   - To: `fetch('https://your-domain.com/api/send-order', ...)`
   - Or your backend service URL

## 🔒 Security Best Practices

- **Never commit credentials to version control**
- Use environment variables for production
- Always use Gmail app passwords, not your main password
- Keep your backend server on a separate port
- Consider using HTTPS for production

## 📁 File Structure

```
C:\Users\adamw\leanr-site\
├── index.html          # Main landing page
├── cart.html           # Shopping cart page
├── styles.css          # All styling
├── script.js           # Main site logic
├── cart-script.js      # Cart page logic
├── app.py              # Email order processing server
├── logo.jpeg           # Brand logo
└── SETUP.md            # This file
```

## 🐛 Troubleshooting

**"Connection refused" on cart submit:**
- Make sure app.py server is running on port 5000
- Check terminal for error messages

**Emails not sending:**
- Verify your Gmail credentials in app.py
- Check that you used an app-specific password (not your main password)
- Ensure 2-Step Verification is enabled on your Gmail account
- Check spam/junk folder

**Cart page not loading:**
- Make sure static file server is running on port 3000
- Check browser console (F12) for JavaScript errors

**Port already in use:**
- If port 3000 is busy: `python -m http.server 3001`
- If port 5000 is busy: Edit app.py, change `app.run(port=5000)` to another port

## 📞 Support

If you encounter issues:
1. Check the browser console (F12) for error messages
2. Check your terminal for server error messages
3. Verify all credentials in app.py are correct
4. Make sure both servers are running

## ✨ Your Site Includes

✅ Mobile-responsive design
✅ 6 peptide products with variants
✅ Real-time price updates
✅ Shopping cart with persistence
✅ Order form with validation
✅ Automated email notifications
✅ Professional email templates
✅ Brand logo and gradient design
✅ Product information modals
✅ Delivery banner ($100+ free next day UK)
✅ Referral program mention ($10 both ways)

---

**You're all set! Start both servers and test your site.** 🚀
