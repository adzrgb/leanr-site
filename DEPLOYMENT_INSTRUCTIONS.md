# 🚀 DEPLOYMENT GUIDE - Your Exact Steps

## Your Information
- **GitHub User:** adzrgb
- **Replit Name:** leanrwellness
- **Domain:** leanrwellness.com
- **Admin Login:** admin / Qx7m#K2$pL9@vN4b

---

## STEP 1: Initialize Git & Push to GitHub

Open **PowerShell** and navigate to your project folder, then copy-paste these commands **one at a time**:

```powershell
cd C:\Users\adamw\leanr-site
```

```powershell
git config --global user.name "adzrgb"
```

```powershell
git config --global user.email "your-email@gmail.com"
```

```powershell
git init
```

```powershell
git add .
```

```powershell
git commit -m "LEANr e-commerce platform - production ready"
```

```powershell
git remote add origin https://github.com/adzrgb/leanr-site.git
```

```powershell
git branch -M main
```

```powershell
git push -u origin main
```

**If prompted for password:** Use your GitHub personal access token (get it from github.com/settings/tokens)

✅ Your code is now on GitHub!

---

## STEP 2: Deploy on Replit

1. Go to https://replit.com/dashboard
2. Click **"Create"** (top right)
3. Select **"Import from GitHub"**
4. Paste: `https://github.com/adzrgb/leanr-site`
5. Click **Import**
6. **Wait 2-3 minutes** while Replit deploys
7. You'll see output saying "Running on..." - it's live! ✅

Your temporary URL: `https://leanr-site.replit.dev`

---

## STEP 3: Add Replit Secrets

1. In Replit dashboard, find your project
2. Click your project to open it
3. Click **"Tools"** (bottom left corner)
4. Click **"Secrets"** 
5. Add each of these (click **"Add new secret"** for each):

| Key | Value |
|-----|-------|
| BUSINESS_EMAIL | leanrwellness@gmail.com |
| BUSINESS_EMAIL_PASSWORD | ugxb naur dasv pkeg |
| ADMIN_USERNAME | admin |
| FLASK_ENV | production |
| HOST | 0.0.0.0 |
| CUSTOM_DOMAIN | leanrwellness.com |

6. Click the **"Restart"** button (top right of editor)
7. Wait 10 seconds for it to restart

✅ Secrets are added!

---

## STEP 4: Connect Your Domain

1. **In Replit:** 
   - Click **"Tools"** (bottom left)
   - Click **"Domains"**
   - Enter: `leanrwellness.com`
   - Click **"Add"**
   - Replit shows you 2 **Nameservers** (copy them)

2. **In Namecheap:**
   - Go to https://ap.namecheap.com/dashboard
   - Click your domain `leanrwellness.com`
   - Click **"Manage"**
   - Find **"Nameservers"** section
   - Change from "Namecheap BasicDNS" to **"Custom DNS"**
   - Paste Replit's 2 nameservers
   - Click **"Save"**

3. **Wait 24 hours** for DNS to update
   - You can check status at: https://mxtoolbox.com/
   - Search for `leanrwellness.com`

✅ Domain is connected!

---

## STEP 5: Test Your Live Store

After DNS updates (up to 24 hours):

1. Visit **https://leanrwellness.com** ✅
2. Add a product to cart
3. Click **"View Cart"**
4. Fill checkout form
5. Click **"Complete Order"**
6. Check your email for order confirmation ✅
7. Visit **https://leanrwellness.com/login.html**
8. Login with: `admin` / `Qx7m#K2$pL9@vN4b` ✅
9. Check orders in admin dashboard ✅

---

## If DNS Takes Too Long

While waiting for DNS (up to 24 hours), you can test at:
- **Temporary URL:** https://leanr-site.replit.dev

Just change the domain in that URL to test everything works!

---

## What Your Customers See

🌐 **https://leanrwellness.com**
- 6 products (RETATRUTIDE, TIRZEPETIDE, MT1, GHK-CU, KLOW PEN, CAGRI)
- Shopping cart
- Checkout with email-based ordering
- WhatsApp/Telegram buttons
- Customer reviews
- Newsletter signup

👨‍💼 **https://leanrwellness.com/login.html**
- Admin dashboard (admin / Qx7m#K2$pL9@vN4b)
- Order management
- Stock management
- Revenue analytics

---

## Troubleshooting

**Domain not working after 24 hours?**
- Clear browser cache (Ctrl+Shift+Delete)
- Try in incognito/private window
- Check nameservers updated correctly in Namecheap

**Can't push to GitHub?**
- Generate personal access token: https://github.com/settings/tokens
- Use that as password (not your GitHub password)

**Emails not sending?**
- Check BUSINESS_EMAIL_PASSWORD in Replit Secrets is correct
- Check spam folder
- Restart Replit app

**Admin login not working?**
- Clear localStorage: Open DevTools (F12) → Application → localStorage → delete all

---

## You're Almost There! 🎉

Follow these steps in order, and your LEANr store will be **LIVE** in about 30 minutes (including DNS wait time).

**Next:** Start with **STEP 1** - Initialize Git & push to GitHub

Need help? Come back and tell me what step you're on!
