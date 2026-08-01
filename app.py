from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os
import secrets
import hashlib
import time
import random
from dotenv import load_dotenv
import threading
import sys
import requests
import smtplib
import base64
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

load_dotenv()

app = Flask(__name__)

# CORS configuration - allow requests from localhost and production
# For debugging: allow all origins
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration - load from environment variables for security
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "leanrwellness@gmail.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_ENABLED = os.getenv("BREVO_ENABLED", "false").lower() == "true"
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "LEANr Wellness <orders@leanrwellness.com>")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", BUSINESS_EMAIL)
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "LEANr Wellness")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", BUSINESS_EMAIL)
SMTP_PASSWORD = os.getenv("BUSINESS_EMAIL_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

print(f"DEBUG: EMAIL CONFIG - Business email: {BUSINESS_EMAIL}", flush=True)
print(f"DEBUG: Resend API key present: {'Yes' if RESEND_API_KEY else 'No - emails will not send'}", flush=True)
print(f"DEBUG: Brevo API key present: {'Yes' if BREVO_API_KEY else 'No'}", flush=True)
print(f"DEBUG: Brevo enabled: {'Yes' if BREVO_ENABLED else 'No'}", flush=True)
print(f"DEBUG: Resend from: {RESEND_FROM_EMAIL}", flush=True)
print(f"DEBUG: Brevo sender: {BREVO_SENDER_NAME} <{BREVO_SENDER_EMAIL}>", flush=True)
print(f"DEBUG: SMTP fallback configured: {'Yes' if SMTP_PASSWORD else 'No'}", flush=True)
print(f"DEBUG: Email provider priority: Resend, then Brevo, then SMTP, then queue", flush=True)

# Optional Supabase state storage (orders/stock/newsletter/queue).
# Email confirmation logic stays unchanged; only persistence backend changes.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STATE_TABLE = os.getenv("SUPABASE_STATE_TABLE", "app_state")
SUPABASE_STATE_KEY_COLUMN = os.getenv("SUPABASE_STATE_KEY_COLUMN", "state_key")
SUPABASE_STATE_VALUE_COLUMN = os.getenv("SUPABASE_STATE_VALUE_COLUMN", "state_value")
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

if SUPABASE_ENABLED:
    print(f"DEBUG: Supabase storage enabled via table '{SUPABASE_STATE_TABLE}'", flush=True)
else:
    print("DEBUG: Supabase storage disabled (using local files)", flush=True)

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("Qx7m#K2$pL9@vN4b".encode()).hexdigest()
ADMIN_TOKENS = {}  # Store active tokens

# File paths for data storage
DEFAULT_DATA_DIR = "."
if os.path.exists("/var/data"):
    DEFAULT_DATA_DIR = "/var/data"
DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
STOCK_FILE = os.path.join(DATA_DIR, "stock.json")
EMAILS_FILE = os.path.join(DATA_DIR, "newsletter_emails.json")
EMAIL_QUEUE_FILE = os.path.join(DATA_DIR, "email_queue.json")

ORDERS_KEY = "orders"
STOCK_KEY = "stock"
EMAILS_KEY = "newsletter_emails"
EMAIL_QUEUE_KEY = "email_queue"

print(f"DEBUG: DATA_DIR in use: {DATA_DIR}", flush=True)

def _seed_data_file(file_path, fallback_name):
    """Initialize data file in persistent dir from fallback project file if available."""
    if os.path.exists(file_path):
        return
    if os.path.exists(fallback_name):
        try:
            shutil.copyfile(fallback_name, file_path)
            print(f"DEBUG: Seeded {file_path} from {fallback_name}", flush=True)
        except Exception as copy_error:
            print(f"WARN: Could not seed {file_path}: {copy_error}", flush=True)

def _load_local_json(file_path, default):
    """Load JSON from local file, returning default if missing/invalid."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"WARN: Failed reading {file_path}: {e}", flush=True)
    return default

def _save_local_json(file_path, data):
    """Save JSON to local file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def _supabase_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

def _supabase_load_state(data_key):
    """Load JSON state blob from Supabase table using REST API."""
    if not SUPABASE_ENABLED:
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_STATE_TABLE}"
        params = {
            SUPABASE_STATE_KEY_COLUMN: f"eq.{data_key}",
            "select": SUPABASE_STATE_VALUE_COLUMN,
            "limit": "1"
        }
        response = requests.get(url, headers=_supabase_headers(), params=params, timeout=10)
        if response.status_code != 200:
            print(f"WARN: Supabase read failed for '{data_key}': {response.status_code} {response.text}", flush=True)
            return None
        rows = response.json() or []
        if not rows:
            return None
        return rows[0].get(SUPABASE_STATE_VALUE_COLUMN)
    except Exception as e:
        print(f"WARN: Supabase read exception for '{data_key}': {e}", flush=True)
        return None

def _supabase_save_state(data_key, data):
    """Upsert JSON state blob into Supabase table using REST API."""
    if not SUPABASE_ENABLED:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_STATE_TABLE}"
        params = {"on_conflict": SUPABASE_STATE_KEY_COLUMN}
        headers = _supabase_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        payload = [{
            SUPABASE_STATE_KEY_COLUMN: data_key,
            SUPABASE_STATE_VALUE_COLUMN: data
        }]
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        if response.status_code in (200, 201):
            return True
        print(f"WARN: Supabase write failed for '{data_key}': {response.status_code} {response.text}", flush=True)
        return False
    except Exception as e:
        print(f"WARN: Supabase write exception for '{data_key}': {e}", flush=True)
        return False

def load_state(data_key, file_path, default):
    """Load state from Supabase when configured, otherwise local file."""
    remote = _supabase_load_state(data_key)
    if remote is not None:
        return remote
    return _load_local_json(file_path, default)

def save_state(data_key, file_path, data):
    """Save state to Supabase when configured, and also mirror to local file."""
    _supabase_save_state(data_key, data)
    _save_local_json(file_path, data)

def load_orders_data():
    return load_state(ORDERS_KEY, ORDERS_FILE, [])

def save_orders_data(orders):
    save_state(ORDERS_KEY, ORDERS_FILE, orders)

def load_stock_data():
    return load_state(STOCK_KEY, STOCK_FILE, {})

def save_stock_data(stock):
    save_state(STOCK_KEY, STOCK_FILE, stock)

def load_newsletter_data():
    return load_state(EMAILS_KEY, EMAILS_FILE, [])

def save_newsletter_data(emails):
    save_state(EMAILS_KEY, EMAILS_FILE, emails)

def load_email_queue_data():
    return load_state(EMAIL_QUEUE_KEY, EMAIL_QUEUE_FILE, [])

def save_email_queue_data(queue):
    save_state(EMAIL_QUEUE_KEY, EMAIL_QUEUE_FILE, queue)

# Initialize stock file if it doesn't exist
default_stock = {
    "RETATRUTIDE": [
        {"name": "20mg", "stock": 50},
        {"name": "40mg", "stock": 50}
    ],
    "TIRZEPETIDE": [
        {"name": "30mg", "stock": 50},
        {"name": "60mg", "stock": 50}
    ],
    "MT1": [
        {"name": "Vial", "stock": 50},
        {"name": "Pen", "stock": 50}
    ],
    "GHK-CU": [
        {"name": "Vial", "stock": 50},
        {"name": "Pen", "stock": 50}
    ],
    "KLOW PEN": {"stock": 50},
    "CAGRI": {"stock": 50}
}

if not os.path.exists(STOCK_FILE):
    _seed_data_file(STOCK_FILE, "stock.json")

if not os.path.exists(STOCK_FILE):
    with open(STOCK_FILE, 'w') as f:
        json.dump(default_stock, f)

if not load_stock_data():
    save_stock_data(default_stock)

_seed_data_file(ORDERS_FILE, "orders.json")
_seed_data_file(EMAILS_FILE, "newsletter_emails.json")
_seed_data_file(EMAIL_QUEUE_FILE, "email_queue.json")

@app.route('/api/send-order', methods=['POST', 'OPTIONS'])
def send_order():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("=" * 50)
        print("NEW ORDER RECEIVED")
        print("=" * 50)
        
        data = request.json
        
        # Generate orderNumber if not provided (for API requests without frontend)
        if 'orderNumber' not in data or not data['orderNumber']:
            data['orderNumber'] = 'ORD-' + str(int(time.time() * 1000)) + '-' + str(random.randint(10000, 99999))
        
        # Generate timestamp if not provided
        if 'timestamp' not in data or not data['timestamp']:
            data['timestamp'] = datetime.now().isoformat()
        
        print(f"Order Number: {data.get('orderNumber')}")
        print(f"Customer: {data.get('customerName')}")
        print(f"Email: {data.get('customerEmail')}")
        
        # Create order summary
        items_html = ""
        for item in data['items']:
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item['name']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item.get('option', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{item['quantity']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">£{item['price'] * item['quantity']:.2f}</td>
            </tr>
            """
        
        # Save order FIRST
        orders = load_orders_data()
        
        order_record = {
            'orderNumber': data['orderNumber'],
            'customerName': data['customerName'],
            'customerEmail': data['customerEmail'],
            'customerPhone': data['customerPhone'],
            'deliveryAddress': data['deliveryAddress'],
            'city': data['city'],
            'postcode': data['postcode'],
            'orderNotes': data.get('orderNotes', ''),
            'useRoyalMailQr': data.get('useRoyalMailQr', False),
            'royalMailQrCode': data.get('royalMailQrCode', ''),
            'items': data['items'],
            'subtotal': data['subtotal'],
            'discountAmount': data.get('discountAmount', 0),
            'discountCode': data.get('discountCode', None),
            'postage': data.get('postage', 0),
            'total': data.get('total', data['subtotal']),
            'timestamp': data['timestamp'],
            'paymentConfirmed': False
        }
        
        orders.append(order_record)
        save_orders_data(orders)
        
        print(f"✓ Order saved to database")
        
        # Return success immediately - don't wait for emails
        result = jsonify({'success': True, 'orderNumber': data['orderNumber']})
        
        # Send emails in background thread (non-blocking)
        def send_emails_background():
            try:
                send_order_emails(data, items_html)
            except Exception as e:
                print(f"✗ Background email error: {str(e)}", flush=True)
                sys.stdout.flush()
        
        # Use daemon=False so Render waits for thread completion before terminating
        email_thread = threading.Thread(target=send_emails_background, daemon=False)
        email_thread.start()
        
        return result, 200
    
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

def send_order_emails(data, items_html):
    """Send order confirmation emails"""
    try:
        print(f"\n{'='*60}", flush=True)
        print(f"STARTING EMAIL SEND FOR ORDER: {data['orderNumber']}", flush=True)
        print(f"Customer: {data['customerEmail']}", flush=True)
        print(f"Business email: {BUSINESS_EMAIL}", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        qr_reference = data.get('royalMailQrCode', '')
        qr_reference_safe = qr_reference.replace('<', '&lt;').replace('>', '&gt;')
        qr_image_data = data.get('royalMailQrImageData', '')
        qr_image_name = (data.get('royalMailQrImageName', 'royalmail-qr') or 'royalmail-qr').rsplit('.', 1)[0]
        qr_photo_attachment = parse_data_url_attachment(qr_image_data, qr_image_name)
        qr_attachments = [qr_photo_attachment] if qr_photo_attachment else []
        
        # Business email body
        business_email_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #0052cc, #ec4899); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .order-details {{ background: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th {{ background: #f1f5f9; padding: 10px; text-align: left; font-weight: bold; }}
                    .total {{ font-size: 18px; font-weight: bold; color: #0052cc; margin-top: 15px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>New Order Received</h1>
                </div>
                <div class="content">
                    <h2>Order Number: {data['orderNumber']}</h2>
                    <p>Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    
                    <div class="order-details">
                        <h3>Customer Details</h3>
                        <p><strong>Name:</strong> {data['customerName']}</p>
                        <p><strong>Email:</strong> {data['customerEmail']}</p>
                        <p><strong>Phone:</strong> {data['customerPhone']}</p>
                    </div>
                    
                    <div class="order-details">
                        <h3>Delivery Address</h3>
                        <p>{data['deliveryAddress']}<br>{data['city']}<br>{data['postcode']}</p>
                    </div>

                    {f'''<div class="order-details">
                        <h3>Royal Mail QR</h3>
                        <p><strong>Customer selected Royal Mail QR option:</strong> Yes</p>
                        <p><strong>QR Code / Reference:</strong><br>{qr_reference_safe}</p>
                        <p><strong>Link:</strong> https://send.royalmail.com/ (Small Parcel)</p>
                        {"<p><strong>QR Photo:</strong> Attached to this email.</p>" if qr_photo_attachment else ""}
                    </div>''' if data.get('useRoyalMailQr') else ''}
                    
                    <h3>Order Items</h3>
                    <table>
                        <th>Product</th>
                        <th>Option</th>
                        <th>Qty</th>
                        <th>Total</th>
                        {items_html}
                    </table>
                    
                    <div style="text-align: right; margin: 20px 0;">
                        <p><strong>Subtotal:</strong> £{data.get('subtotal', 0):.2f}</p>
                        {f"<p style='color: #10b981;'><strong>Discount ({data.get('discountCode', 'N/A')}):</strong> -£{data.get('discountAmount', 0):.2f}</p>" if data.get('discountAmount', 0) > 0 else ""}
                        <p><strong>Postage:</strong> £{data.get('postage', 0):.2f}</p>
                        <div class="total" style="border-top: 2px solid #0052cc; padding-top: 10px;">
                            Total: £{data.get('total', data.get('subtotal', 0)):.2f}
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Customer email body
        customer_email_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #0052cc, #ec4899); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .order-details {{ background: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th {{ background: #f1f5f9; padding: 10px; text-align: left; font-weight: bold; }}
                    .total {{ font-size: 18px; font-weight: bold; color: #0052cc; margin-top: 15px; }}
                    .payment-section {{ background: #fffbeb; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ec4899; }}
                </style>
            </head>
            <body>
                <div class="header"><h1>LEANr Order Confirmation</h1></div>
                <div class="content">
                    <p>Hi {data['customerName']},</p>
                    <p>Thank you for your order!</p>
                    <h2>Order Number: {data['orderNumber']}</h2>
                    <div class="order-details">
                        <p>{data['deliveryAddress']}<br>{data['city']}<br>{data['postcode']}</p>
                    </div>
                    <table>
                        <th>Product</th><th>Option</th><th>Qty</th><th>Total</th>
                        {items_html}
                    </table>
                    <div style="text-align: right; margin: 20px 0;">
                        <p><strong>Subtotal:</strong> £{data.get('subtotal', 0):.2f}</p>
                        {f"<p style='color: #10b981;'><strong>Discount:</strong> -£{data.get('discountAmount', 0):.2f}</p>" if data.get('discountAmount', 0) > 0 else ""}
                        <p><strong>Postage:</strong> £{data.get('postage', 0):.2f}</p>
                        <div class="total">Total: £{data.get('total', data.get('subtotal', 0)):.2f}</div>
                    </div>
                    <div class="payment-section">
                        <h3>Payment Information</h3>
                        <p><strong>Option 1: PayPal</strong><br>leanrwellness@gmail.com</p>
                        <p><strong>Option 2: Bank Transfer</strong><br>Sort: 23-01-20 | Account: 13050648<br>Reference: {data['orderNumber'][-4:]}<br><em>Please use the name A W when making the transfer. Don't worry if the name does not match your bank — this is normal.</em></p>
                    </div>
                    {f'''<div class="order-details">
                        <h3>Royal Mail QR (Under £100 Orders)</h3>
                        <p>You selected Royal Mail QR postage. Please use <strong>Small Parcel</strong> on <a href="https://send.royalmail.com/">send.royalmail.com</a>.</p>
                        <p><strong>Your QR Code / Reference:</strong><br>{qr_reference_safe}</p>
                        {"<p><strong>Your QR Photo:</strong> Attached to this email.</p>" if qr_photo_attachment else ""}
                    </div>''' if data.get('useRoyalMailQr') else ''}
                </div>
            </body>
        </html>
        """
        
        # Send business email
        print(f"[1/2] Attempting to send BUSINESS email...", flush=True)
        sys.stdout.flush()
        business_sent, business_error = send_email(
            BUSINESS_EMAIL,
            f"New Order: {data['orderNumber']}",
            business_email_body,
            data['orderNumber'],
            attachments=qr_attachments
        )
        if business_sent:
            print(f"✓ Business email sent successfully", flush=True)
        else:
            print(f"⚠ Business email not delivered immediately: {business_error}", flush=True)
        sys.stdout.flush()

        # Send customer email (independent from business email result)
        print(f"[2/2] Attempting to send CUSTOMER email...", flush=True)
        sys.stdout.flush()
        customer_sent, customer_error = send_email(
            data['customerEmail'],
            f"Order Confirmation: {data['orderNumber']}",
            customer_email_body,
            data['orderNumber'],
            attachments=qr_attachments
        )
        if customer_sent:
            print(f"✓ Customer email sent successfully", flush=True)
        else:
            print(f"⚠ Customer email not delivered immediately: {customer_error}", flush=True)

        if business_sent and customer_sent:
            print(f"✓ ALL EMAILS SENT SUCCESSFULLY for order {data['orderNumber']}\n", flush=True)
        else:
            print(f"⚠ Order {data['orderNumber']} emails processed with queue fallback\n", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"✗ Email sending failed: {str(e)}", flush=True)
        sys.stdout.flush()
        import traceback
        print(traceback.format_exc(), flush=True)
        sys.stdout.flush()

def load_email_queue():
    """Load email queue from file"""
    try:
        return load_email_queue_data()
    except Exception:
        return []

def save_email_queue(queue):
    """Save email queue to file"""
    save_email_queue_data(queue)

def queue_email(recipient, subject, html_body, order_id="", last_error="", attachments=None):
    """Add email to queue for later sending"""
    queue = load_email_queue()
    queue.append({
        "recipient": recipient,
        "subject": subject,
        "htmlContent": html_body,
        "order_id": order_id,
        "attachments": attachments or [],
        "queued_at": datetime.now().isoformat(),
        "status": "pending",
        "last_error": last_error
    })
    save_email_queue(queue)
    print(f"    ⏳ Email QUEUED: {recipient}", flush=True)
    if last_error:
        print(f"    ⏳ Queue reason: {last_error}", flush=True)
    sys.stdout.flush()

def get_email_provider_status():
    """Return a human-readable provider status for admin/debug endpoints."""
    if RESEND_API_KEY:
        return "Resend API"
    if BREVO_API_KEY and BREVO_ENABLED:
        return "Brevo API"
    if SMTP_PASSWORD:
        return "SMTP"
    return "Queue only (no provider API key configured)"

def send_email(recipient, subject, html_body, order_id="", queue_on_fail=True, attachments=None):
    """Send email via configured providers. Returns (sent, error_message)."""
    try:
        print(f"\n  → Sending email to {recipient}...", flush=True)
        print(f"    Subject: {subject}", flush=True)
        attempt_errors = []
        normalized_attachments = attachments or []

        if RESEND_API_KEY:
            print(f"    Sending via Resend API...", flush=True)
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": RESEND_FROM_EMAIL,
                "reply_to": BUSINESS_EMAIL,
                "to": [recipient],
                "subject": subject,
                "html": html_body
            }
            if normalized_attachments:
                payload["attachments"] = [
                    {
                        "filename": item.get("filename", "attachment"),
                        "content": item.get("content", "")
                    }
                    for item in normalized_attachments if item.get("content")
                ]
            response = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                print(f"    ✓ Email sent successfully to {recipient}\n", flush=True)
                sys.stdout.flush()
                return True, ""

            resend_error = f"Resend API error: {response.status_code} - {response.text}"
            attempt_errors.append(resend_error)
            print(f"    ✗ {resend_error}", flush=True)
            sys.stdout.flush()
        else:
            attempt_errors.append("Resend skipped: missing API key")

        if BREVO_API_KEY and BREVO_ENABLED:
            print(f"    Sending via Brevo API...", flush=True)
            headers = {
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "sender": {
                    "email": BREVO_SENDER_EMAIL,
                    "name": BREVO_SENDER_NAME
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_body
            }
            if normalized_attachments:
                payload["attachment"] = [
                    {
                        "name": item.get("filename", "attachment"),
                        "content": item.get("content", "")
                    }
                    for item in normalized_attachments if item.get("content")
                ]
            response = requests.post(BREVO_URL, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201, 202]:
                print(f"    ✓ Email sent successfully to {recipient}\n", flush=True)
                sys.stdout.flush()
                return True, ""

            brevo_error = f"Brevo API error: {response.status_code} - {response.text}"
            attempt_errors.append(brevo_error)
            print(f"    ✗ {brevo_error}", flush=True)
            sys.stdout.flush()
        elif BREVO_API_KEY and not BREVO_ENABLED:
            attempt_errors.append("Brevo skipped: BREVO_ENABLED=false")
        else:
            attempt_errors.append("Brevo skipped: missing API key")

        if SMTP_PASSWORD:
            print(f"    Sending via SMTP fallback...", flush=True)
            try:
                message = MIMEMultipart()
                message["Subject"] = subject
                message["From"] = BUSINESS_EMAIL
                message["To"] = recipient
                message.attach(MIMEText(html_body, "html", "utf-8"))

                for item in normalized_attachments:
                    content_b64 = item.get("content", "")
                    if not content_b64:
                        continue
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(base64.b64decode(content_b64))
                    encoders.encode_base64(part)
                    filename = item.get("filename", "attachment")
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    message.attach(part)

                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
                if SMTP_USE_TLS:
                    server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(BUSINESS_EMAIL, [recipient], message.as_string())
                server.quit()

                print(f"    ✓ Email sent successfully via SMTP to {recipient}\n", flush=True)
                sys.stdout.flush()
                return True, ""
            except Exception as smtp_error:
                smtp_error_msg = f"SMTP error: {str(smtp_error)}"
                attempt_errors.append(smtp_error_msg)
                print(f"    ✗ {smtp_error_msg}", flush=True)
                sys.stdout.flush()
        else:
            attempt_errors.append("SMTP skipped: missing password")

        last_error = " | ".join(attempt_errors)
        if not last_error:
            last_error = "No delivery attempt was made"

        print(f"    ⚠ WARNING: {last_error}", flush=True)
        if queue_on_fail:
            queue_email(recipient, subject, html_body, order_id, last_error, normalized_attachments)
        return False, last_error
        
    except Exception as e:
        import traceback
        last_error = f"Exception: {str(e)}"
        print(f"    ✗ {last_error}", flush=True)
        traceback.print_exc()
        if queue_on_fail:
            queue_email(recipient, subject, html_body, order_id, last_error, normalized_attachments)
        sys.stdout.flush()
        return False, last_error

def parse_data_url_attachment(data_url, default_name="qr-photo"):
    """Convert a data URL to provider-compatible attachment payload."""
    if not data_url or not isinstance(data_url, str):
        return None
    if not data_url.startswith("data:") or "," not in data_url:
        return None

    header, content = data_url.split(",", 1)
    if ";base64" not in header or not content:
        return None

    mime_type = "application/octet-stream"
    if ":" in header:
        mime_type = header.split(":", 1)[1].split(";", 1)[0] or mime_type

    extension_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif"
    }
    extension = extension_map.get(mime_type, "bin")
    filename = f"{default_name}.{extension}"

    return {
        "filename": filename,
        "content": content,
        "content_type": mime_type
    }

# ==================== ADMIN ENDPOINTS ====================

def verify_token(token):
    """Verify admin token"""
    return token in ADMIN_TOKENS

@app.route('/api/admin/email-queue', methods=['GET', 'OPTIONS'])
def get_email_queue():
    """Get list of queued emails"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        queue = load_email_queue()
        return jsonify({
            'total': len(queue),
            'queued': queue,
            'provider_status': get_email_provider_status()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email-queue-debug', methods=['GET'])
def get_email_queue_debug():
    """DEBUG: Check email queue status (no auth required for testing)"""
    try:
        queue = load_email_queue()
        return jsonify({
            'status': 'Email Queue Debug',
            'total_queued': len(queue),
            'resend_api_key_set': bool(RESEND_API_KEY),
            'brevo_api_key_set': bool(BREVO_API_KEY),
            'brevo_enabled': BREVO_ENABLED,
            'smtp_password_set': bool(SMTP_PASSWORD),
            'provider_status': get_email_provider_status(),
            'business_email': BUSINESS_EMAIL,
            'recent_queued': queue[-5:] if queue else [],  # Last 5 queued
            'message': 'Emails will be sent via configured provider or queued on failure'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/email-queue/retry-all', methods=['POST', 'OPTIONS'])
def retry_all_queued_emails():
    """Retry sending all queued emails"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        queue = load_email_queue()
        sent = 0
        failed = 0
        still_queued = []
        
        for email in queue:
            try:
                delivered, error_message = send_email(
                    email['recipient'],
                    email['subject'],
                    email['htmlContent'],
                    email.get('order_id', ''),
                    queue_on_fail=False,
                    attachments=email.get('attachments', [])
                )

                if delivered:
                    sent += 1
                    print(f"✓ Queued email SENT to {email['recipient']}", flush=True)
                else:
                    email['last_error'] = error_message
                    email['last_retry_at'] = datetime.now().isoformat()
                    still_queued.append(email)
                    failed += 1
                    print(f"⚠ Email still queued for {email['recipient']}", flush=True)
            except Exception as e:
                still_queued.append(email)
                failed += 1
                print(f"✗ Failed to retry email to {email['recipient']}: {str(e)}", flush=True)
        
        # Save remaining queued emails
        save_email_queue(still_queued)
        
        return jsonify({
            'message': f'Retry complete: {sent} sent, {failed} still queued',
            'sent': sent,
            'failed': failed,
            'remaining': still_queued
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login.html')
def serve_login():
    """Serve corrected login page"""
    with open('login.html') as f:
        html = f.read()
    # Replace the entire problematic fetch block with corrected version
    old_fetch = """const response = await fetch('http://127.0.0.1:5000/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'omit',
          body: JSON.stringify({ username, password })
        }).catch(() => 
          fetch('http://localhost:5000/api/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'omit',
            body: JSON.stringify({ username, password })
          })
        );"""
    
    new_fetch = """const response = await fetch(window.location.origin + '/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ username, password })
        });"""
    
    html = html.replace(old_fetch, new_fetch)
    return html

@app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
def admin_login():
    """Admin login endpoint"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # DEBUG: Log credentials
        print(f"DEBUG: username={username}, ADMIN_USERNAME={ADMIN_USERNAME}")
        print(f"DEBUG: password_hash={password_hash}")
        print(f"DEBUG: ADMIN_PASSWORD_HASH={ADMIN_PASSWORD_HASH}")
        
        if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
            # Generate token
            token = secrets.token_urlsafe(32)
            ADMIN_TOKENS[token] = {
                'username': username,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✓ Admin login successful for {username}")
            return jsonify({'success': True, 'token': token}), 200
        else:
            print(f"✗ Admin login failed - invalid credentials")
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/orders', methods=['GET'])
def get_orders():
    """Retrieve all orders"""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        orders = load_orders_data()
        
        print(f"✓ Retrieved {len(orders)} orders")
        return jsonify({'orders': orders}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/delete-order', methods=['POST', 'OPTIONS'])
def delete_order():
    """Delete an order from admin dashboard"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        data = request.json or {}
        order_number = data.get('orderNumber')
        if not order_number:
            return jsonify({'error': 'Missing order number'}), 400

        orders = load_orders_data()

        original_count = len(orders)
        filtered_orders = [o for o in orders if o.get('orderNumber') != order_number]

        if len(filtered_orders) == original_count:
            return jsonify({'error': 'Order not found'}), 404

        save_orders_data(filtered_orders)

        print(f"✓ Deleted order {order_number}")
        return jsonify({'success': True, 'message': f'Order {order_number} deleted'}), 200
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/send-tracking', methods=['POST', 'OPTIONS'])
def send_tracking():
    """Send tracking number to customer"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.json or {}
        order_number = data.get('orderNumber')
        tracking_number = (data.get('trackingNumber') or '').strip()

        if not order_number:
            return jsonify({'error': 'Order number is required'}), 400
        if not tracking_number:
            return jsonify({'error': 'Tracking number is required'}), 400
        
        # Find order and update
        orders = load_orders_data()
        
        order = next((o for o in orders if o['orderNumber'] == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Update tracking number
        order['trackingNumber'] = tracking_number
        save_orders_data(orders)
        
        # Send email to customer
        tracking_email_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #0052cc, #ec4899); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .tracking-section {{ background: #f0f9ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0052cc; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Your LEANr Order is on the Way!</h1>
                </div>
                <div class="content">
                    <p>Hi {order['customerName']},</p>
                    <p>Great news! Your order has been dispatched.</p>
                    
                    <div class="tracking-section">
                        <h3>Order Number: {order_number}</h3>
                        <p><strong>Tracking Number:</strong> {tracking_number}</p>
                        <p>You can track your package using this tracking number with the carrier.</p>
                    </div>
                    
                    <p>Thank you for your order!<br>
                    The LEANr Team</p>
                </div>
            </body>
        </html>
        """
        
        customer_email = order.get('customerEmail') or order.get('email')
        if not customer_email:
            return jsonify({'error': 'Customer email not found for this order'}), 400

        sent, send_error = send_email(
            customer_email,
            f"Your Order {order_number} is on the Way! - Tracking: {tracking_number}",
            tracking_email_body,
            order_number
        )

        if not sent:
            return jsonify({
                'error': 'Tracking email could not be delivered immediately',
                'details': send_error
            }), 502

        print(f"✓ Tracking email sent for order {order_number}")
        return jsonify({'success': True, 'message': 'Tracking number sent to customer'}), 200
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/confirm-payment', methods=['POST', 'OPTIONS'])
def confirm_payment():
    """Confirm payment and send confirmation email to customer"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.json or {}
        order_number = data.get('orderNumber')

        if not order_number:
            return jsonify({'error': 'Order number is required'}), 400
        
        # Find order and update
        orders = load_orders_data()
        
        order = next((o for o in orders if o['orderNumber'] == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Mark payment as confirmed
        order['paymentConfirmed'] = True
        save_orders_data(orders)
        
        # Send payment confirmation email to customer
        payment_confirmation_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #0052cc, #7c3aed); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .confirmation-section {{ background: #dcfce7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
                    .confirmation-badge {{ display: inline-block; background: #10b981; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; margin: 10px 0; }}
                    .order-details {{ background: #f8fafc; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .order-details p {{ margin: 8px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                    th, td {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
                    th {{ background: #f1f5f9; font-weight: bold; }}
                    .total-row {{ background: #f1f5f9; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>✓ Payment Confirmed</h1>
                </div>
                <div class="content">
                    <p>Hi {order['customerName']},</p>
                    <p>Your payment has been confirmed by LEANr. Thank you for your order!</p>
                    
                    <div class="confirmation-section">
                        <div class="confirmation-badge">✓ Payment Confirmed</div>
                        <h3>Order Number: {order_number}</h3>
                        <p>We've received your payment and are processing your order.</p>
                    </div>
                    
                    <div class="order-details">
                        <h4>Order Summary:</h4>
                        <table>
                            <tr>
                                <th>Product</th>
                                <th>Quantity</th>
                                <th>Price</th>
                                <th>Total</th>
                            </tr>
        """
        
        # Add items to email
        for item in order.get('items', []):
            item_total = item['price'] * item['quantity']
            payment_confirmation_body += f"""
                            <tr>
                                <td>{item['name']} ({item['option']})</td>
                                <td>{item['quantity']}</td>
                                <td>£{item['price']:.2f}</td>
                                <td>£{item_total:.2f}</td>
                            </tr>
            """
        
        # Add totals
        discount_amount = order.get('discountAmount', 0)
        postage = order.get('postage', 0)
        total = order.get('total', order.get('subtotal', 0))
        
        payment_confirmation_body += f"""
                            <tr class="total-row">
                                <td colspan="3" style="text-align: right;">Subtotal:</td>
                                <td>£{order.get('subtotal', 0):.2f}</td>
                            </tr>
        """
        
        if discount_amount > 0:
            payment_confirmation_body += f"""
                            <tr class="total-row" style="background: #dcfce7;">
                                <td colspan="3" style="text-align: right;">Discount ({order.get('discountCode', 'N/A')}):</td>
                                <td style="color: #10b981;">-£{discount_amount:.2f}</td>
                            </tr>
            """
        
        payment_confirmation_body += f"""
                            <tr class="total-row">
                                <td colspan="3" style="text-align: right;">Postage:</td>
                                <td>£{postage:.2f}</td>
                            </tr>
                            <tr class="total-row" style="font-size: 1.2em;">
                                <td colspan="3" style="text-align: right;">Total:</td>
                                <td>£{total:.2f}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p><strong>What's Next?</strong><br>
                    Your order will be processed and dispatched shortly. You'll receive a tracking number email once it's on its way.</p>
                    
                    <p>Thank you for shopping with LEANr!<br>
                    The LEANr Team</p>
                </div>
            </body>
        </html>
        """
        
        customer_email = order.get('customerEmail') or order.get('email')
        if not customer_email:
            return jsonify({'error': 'Customer email not found for this order'}), 400

        sent, send_error = send_email(
            customer_email,
            f"Payment Confirmed - Order {order_number}",
            payment_confirmation_body,
            order_number
        )

        if not sent:
            return jsonify({
                'error': 'Payment was confirmed but email could not be delivered immediately',
                'details': send_error
            }), 502
        
        print(f"✓ Payment confirmation email sent for order {order_number}")
        return jsonify({'success': True, 'message': 'Payment confirmed and email sent to customer'}), 200
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stock', methods=['GET'])
def get_stock():
    """Get current stock levels"""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        stock_data = load_stock_data()
        
        # Format for frontend
        stock_list = []
        for product_name, product_data in stock_data.items():
            if isinstance(product_data, list):
                stock_list.append({
                    'name': product_name,
                    'variants': product_data
                })
            else:
                stock_list.append({
                    'name': product_name,
                    'stock': product_data.get('stock', 0)
                })
        
        return jsonify({'stock': stock_list}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-stock', methods=['POST', 'OPTIONS'])
def update_stock():
    """Update stock levels"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.json or {}
        product_name = data.get('productName')
        variant = data.get('variant')
        new_stock = data.get('stock')

        if not product_name or not variant:
            return jsonify({'error': 'Missing product or variant'}), 400

        try:
            new_stock = int(new_stock)
        except (TypeError, ValueError):
            return jsonify({'error': 'Stock must be a whole number'}), 400

        if new_stock < 0:
            return jsonify({'error': 'Stock cannot be negative'}), 400
        
        stock_data = load_stock_data()
        
        if product_name not in stock_data:
            return jsonify({'error': 'Product not found'}), 404
        
        updated = False

        if variant == 'default':
            if not isinstance(stock_data[product_name], dict):
                return jsonify({'error': 'Invalid product stock format'}), 400
            stock_data[product_name]['stock'] = new_stock
            updated = True
        else:
            # Find and update variant
            product = stock_data[product_name]
            if isinstance(product, list):
                for v in product:
                    if v['name'] == variant:
                        v['stock'] = new_stock
                        updated = True
                        break

        if not updated:
            return jsonify({'error': 'Variant not found'}), 404
        
        save_stock_data(stock_data)
        
        print(f"✓ Updated stock: {product_name} {variant} = {new_stock}")
        return jsonify({'success': True, 'message': 'Stock updated', 'stock': new_stock}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Public endpoint for stock data (no auth required)
@app.route('/api/public/stock', methods=['GET'])
def get_public_stock():
    try:
        stock_data = load_stock_data()
        
        # Format stock data for frontend
        stock_list = []
        for product_name, product_info in stock_data.items():
            if isinstance(product_info, list):
                # Product with variants
                stock_list.append({
                    'name': product_name,
                    'variants': product_info
                })
            else:
                # Product without variants
                stock_list.append({
                    'name': product_name,
                    'stock': product_info.get('stock', 0)
                })
        
        return jsonify({'stock': stock_list}), 200
    except Exception as e:
        print(f"ERROR fetching stock: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Newsletter email endpoint
@app.route('/api/newsletter/subscribe', methods=['POST', 'OPTIONS'])
def newsletter_subscribe():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        # Load existing emails
        emails = load_newsletter_data()
        
        # Check if already subscribed
        if email in emails:
            return jsonify({'success': True, 'message': 'Already subscribed'}), 200
        
        # Add new email
        emails.append(email)
        save_newsletter_data(emails)
        
        print(f"✓ Newsletter subscription: {email}")
        return jsonify({'success': True, 'message': 'Subscribed successfully'}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Admin dashboard stats
@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401
        
        orders = load_orders_data()
        
        # Calculate stats
        total_revenue = sum(o.get('total', o.get('subtotal', 0)) for o in orders)
        total_orders = len(orders)
        
        # Get top products
        product_counts = {}
        for order in orders:
            for item in order.get('items', []):
                product_name = item['name']
                product_counts[product_name] = product_counts.get(product_name, 0) + item.get('quantity', 1)
        
        top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats = {
            'totalRevenue': f"£{total_revenue:.2f}",
            'totalOrders': total_orders,
            'topProducts': [{'name': name, 'sold': count} for name, count in top_products]
        }
        
        print(f"✓ Retrieved stats: {total_orders} orders, £{total_revenue:.2f} revenue")
        return jsonify(stats), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== STATIC FILE ROUTES ====================

@app.route('/')
def serve_index():
    """Serve index.html"""
    with open('index.html') as f:
        return f.read()

@app.route('/index.html')
def serve_index_explicit():
    """Serve index.html (explicit route)"""
    with open('index.html') as f:
        return f.read()

@app.route('/cart.html')
def serve_cart():
    """Serve cart.html"""
    with open('cart.html') as f:
        return f.read()

@app.route('/admin.html')
def serve_admin():
    """Serve admin.html"""
    with open('admin.html') as f:
        return f.read(), 200, {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0'
        }

# Serve CSS and JavaScript files
@app.route('/styles.css')
def serve_styles():
    """Serve styles.css"""
    with open('styles.css') as f:
        return f.read(), 200, {'Content-Type': 'text/css'}

@app.route('/script.js')
def serve_script():
    """Serve script.js"""
    with open('script.js') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}

@app.route('/cart-script.js')
def serve_cart_script():
    """Serve cart-script.js"""
    with open('cart-script.js') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host=host, port=port)
