# 🚀 Quick Start - Deploy LEANr in 5 Minutes

## Step 1: Push to GitHub (5 min)

```bash
# In your leanr-site directory
git init
git add .
git commit -m "LEANr e-commerce"
git remote add origin https://github.com/YOUR-USERNAME/leanr-site.git
git push -u origin main
```

Need GitHub? Go to https://github.com and sign up (free)

---

## Step 2: Deploy on Replit (2 min)

1. Go to https://replit.com and sign up (free)
2. Click **"Create"** → **"Import from GitHub"**
3. Paste: `https://github.com/YOUR-USERNAME/leanr-site.git`
4. Click Import
5. Replit auto-deploys! ✅ Your app is live at `https://leanr-site.replit.dev`

---

## Step 3: Add Secrets (2 min)

1. In Replit, click **Tools** (bottom left) → **Secrets**
2. Add these:

| Key | Value |
|-----|-------|
| BUSINESS_EMAIL | leanrwellness@gmail.com |
| BUSINESS_EMAIL_PASSWORD | ugxb naur dasv pkeg |
| ADMIN_USERNAME | admin |
| FLASK_ENV | production |
| HOST | 0.0.0.0 |

3. Click Replit's restart button (top right)

---

## Step 4: Get a Custom Domain (Optional but Recommended)

### Option A: Free Domain (Freenom)
1. Go to https://www.freenom.com
2. Search for domain (e.g., leanr.tk)
3. Select 12 months free
4. Sign up and claim domain
5. Get nameservers from Replit (see Step 5)
6. Update in Freenom settings
7. **Cost: FREE** ✅

### Option B: Premium Domain (Namecheap) 
1. Go to https://namecheap.com
2. Search for domain (e.g., leanr.com)
3. Buy (usually $0.99-$10 first year)
4. Get nameservers from Replit (see Step 5)
5. Update in Namecheap settings
6. **Cost: ~$0.99-$10/year**

---

## Step 5: Connect Domain to Replit

1. In Replit → **Tools** → **Domains**
2. Enter your domain name
3. Click **Add Domain**
4. Replit shows you **Nameservers** (copy them)
5. Go to your domain registrar (Freenom/Namecheap)
6. Find "Nameservers" settings
7. Replace with Replit's nameservers
8. Save
9. **Wait 24 hours** for DNS to update
10. Visit https://yourdomain.com ✅

---

## That's It! 🎉

Your LEANr store is now live online!

### Quick Links
- **Your Store:** https://yourdomain.com
- **Admin Login:** https://yourdomain.com/login.html
- **Admin Credentials:** admin / leanr123

---

## Troubleshooting

**Domain not working after 24 hours?**
- Clear browser cache
- Try incognito/private window
- Check nameservers were updated correctly

**Emails not sending?**
- Verify Gmail app password in Secrets
- Check spam folder
- Make sure BUSINESS_EMAIL is correct

**Admin dashboard not loading?**
- Clear localStorage in browser
- Try logging in again
- Check Replit logs for errors (click "Console" in Replit)

---

## First Order Test

1. Go to https://yourdomain.com
2. Add a product to cart
3. Fill out checkout form
4. Submit order
5. Check your email for confirmation
6. Log into admin at https://yourdomain.com/login.html
7. Verify order appears in Orders tab ✅

---

**Questions?** Check the full README.md or DEPLOYMENT_CHECKLIST.md for more details.

**You've got this!** 💪
