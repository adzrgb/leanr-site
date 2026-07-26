# LEANr Deployment Checklist

## Pre-Deployment (Local Testing)
- [ ] Test all features locally (cart, checkout, admin dashboard)
- [ ] Verify email sending works with test order
- [ ] Test all product variants and pricing
- [ ] Check mobile responsiveness
- [ ] Test admin login and stock/order management

## GitHub Setup
- [ ] Create GitHub account (if needed)
- [ ] Create new repository: `leanr-site`
- [ ] Add `.gitignore` (included in project)
- [ ] Add `requirements.txt` (included in project)
- [ ] Add `Procfile` (included in project)
- [ ] Push all files to GitHub

```bash
git init
git add .
git commit -m "Initial commit: LEANr e-commerce platform"
git remote add origin https://github.com/YOUR-USERNAME/leanr-site.git
git push -u origin main
```

## Replit Deployment
- [ ] Create Replit account (https://replit.com)
- [ ] Click "Create" → "Import from GitHub"
- [ ] Select your leanr-site repository
- [ ] Wait for deployment (auto-detects Flask)
- [ ] Test at `https://leanr-site.replit.dev`
- [ ] Get your Replit URL and nameservers

## Replit Environment Variables
In Replit dashboard, go to "Secrets" and add:

```
BUSINESS_EMAIL=leanrwellness@gmail.com
BUSINESS_EMAIL_PASSWORD=ugxb naur dasv pkeg
ADMIN_USERNAME=admin
FLASK_ENV=production
HOST=0.0.0.0
PORT=5000
CUSTOM_DOMAIN=yourdomain.com
```

- [ ] Add BUSINESS_EMAIL
- [ ] Add BUSINESS_EMAIL_PASSWORD (your Gmail app password)
- [ ] Add ADMIN_USERNAME
- [ ] Set FLASK_ENV=production
- [ ] Set HOST=0.0.0.0
- [ ] Add CUSTOM_DOMAIN (if you have one)

## Domain Registration
- [ ] Go to Namecheap.com (or your preferred registrar)
- [ ] Search for your domain (e.g., leanr.com)
- [ ] Add to cart and purchase
- [ ] Get the nameservers (Replit will provide these)
- [ ] Update domain nameservers to point to Replit

## Connect Domain to Replit
- [ ] In Replit → Tools → Domains
- [ ] Enter your custom domain
- [ ] Copy the nameservers shown
- [ ] Go to Namecheap → Your Domains
- [ ] Select your domain → Manage
- [ ] Nameservers → Custom DNS
- [ ] Add Replit's nameservers
- [ ] Save and wait 24 hours for DNS propagation

## Post-Deployment Testing
- [ ] Visit https://yourdomain.com (should load)
- [ ] Test adding products to cart
- [ ] Test checkout form and order submission
- [ ] Check for order confirmation email
- [ ] Test admin login at https://yourdomain.com/login.html
- [ ] Verify stock and order management in admin
- [ ] Test newsletter signup
- [ ] Test cookie consent
- [ ] Test WhatsApp/Telegram buttons

## Optional Enhancements
- [ ] Add SSL certificate (Replit does this automatically)
- [ ] Set up email forwarding on Namecheap
- [ ] Create backup of orders.json regularly
- [ ] Monitor error logs in Replit console
- [ ] Test on mobile devices

## Going Live
- [ ] Update order email confirmation template with final domain
- [ ] Add any final branding/messaging changes
- [ ] Brief team/admins on how to access dashboard
- [ ] Set up admin password for production (change from default)
- [ ] Share domain with customers
- [ ] Post on WhatsApp/Telegram community channels
- [ ] Monitor first orders for any issues

---

## Quick Reference

**Replit Dashboard:**
https://replit.com/dashboard

**Namecheap Dashboard:**
https://ap.namecheap.com/dashboard

**Gmail App Passwords:**
https://myaccount.google.com/apppasswords

**Your Site (after deployment):**
https://yourdomain.com

**Admin Dashboard:**
https://yourdomain.com/login.html (admin / leanr123)

---

## Estimated Timeline
- GitHub setup: 5 minutes
- Replit deployment: 2 minutes (auto)
- Domain purchase: 5 minutes
- DNS propagation: 24 hours
- **Total: ~5 minutes active work + 24 hours for DNS**

Your site will be live within 24 hours!
