# LEANr - E-Commerce Peptide Platform

A complete, mobile-responsive e-commerce platform for selling research peptides online. Email-based order system with admin dashboard for order and stock management.

## Features

✅ **6-Product Catalog** - RETATRUTIDE, TIRZEPETIDE, MT1, GHK-CU, KLOW PEN, CAGRI
✅ **Shopping Cart** - localStorage-based persistence
✅ **Email Ordering** - No payment processing on site (customers receive order details via email)
✅ **Postage Calculation** - £6 under £100, FREE over £100
✅ **Admin Dashboard** - Manage orders, stock levels, and view revenue analytics
✅ **Customer Reviews** - Auto-rotating review carousel
✅ **Product Variants** - Different strengths/formats with real-time pricing
✅ **Low Stock Warnings** - Orange badges when stock ≤ 5 units
✅ **Newsletter Signup** - Collect customer emails for marketing
✅ **Social Integration** - Floating WhatsApp & Telegram buttons
✅ **Cookie Consent** - GDPR-compliant banner with localStorage persistence
✅ **Order Notes** - Allow customers to add special delivery instructions
✅ **Mobile Responsive** - 100% mobile-friendly design

## Local Setup

### Requirements
- Python 3.8+
- Flask, Flask-CORS

### Installation

```bash
# Clone or download the project
cd leanr-site

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp .env.example .env

# Run Flask backend (one terminal)
python app.py
# Runs on http://localhost:5000

# Serve frontend (another terminal)
cd leanr-site
python -m http.server 3000
# Runs on http://localhost:3000
```

Open browser to **http://localhost:3000**

## Deployment to Production

### Option 1: Replit + Custom Domain (EASIEST & CHEAPEST)

**Step 1: Push to GitHub**
```bash
git init
git add .
git commit -m "LEANr e-commerce platform"
git remote add origin https://github.com/YOUR-USERNAME/leanr-site.git
git push -u origin main
```

**Step 2: Deploy on Replit**
1. Go to [replit.com](https://replit.com)
2. Click "Create" → "Import from GitHub"
3. Paste your repo URL
4. Replit auto-detects Flask and deploys automatically
5. Your app gets a free URL: `https://leanr-site.replit.dev`

**Step 3: Buy Custom Domain**
1. Go to [Namecheap.com](https://namecheap.com)
2. Search for your domain (e.g., leanr.com)
3. Buy (first year often $0.99-$8.88)

**Step 4: Connect Domain**
1. In Replit dashboard → Tools → Domain
2. Enter your domain
3. Copy the nameservers Replit provides
4. In Namecheap, go to Domain Settings → Nameservers
5. Paste Replit's nameservers
6. Done! Your domain now points to your live site

**Environment Variables in Replit:**
In Replit Secrets, add:
```
BUSINESS_EMAIL=your-email@gmail.com
BUSINESS_EMAIL_PASSWORD=your-app-password
ADMIN_USERNAME=admin
FLASK_ENV=production
HOST=0.0.0.0
CUSTOM_DOMAIN=yourdomain.com
```

---

### Option 2: PythonAnywhere (Good Alternative)

1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. Upload files via their web interface
3. Configure Flask app in Web tab
4. Add custom domain ($10/year)
5. Restart and go live

---

## Email Configuration

This platform uses Gmail SMTP to send order confirmations. 

**To set up:**

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App-Specific Password:
   - Go to [Google Account](https://myaccount.google.com)
   - Security → App passwords
   - Select "Mail" and "Windows Computer"
   - Copy the password provided
3. Set `BUSINESS_EMAIL_PASSWORD` to this app password

**In Production:**
Never commit your email password to GitHub. Always use environment variables (Replit Secrets, PythonAnywhere variables, etc.)

---

## Admin Dashboard

**Login:** `admin` / `leanr123` (default, change in production)

**Tabs:**
- **Orders** - View customer orders, add tracking numbers
- **Stock Levels** - Update inventory for each product variant
- **Revenue** - View total sales, order count, top-selling products

---

## File Structure

```
leanr-site/
├── index.html           # Main landing page
├── cart.html            # Shopping cart page
├── login.html           # Admin login
├── admin.html           # Admin dashboard
├── styles.css           # All styling
├── script.js            # Frontend logic (cart, modals, reviews)
├── cart-script.js       # Checkout form logic
├── app.py               # Flask backend API
├── orders.json          # Order records (auto-created)
├── stock.json           # Inventory levels
├── newsletter_emails.json # Newsletter subscribers
├── requirements.txt     # Python dependencies
├── Procfile             # Deployment config
├── .env.example         # Environment variables template
└── README.md            # This file
```

---

## API Endpoints

### Public
- `GET /api/public/stock` - Get current stock levels

### Orders
- `POST /api/send-order` - Submit new order

### Newsletter
- `POST /api/newsletter/subscribe` - Subscribe to newsletter

### Admin (require Bearer token)
- `POST /api/admin/login` - Admin login
- `GET /api/admin/orders` - Get all orders
- `POST /api/admin/send-tracking` - Send tracking number to customer
- `GET /api/admin/stock` - Get stock (admin view)
- `POST /api/admin/update-stock` - Update inventory
- `GET /api/admin/stats` - Get revenue analytics

---

## Customization

### Change Admin Password
In `app.py`, update:
```python
ADMIN_PASSWORD_HASH = hashlib.sha256(b"YOUR_NEW_PASSWORD").hexdigest()
```

### Update Product Pricing
Edit `app.py` - search for product definitions and update prices

### Change Email Templates
Edit HTML email templates in `app.py` (in `business_email_body` and `customer_email_body`)

### Customize Styling
Edit `styles.css` - all colors and layouts are in CSS custom properties at the top

---

## Troubleshooting

**Orders not sending emails?**
- Check email/password in environment variables
- Verify Gmail 2FA and app-specific password setup
- Check spam folder
- Verify SMTP settings (should be smtp.gmail.com:587)

**Admin dashboard not loading?**
- Clear browser cache
- Check admin token in localStorage
- Try logging out and logging back in

**Frontend not connecting to backend?**
- Make sure both servers are running
- Check console for CORS errors
- Verify ports (3000 for frontend, 5000 for backend)

---

## Support

For questions about deployment or customization, check the console logs and error messages. Most issues are related to environment variables or CORS configuration.

---

**Ready to launch?** Deploy to Replit in 5 minutes! 🚀
