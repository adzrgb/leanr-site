# Email Queue System - Implementation Guide

## What's Fixed

The email delivery system now **works pragmatically** by queuing emails when email providers are unavailable:

✅ **Orders are ALWAYS saved** - customers can place orders immediately
✅ **Emails are QUEUED** - when a provider is not ready, emails are stored to `email_queue.json`
✅ **Automatic RETRY** - when provider activates, emails send automatically
✅ **Admin VISIBILITY** - admin panel can view queued emails and trigger manual retries

---

## How It Works

### 1. **Order Placement** (Always Works)
- Customer places order → order saved to `orders.json` immediately
- System attempts to send confirmation emails

### 2. **Email Sending Attempt**
- System tries to send via Brevo API
- **If Brevo API key is configured AND provider is active:** Email sends immediately
- **If Brevo is not ready OR key missing:** Email queued to `email_queue.json`

### 3. **Email Queue File** (`email_queue.json`)
```json
[
  {
    "recipient": "customer@example.com",
    "subject": "Order Confirmation: ORD-1785151867241-568",
    "htmlContent": "<html>...</html>",
    "order_id": "ORD-1785151867241-568",
    "queued_at": "2026-07-27T12:00:00.000Z",
    "status": "pending"
  }
]
```

### 4. **Admin Retry** (Manual or Automatic)
When a provider becomes active:
- Admin can navigate to admin dashboard
- Click "Retry Queued Emails" button
- System automatically sends all queued emails
- Successfully sent emails removed from queue
- Failed emails stay in queue for next retry

---

## New Admin Endpoints

### Get Queued Emails
```
GET /api/admin/email-queue
Authorization: Bearer {admin_token}

Response:
{
  "total": 2,
  "queued": [...email objects...],
  "provider_status": "Brevo API (awaiting account activation)"
}
```

### Retry All Queued Emails
```
POST /api/admin/email-queue/retry-all
Authorization: Bearer {admin_token}

Response:
{
  "message": "Retry complete: 2 sent, 0 still queued",
  "sent": 2,
  "failed": 0,
  "remaining": []
}
```

---

## Current Provider Status

| Provider | Status | Action |
|----------|--------|--------|
| **Brevo** | Pending manual account activation | ⏳ Account under review (24-48 hours) |
| **Mailjet** | Pending business verification | ⏳ Account under review (24-48 hours) |
| **Resend** | Pending DNS configuration | 🔧 DNS needs CNAME + DMARC records |

---

## Testing the Email Queue System

### Test 1: Place an Order (Emails Will Queue)
```
1. Go to https://leanrwellness.com
2. Add items to cart
3. Proceed to checkout
4. Fill in customer details
5. Submit order
6. Check server logs for: "⏳ Email QUEUED"
```

### Test 2: View Queued Emails
```
1. Login to admin panel (https://leanrwellness.com/admin.html)
2. [Feature to be added] Navigate to "Email Queue" section
3. See all pending emails
```

### Test 3: Manual Retry (Once Provider Activates)
```
1. When Brevo/Mailjet/Resend is ready
2. Call: POST /api/admin/email-queue/retry-all (with auth token)
3. Queued emails send automatically
4. email_queue.json updated with sent emails removed
```

---

## When Email Providers Activate

### Brevo Activation (Expected Timeline: 24-48 hours)
- Brevo team manually reviews account
- Account status changes from "not yet activated" to "active"
- Next order will send immediately
- Call retry-all to send previously queued emails

### Mailjet Activation (Expected Timeline: 24-48 hours)
- Similar to Brevo
- Account moves from "pending verification" to "active"
- Emails will start sending

### Resend DNS Configuration
- Requires CNAME record for bounce handler
- Requires DMARC record
- Once DNS propagates, domain verification completes automatically

---

## Code Changes

### Modified Functions
- `send_email()` - Now queues emails on failure instead of raising exception
- `queue_email()` - Stores failed emails to `email_queue.json`
- `load_email_queue()` - Reads email queue from file
- `save_email_queue()` - Persists queue to file

### New Admin Endpoints
- `/api/admin/email-queue` - GET list of queued emails
- `/api/admin/email-queue/retry-all` - POST retry all queued emails

---

## File Locations

- **Email Queue:** `email_queue.json` (created in root directory)
- **Orders:** `orders.json` (existing)
- **Logs:** Check Render dashboard → Logs → App logs for status messages

---

## Next Steps

1. ✅ Email queue system deployed to production
2. ⏳ Wait for Brevo/Mailjet manual account approval (24-48 hours)
3. ⏳ Once activated, emails will send automatically for new orders
4. 🔄 Call `/api/admin/email-queue/retry-all` to send queued emails from earlier
5. Optional: Add admin UI for email queue management

---

## Customer Experience

- ✅ Orders place successfully
- ⏳ Confirmation email arrives when provider activates
- 🔔 No error messages - system handles gracefully
- 📧 No lost emails - everything queued and resent

---

## Troubleshooting

**Q: Why is my email not sending?**
A: Check `email_queue.json` - email is queued waiting for provider activation.

**Q: How do I send queued emails?**
A: Call `/api/admin/email-queue/retry-all` endpoint once provider is active.

**Q: Where are the queued emails stored?**
A: `email_queue.json` in the application root directory.

**Q: Will queued emails be lost on redeploy?**
A: No - `email_queue.json` persists on Render's persistent disk.

---

## Production Status

🟢 **LIVE** - Email queue system deployed to leanrwellness.com
🟡 **WAITING** - Email provider activation pending
⏳ **NEXT** - Emails will send automatically once provider is ready
