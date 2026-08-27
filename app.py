from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
import secrets
import hashlib
from html import escape
import time
import random
import re
from dotenv import load_dotenv
import threading
import sys
import requests
import smtplib
import base64
import shutil
from zoneinfo import ZoneInfo
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
AUTO_PRINT_LABELS = os.getenv("AUTO_PRINT_LABELS", "false").lower() == "true"
PRINTNODE_API_KEY = os.getenv("PRINTNODE_API_KEY", "")
PRINTNODE_PRINTER_ID = os.getenv("PRINTNODE_PRINTER_ID", "")
SENDCLOUD_ENABLED = os.getenv("SENDCLOUD_ENABLED", "false").lower() == "true"
SENDCLOUD_PUBLIC_KEY = os.getenv("SENDCLOUD_PUBLIC_KEY", "")
SENDCLOUD_SECRET_KEY = os.getenv("SENDCLOUD_SECRET_KEY", "")
SENDCLOUD_BASE_URL = os.getenv("SENDCLOUD_BASE_URL", "https://panel.sendcloud.sc/api/v2").rstrip("/")
SENDCLOUD_SHIPPING_METHOD_ID = os.getenv("SENDCLOUD_SHIPPING_METHOD_ID", "")
SENDCLOUD_DEFAULT_COUNTRY = os.getenv("SENDCLOUD_DEFAULT_COUNTRY", "GB")
SENDCLOUD_METHOD_HINT = os.getenv("SENDCLOUD_METHOD_HINT", "tracked 24")

print(f"DEBUG: EMAIL CONFIG - Business email: {BUSINESS_EMAIL}", flush=True)
print(f"DEBUG: Resend API key present: {'Yes' if RESEND_API_KEY else 'No - emails will not send'}", flush=True)
print(f"DEBUG: Brevo API key present: {'Yes' if BREVO_API_KEY else 'No'}", flush=True)
print(f"DEBUG: Brevo enabled: {'Yes' if BREVO_ENABLED else 'No'}", flush=True)
print(f"DEBUG: Resend from: {RESEND_FROM_EMAIL}", flush=True)
print(f"DEBUG: Brevo sender: {BREVO_SENDER_NAME} <{BREVO_SENDER_EMAIL}>", flush=True)
print(f"DEBUG: SMTP fallback configured: {'Yes' if SMTP_PASSWORD else 'No'}", flush=True)
print(f"DEBUG: Email provider priority: Resend, then Brevo, then SMTP, then queue", flush=True)
print(f"DEBUG: Auto print labels enabled: {'Yes' if AUTO_PRINT_LABELS else 'No'}", flush=True)
print(f"DEBUG: PrintNode configured: {'Yes' if PRINTNODE_API_KEY and PRINTNODE_PRINTER_ID else 'No'}", flush=True)
print(f"DEBUG: Sendcloud enabled: {'Yes' if SENDCLOUD_ENABLED else 'No'}", flush=True)
print(f"DEBUG: Sendcloud configured: {'Yes' if SENDCLOUD_PUBLIC_KEY and SENDCLOUD_SECRET_KEY else 'No'}", flush=True)

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
DISCOUNT_SETTINGS_FILE = os.path.join(DATA_DIR, "discount_settings.json")
PRODUCT_VISIBILITY_FILE = os.path.join(DATA_DIR, "product_visibility.json")
PRODUCT_SUGGESTIONS_FILE = os.path.join(DATA_DIR, "product_suggestions.json")

ORDERS_KEY = "orders"
STOCK_KEY = "stock"
EMAILS_KEY = "newsletter_emails"
EMAIL_QUEUE_KEY = "email_queue"
DISCOUNT_SETTINGS_KEY = "discount_settings"
PRODUCT_VISIBILITY_KEY = "product_visibility"
PRODUCT_SUGGESTIONS_KEY = "product_suggestions"

DEFAULT_DISCOUNT_SETTINGS = {
    "enabled": True,
    "code": "BANKHOLIDAY15",
    "percent": 15,
    "starts_at": "2026-08-25T00:00:00",
    "ends_at": "2026-09-01T00:00:00",
    "secret_enabled": False
}

DEFAULT_PRODUCT_VISIBILITY = {
    "RETATRUTIDE": True,
    "TIRZEPETIDE": True,
    "MT1": True,
    "MT2": True,
    "MULTI BUY BUNDLE": True,
    "GHK-CU": True,
    "KLOW PEN": True,
    "CAGRI": True,
    "NAD+": True,
    "MOTS-C": True,
    "SELANK": True,
    "SEMAX": True
}

SECRET_DISCOUNT_CODE = "QUEENS"
SECRET_DISCOUNT_PERCENT = 10
PAYPAL_FEE_PERCENT = 2.9
SALE_GIFT_NAMES = {
    "MT2": "Nasal - Free bank holiday gift",
    "GHK-CU": "Pen - Free bank holiday gift"
}

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

def load_product_suggestions_data():
    return load_state(PRODUCT_SUGGESTIONS_KEY, PRODUCT_SUGGESTIONS_FILE, [])

def save_product_suggestions_data(suggestions):
    save_state(PRODUCT_SUGGESTIONS_KEY, PRODUCT_SUGGESTIONS_FILE, suggestions)

def load_email_queue_data():
    return load_state(EMAIL_QUEUE_KEY, EMAIL_QUEUE_FILE, [])

def save_email_queue_data(queue):
    save_state(EMAIL_QUEUE_KEY, EMAIL_QUEUE_FILE, queue)

def load_discount_settings_data():
    return load_state(DISCOUNT_SETTINGS_KEY, DISCOUNT_SETTINGS_FILE, DEFAULT_DISCOUNT_SETTINGS)

def save_discount_settings_data(settings):
    save_state(DISCOUNT_SETTINGS_KEY, DISCOUNT_SETTINGS_FILE, settings)

def get_discount_settings():
    """Return validated discount settings with safe defaults."""
    raw = load_discount_settings_data()
    if not isinstance(raw, dict):
        raw = {}

    configured_enabled = bool(raw.get('enabled', DEFAULT_DISCOUNT_SETTINGS['enabled']))
    enabled = configured_enabled
    code = str(raw.get('code', DEFAULT_DISCOUNT_SETTINGS['code'])).strip().upper() or DEFAULT_DISCOUNT_SETTINGS['code']

    try:
        percent = int(raw.get('percent', DEFAULT_DISCOUNT_SETTINGS['percent']))
    except (TypeError, ValueError):
        percent = DEFAULT_DISCOUNT_SETTINGS['percent']

    if percent < 0:
        percent = 0

    starts_at = str(raw.get('starts_at', DEFAULT_DISCOUNT_SETTINGS['starts_at']))
    ends_at = str(raw.get('ends_at', DEFAULT_DISCOUNT_SETTINGS['ends_at']))
    try:
        now = datetime.now(ZoneInfo('Europe/London')).replace(tzinfo=None)
        enabled = enabled and datetime.fromisoformat(starts_at) <= now < datetime.fromisoformat(ends_at)
    except (TypeError, ValueError):
        enabled = False

    return {
        'enabled': enabled,
        'configured_enabled': configured_enabled,
        'code': code,
        'percent': percent,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'secret_enabled': bool(raw.get('secret_enabled', DEFAULT_DISCOUNT_SETTINGS['secret_enabled']))
    }

def get_sale_gift_stock(stock_data=None):
    """Return the available stock for the bank holiday free gifts."""
    if stock_data is None:
        stock_data = load_stock_data()

    mt2_stock = _get_variant_stock(stock_data, 'MT2', 'Nasal') or 0
    ghkcu_stock = _get_variant_stock(stock_data, 'GHK-CU', 'Pen') or 0
    return {
        'MT2': int(mt2_stock),
        'GHK-CU': int(ghkcu_stock)
    }


def get_sale_gift_tier(subtotal, discount_percent=0, stock_data=None):
    """Return the eligible free gift tier based on the discounted subtotal and gift stock."""
    subtotal_value = float(subtotal or 0)
    percent_value = float(discount_percent or 0)
    if percent_value < 0:
        percent_value = 0

    discounted_subtotal = subtotal_value * (1 - (percent_value / 100))
    available_stock = get_sale_gift_stock(stock_data)

    if discounted_subtotal >= 200:
        return 'GHK-CU' if available_stock['GHK-CU'] > 0 else None
    if discounted_subtotal >= 150:
        return 'MT2' if available_stock['MT2'] > 0 else None
    return None


def set_discount_enabled(enabled):
    settings = get_discount_settings()
    settings['enabled'] = bool(enabled)
    save_discount_settings_data(settings)
    return settings

def load_product_visibility_data():
    return load_state(PRODUCT_VISIBILITY_KEY, PRODUCT_VISIBILITY_FILE, DEFAULT_PRODUCT_VISIBILITY)

def save_product_visibility_data(visibility):
    save_state(PRODUCT_VISIBILITY_KEY, PRODUCT_VISIBILITY_FILE, visibility)

def get_product_visibility():
    raw = load_product_visibility_data()
    if not isinstance(raw, dict):
        raw = {}

    return {
        product_name: bool(raw.get(product_name, is_visible))
        for product_name, is_visible in DEFAULT_PRODUCT_VISIBILITY.items()
    }

def set_product_visibility(visibility):
    current = get_product_visibility()
    for product_name in DEFAULT_PRODUCT_VISIBILITY:
        if product_name in visibility:
            current[product_name] = bool(visibility[product_name])
    save_product_visibility_data(current)
    return current

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
    "MT2": [
        {"name": "Nasal", "stock": 50},
        {"name": "Pen", "stock": 50}
    ],
    "GHK-CU": [
        {"name": "Vial", "stock": 50},
        {"name": "Pen", "stock": 50}
    ],
    "KLOW PEN": {"stock": 50},
    "CAGRI": {"stock": 50},
    "NAD+": {"stock": 50},
    "MOTS-C": {"stock": 50},
    "SELANK": {"stock": 50},
    "SEMAX": {"stock": 50}
}

if not os.path.exists(STOCK_FILE):
    _seed_data_file(STOCK_FILE, "stock.json")

if not os.path.exists(STOCK_FILE):
    with open(STOCK_FILE, 'w') as f:
        json.dump(default_stock, f)

if not load_stock_data():
    save_stock_data(default_stock)

# Ensure new products/variants are added to existing stock files without
# overwriting current quantities for already configured items.
current_stock = load_stock_data()
stock_changed = False

# MT2 variant update: migrate legacy "Vial" stock to "Nasal".
if isinstance(current_stock.get("MT2"), list):
    mt2_variants = current_stock["MT2"]
    has_nasal = any(v.get("name") == "Nasal" for v in mt2_variants)
    if not has_nasal:
        for variant in mt2_variants:
            if variant.get("name") == "Vial":
                variant["name"] = "Nasal"
                stock_changed = True
                break

for product_name, default_value in default_stock.items():
    if product_name not in current_stock:
        current_stock[product_name] = default_value
        stock_changed = True

if stock_changed:
    save_stock_data(current_stock)

current_discount_settings = load_discount_settings_data()
if not current_discount_settings:
    save_discount_settings_data(DEFAULT_DISCOUNT_SETTINGS)
elif current_discount_settings.get('starts_at') == '2026-08-26T00:00:00':
    save_discount_settings_data(DEFAULT_DISCOUNT_SETTINGS)

if not load_product_visibility_data():
    save_product_visibility_data(DEFAULT_PRODUCT_VISIBILITY)

_seed_data_file(ORDERS_FILE, "orders.json")
_seed_data_file(EMAILS_FILE, "newsletter_emails.json")
_seed_data_file(EMAIL_QUEUE_FILE, "email_queue.json")

if not os.path.exists(PRODUCT_SUGGESTIONS_FILE):
    save_product_suggestions_data([])

def _extract_variant_name(option_value):
    """Normalize cart option text to a stock variant name."""
    if not option_value:
        return "default"

    raw_value = str(option_value).strip()
    if not raw_value:
        return "default"

    # Frontend variants are stored as texts like:
    # "20mg — £89", "Pen - Free bank holiday gift", "Nasal — £35 (...)"
    # We only need the variant name before the pricing or gift suffix.
    parts = re.split(r"\s*(?:—|–|-)\s*", raw_value, maxsplit=1)
    normalized = parts[0].strip()
    return normalized or "default"

def _get_mt2_nasal_stock_multiplier(option_value):
    """Return stock multiplier for MT2 Nasal based on selected strength text."""
    option_text = str(option_value or "").lower()
    return 2 if "20mg total" in option_text else 1

BUNDLE_PRODUCT_NAME = "MULTI BUY BUNDLE"
BUNDLE_COMPONENTS = [
    ("GHK-CU", "Pen"),
    ("MT2", "Nasal"),
    ("MT2", "Pen")
]

def _get_variant_stock(stock_data, product_name, variant_name):
    """Return stock integer for a product variant, or None if missing."""
    product_stock = stock_data.get(product_name)
    if not isinstance(product_stock, list):
        return None
    variant_obj = next((v for v in product_stock if v.get('name') == variant_name), None)
    if not variant_obj:
        return None
    return int(variant_obj.get('stock', 0))

def _calculate_bundle_stock(stock_data):
    """Bundle availability equals the lowest stock among required components."""
    component_levels = []
    for product_name, variant_name in BUNDLE_COMPONENTS:
        variant_stock = _get_variant_stock(stock_data, product_name, variant_name)
        if variant_stock is None:
            return 0
        component_levels.append(variant_stock)
    return min(component_levels) if component_levels else 0

def decrement_stock_for_order_items(items):
    """Reduce stock for each ordered item. Returns (ok, error_message)."""
    stock_data = load_stock_data()
    decrements = {}

    for item in items or []:
        product_name = str(item.get('name', '')).strip()
        if not product_name:
            return False, "Order item is missing product name"

        try:
            quantity = int(item.get('quantity', 0))
        except (TypeError, ValueError):
            return False, f"Invalid quantity for {product_name}"

        if quantity <= 0:
            return False, f"Quantity must be greater than 0 for {product_name}"

        if product_name == BUNDLE_PRODUCT_NAME:
            for bundle_product, bundle_variant in BUNDLE_COMPONENTS:
                key = f"{bundle_product}|{bundle_variant}"
                decrements[key] = decrements.get(key, 0) + quantity
            continue

        option_value = item.get('option')
        variant_name = _extract_variant_name(option_value)
        effective_quantity = quantity

        # MT2 Nasal 20mg total uses two 10mg stock units.
        if product_name == "MT2" and variant_name == "Nasal":
            effective_quantity = quantity * _get_mt2_nasal_stock_multiplier(option_value)

        key = f"{product_name}|{variant_name}"
        decrements[key] = decrements.get(key, 0) + effective_quantity

    # Validate availability first so we never partially decrement stock.
    for key, quantity in decrements.items():
        product_name, variant_name = key.split('|', 1)
        product_stock = stock_data.get(product_name)

        if product_stock is None:
            return False, f"Product not found in stock: {product_name}"

        if variant_name == 'default':
            if not isinstance(product_stock, dict):
                return False, f"Stock variant required for {product_name}"
            current_stock = int(product_stock.get('stock', 0))
            if current_stock < quantity:
                return False, f"Not enough stock for {product_name}"
        else:
            if not isinstance(product_stock, list):
                return False, f"Invalid stock format for {product_name}"
            variant_obj = next((v for v in product_stock if v.get('name') == variant_name), None)
            if not variant_obj:
                return False, f"Variant not found: {product_name} {variant_name}"
            current_stock = int(variant_obj.get('stock', 0))
            if current_stock < quantity:
                return False, f"Not enough stock for {product_name} {variant_name}"

    # Apply decrements after all validations pass.
    for key, quantity in decrements.items():
        product_name, variant_name = key.split('|', 1)
        product_stock = stock_data[product_name]

        if variant_name == 'default':
            product_stock['stock'] = int(product_stock.get('stock', 0)) - quantity
        else:
            variant_obj = next((v for v in product_stock if v.get('name') == variant_name), None)
            variant_obj['stock'] = int(variant_obj.get('stock', 0)) - quantity

    save_stock_data(stock_data)
    return True, ""

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

        # Enforce discount rules on the server so disabled discounts cannot be
        # applied by stale clients.
        discount_settings = get_discount_settings()
        submitted_code = str(data.get('discountCode') or '').strip().upper()
        submitted_discount = data.get('discountAmount', 0)

        try:
            submitted_discount = float(submitted_discount)
        except (TypeError, ValueError):
            submitted_discount = 0

        is_public_discount = discount_settings['enabled'] and (submitted_code == discount_settings['code'])
        is_secret_discount = discount_settings['secret_enabled'] and submitted_code == SECRET_DISCOUNT_CODE

        if not is_public_discount and not is_secret_discount:
            submitted_discount = 0
            submitted_code = None

        allowed_percent = SECRET_DISCOUNT_PERCENT if is_secret_discount else discount_settings['percent']

        subtotal_value = float(data.get('subtotal', 0) or 0)
        postage_value = float(data.get('postage', 0) or 0)

        gift_items = [item for item in data.get('items', []) if item.get('option', '').endswith('Free bank holiday gift')]
        allowed_gifts = set()
        if discount_settings['enabled']:
            stock_state = load_stock_data()
            gift_tier = get_sale_gift_tier(subtotal_value, allowed_percent, stock_state)
            if gift_tier == 'MT2':
                allowed_gifts.add(('MT2', SALE_GIFT_NAMES['MT2']))
            elif gift_tier == 'GHK-CU':
                allowed_gifts.add(('GHK-CU', SALE_GIFT_NAMES['GHK-CU']))
        for gift in gift_items:
            gift_key = (gift.get('name'), gift.get('option'))
            if gift_key not in allowed_gifts or gift.get('price') != 0 or gift.get('quantity') != 1:
                return jsonify({'success': False, 'error': 'Bank holiday gift eligibility could not be verified'}), 400

        max_allowed_discount = subtotal_value * (allowed_percent / 100)

        if submitted_discount < 0:
            submitted_discount = 0
        if submitted_discount > max_allowed_discount:
            submitted_discount = max_allowed_discount

        data['discountAmount'] = round(submitted_discount, 2)
        data['discountCode'] = submitted_code
        data['total'] = round(subtotal_value - data['discountAmount'] + postage_value, 2)
        
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

        # Decrement stock for this purchase before persisting the order.
        stock_ok, stock_error = decrement_stock_for_order_items(data.get('items', []))
        if not stock_ok:
            return jsonify({'success': False, 'error': stock_error}), 400
        
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
            'paypalFee': round(float(data.get('paypalFee', 0) or 0), 2),
            'paypalTotal': round(float(data.get('paypalTotal', data.get('total', data['subtotal'])) or 0), 2),
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
                        <p><strong>PayPal fee (2.9%):</strong> £{data.get('paypalFee', 0):.2f}</p>
                        <div class="total" style="border-top: 2px solid #0052cc; padding-top: 10px;">
                            Total: £{data.get('total', data.get('subtotal', 0)):.2f}
                        </div>
                        <p style="margin-top: 10px;"><strong>Amount to send with PayPal G&amp;S:</strong> £{data.get('paypalTotal', data.get('total', data.get('subtotal', 0))):.2f}</p>
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
                        <p><strong>PayPal fee (2.9%):</strong> £{data.get('paypalFee', 0):.2f}</p>
                        <div class="total">Total: £{data.get('total', data.get('subtotal', 0)):.2f}</div>
                        <p style="margin-top: 10px;"><strong>Amount to send with PayPal G&amp;S:</strong> £{data.get('paypalTotal', data.get('total', data.get('subtotal', 0))):.2f}</p>
                    </div>
                    <div class="payment-section">
                        <h3>Payment Information</h3>
                        <p><strong>PayPal:</strong> ellaclegg232@gmail.com</p>
                        <p><strong>Bank Transfer:</strong> E Clegg<br>Sort code: 20-30-02<br>Account number: 90677582</p>
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

def _split_address_for_sendcloud(address_line):
    """Best-effort split of UK address line into street and house number."""
    raw = str(address_line or "").strip()
    if not raw:
        return "Unknown Street", "1"

    parts = raw.split()
    if parts and any(ch.isdigit() for ch in parts[0]):
        house_number = parts[0]
        street = " ".join(parts[1:]) or raw
        return street[:120], house_number[:24]

    if parts and any(ch.isdigit() for ch in parts[-1]):
        house_number = parts[-1]
        street = " ".join(parts[:-1]) or raw
        return street[:120], house_number[:24]

    return raw[:120], "1"

def _extract_sendcloud_label_url(parcel):
    """Read Sendcloud parcel payload and extract a downloadable label URL."""
    if not isinstance(parcel, dict):
        return ""

    direct_keys = [
        'label_url',
        'label_download',
        'label_printer',
        'label',
        'label_zpl_url'
    ]
    for key in direct_keys:
        value = parcel.get(key)
        if isinstance(value, str) and value.startswith('http'):
            return value

    label_obj = parcel.get('label')
    if isinstance(label_obj, dict):
        nested_keys = ['normal', 'printer', 'label_printer', 'label']
        for key in nested_keys:
            value = label_obj.get(key)
            if isinstance(value, str) and value.startswith('http'):
                return value

    return ""

def _download_sendcloud_label_pdf(label_url):
    """Download label bytes from Sendcloud label URL."""
    if not label_url:
        return False, "Missing Sendcloud label URL", b""

    try:
        response = requests.get(
            label_url,
            auth=(SENDCLOUD_PUBLIC_KEY, SENDCLOUD_SECRET_KEY),
            timeout=20
        )
        if response.status_code != 200:
            return False, f"Sendcloud label download failed: {response.status_code}", b""

        content = response.content or b""
        if not content:
            return False, "Sendcloud label download returned empty content", b""

        return True, "", content
    except Exception as e:
        return False, f"Sendcloud label download exception: {str(e)}", b""

def resolve_sendcloud_shipping_method_id():
    """Resolve shipping method ID from env or Sendcloud shipping method lookup."""
    if SENDCLOUD_SHIPPING_METHOD_ID:
        try:
            return True, int(SENDCLOUD_SHIPPING_METHOD_ID), ""
        except (TypeError, ValueError):
            return False, None, "SENDCLOUD_SHIPPING_METHOD_ID must be a number"

    try:
        response = requests.get(
            f"{SENDCLOUD_BASE_URL}/shipping_methods",
            auth=(SENDCLOUD_PUBLIC_KEY, SENDCLOUD_SECRET_KEY),
            timeout=20
        )
        if response.status_code != 200:
            return False, None, f"Sendcloud shipping methods lookup failed: {response.status_code}"

        payload = response.json() if response.content else {}
        methods = payload.get('shipping_methods', [])
        if not isinstance(methods, list) or not methods:
            return False, None, "No Sendcloud shipping methods returned"

        method_hint = SENDCLOUD_METHOD_HINT.strip().lower()

        # Prefer explicit Royal Mail + Tracked 24 style matches.
        best_match = None
        for method in methods:
            name = str(method.get('name') or '').lower()
            carrier = str(method.get('carrier') or method.get('carrier_name') or '').lower()
            if ('tracked' in name and '24' in name) and ('royal' in carrier or 'mail' in carrier or 'royal' in name):
                best_match = method
                break

        if not best_match and method_hint:
            for method in methods:
                name = str(method.get('name') or '').lower()
                if method_hint in name:
                    best_match = method
                    break

        if not best_match:
            return False, None, "Could not auto-match a Sendcloud Tracked 24 shipping method"

        try:
            return True, int(best_match.get('id')), ""
        except (TypeError, ValueError):
            return False, None, "Matched Sendcloud method has invalid id"
    except Exception as e:
        return False, None, f"Sendcloud shipping method lookup exception: {str(e)}"

def create_sendcloud_tracked24_label(order):
    """Create a Sendcloud parcel and request a carrier label."""
    if not SENDCLOUD_ENABLED:
        return False, "SENDCLOUD_ENABLED is disabled", {}

    if not SENDCLOUD_PUBLIC_KEY or not SENDCLOUD_SECRET_KEY:
        return False, "Sendcloud API keys are missing", {}

    resolved, shipping_method_id, method_error = resolve_sendcloud_shipping_method_id()
    if not resolved:
        return False, method_error, {}

    street, house_number = _split_address_for_sendcloud(order.get('deliveryAddress', ''))

    parcel_payload = {
        'name': str(order.get('customerName') or 'Customer')[:120],
        'address': street,
        'house_number': house_number,
        'city': str(order.get('city') or '')[:120],
        'postal_code': str(order.get('postcode') or '')[:32],
        'country': SENDCLOUD_DEFAULT_COUNTRY,
        'telephone': str(order.get('customerPhone') or '')[:32],
        'email': str(order.get('customerEmail') or '')[:255],
        'order_number': str(order.get('orderNumber') or ''),
        'request_label': True,
        'shipment': {
            'id': shipping_method_id
        },
        'weight': '0.5',
        'apply_shipping_rules': False
    }

    try:
        response = requests.post(
            f"{SENDCLOUD_BASE_URL}/parcels",
            auth=(SENDCLOUD_PUBLIC_KEY, SENDCLOUD_SECRET_KEY),
            json={'parcel': parcel_payload},
            timeout=20
        )
        if response.status_code not in (200, 201):
            return False, f"Sendcloud parcel creation failed: {response.status_code} - {response.text}", {}

        payload = response.json() if response.content else {}
        parcel = payload.get('parcel', payload)
        label_url = _extract_sendcloud_label_url(parcel)
        if not label_url:
            return False, "Sendcloud parcel created but no label URL returned", {
                'parcelId': parcel.get('id'),
                'trackingNumber': parcel.get('tracking_number') or ''
            }

        downloaded, download_error, pdf_bytes = _download_sendcloud_label_pdf(label_url)
        if not downloaded:
            return False, download_error, {
                'parcelId': parcel.get('id'),
                'trackingNumber': parcel.get('tracking_number') or '',
                'labelUrl': label_url
            }

        return True, "", {
            'parcelId': parcel.get('id'),
            'trackingNumber': parcel.get('tracking_number') or '',
            'trackingUrl': parcel.get('tracking_url') or '',
            'labelUrl': label_url,
            'labelPdfBytes': pdf_bytes
        }
    except Exception as e:
        return False, f"Sendcloud request failed: {str(e)}", {}

def build_shipping_label_text(order):
    """Build a printable shipping label body for an order."""
    order_number = order.get('orderNumber', 'UNKNOWN')
    customer_name = order.get('customerName', '').strip()
    address = order.get('deliveryAddress', '').strip()
    city = order.get('city', '').strip()
    postcode = order.get('postcode', '').strip()
    phone = order.get('customerPhone', '').strip()

    items_lines = []
    for item in order.get('items', []):
        item_name = str(item.get('name', 'Item')).strip()
        item_option = str(item.get('option') or '').strip()
        quantity = int(item.get('quantity', 1) or 1)
        option_suffix = f" ({item_option})" if item_option else ""
        items_lines.append(f"- {quantity} x {item_name}{option_suffix}")

    if not items_lines:
        items_lines.append("- No items listed")

    qr_reference = str(order.get('royalMailQrCode') or '').strip()
    qr_block = ""
    if order.get('useRoyalMailQr') and qr_reference:
        qr_block = f"\nROYAL MAIL QR REF: {qr_reference}"

    return (
        "LEANr SHIPPING LABEL\n"
        "====================\n"
        f"ORDER: {order_number}\n"
        f"PAID: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\n"
        "SHIP TO:\n"
        f"{customer_name}\n"
        f"{address}\n"
        f"{city}\n"
        f"{postcode}\n"
        f"TEL: {phone}\n"
        f"{qr_block}\n"
        "\n"
        "ITEMS:\n"
        f"{'\n'.join(items_lines)}\n"
    )

def send_shipping_label_to_printnode(order, label_text):
    """Send a raw text fallback label to PrintNode. Returns (ok, error_message)."""
    if not AUTO_PRINT_LABELS:
        return False, "AUTO_PRINT_LABELS is disabled"

    if not PRINTNODE_API_KEY or not PRINTNODE_PRINTER_ID:
        return False, "PrintNode credentials are missing"

    try:
        printer_id = int(PRINTNODE_PRINTER_ID)
    except (TypeError, ValueError):
        return False, "PRINTNODE_PRINTER_ID must be a number"

    try:
        payload = {
            "printerId": printer_id,
            "title": f"LEANr Shipping Label - {order.get('orderNumber', 'UNKNOWN')}",
            "contentType": "raw_base64",
            "content": base64.b64encode(label_text.encode('utf-8')).decode('ascii'),
            "source": "LEANr Auto Label"
        }
        response = requests.post(
            "https://api.printnode.com/printjobs",
            auth=(PRINTNODE_API_KEY, ""),
            json=payload,
            timeout=15
        )
        if response.status_code in (200, 201):
            return True, ""

        return False, f"PrintNode error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"PrintNode request failed: {str(e)}"

def send_pdf_label_to_printnode(order, pdf_bytes, label_title):
    """Send PDF label to PrintNode. Returns (ok, error_message)."""
    if not AUTO_PRINT_LABELS:
        return False, "AUTO_PRINT_LABELS is disabled"

    if not PRINTNODE_API_KEY or not PRINTNODE_PRINTER_ID:
        return False, "PrintNode credentials are missing"

    try:
        printer_id = int(PRINTNODE_PRINTER_ID)
    except (TypeError, ValueError):
        return False, "PRINTNODE_PRINTER_ID must be a number"

    try:
        payload = {
            "printerId": printer_id,
            "title": f"{label_title} - {order.get('orderNumber', 'UNKNOWN')}",
            "contentType": "pdf_base64",
            "content": base64.b64encode(pdf_bytes).decode('ascii'),
            "source": "LEANr Sendcloud Label"
        }
        response = requests.post(
            "https://api.printnode.com/printjobs",
            auth=(PRINTNODE_API_KEY, ""),
            json=payload,
            timeout=20
        )
        if response.status_code in (200, 201):
            return True, ""

        return False, f"PrintNode error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"PrintNode PDF request failed: {str(e)}"

def send_shipping_label_fallback_email(order, label_text, reason):
    """Fallback path if auto-print is enabled but the print job fails."""
    order_number = order.get('orderNumber', 'UNKNOWN')
    html_body = f"""
    <html>
      <body style=\"font-family: Arial, sans-serif; color: #1f2937;\">
        <h2>Shipping Label Fallback - {order_number}</h2>
        <p>Automatic printing failed after payment confirmation.</p>
        <p><strong>Reason:</strong> {escape(reason)}</p>
        <p>Please print the attached label manually.</p>
        <pre style=\"background:#f8fafc;padding:12px;border:1px solid #e2e8f0;border-radius:6px;\">{escape(label_text)}</pre>
      </body>
    </html>
    """
    attachment = {
        "filename": f"shipping-label-{order_number}.txt",
        "content": base64.b64encode(label_text.encode('utf-8')).decode('ascii'),
        "content_type": "text/plain"
    }
    return send_email(
        BUSINESS_EMAIL,
        f"Shipping Label Fallback - {order_number}",
        html_body,
        order_number,
        attachments=[attachment]
    )

def send_sendcloud_label_fallback_email(order, reason, label_url="", label_pdf_bytes=None):
    """Email fallback details if Sendcloud label generation or print fails."""
    order_number = order.get('orderNumber', 'UNKNOWN')
    label_link = f"<p><strong>Label URL:</strong> <a href=\"{escape(label_url)}\">{escape(label_url)}</a></p>" if label_url else ""
    html_body = f"""
    <html>
      <body style=\"font-family: Arial, sans-serif; color: #1f2937;\">
        <h2>Sendcloud Label Fallback - {order_number}</h2>
        <p>Automatic Sendcloud label printing failed after payment confirmation.</p>
        <p><strong>Reason:</strong> {escape(reason)}</p>
        {label_link}
        <p>Please print the attached label manually if present.</p>
      </body>
    </html>
    """

    attachments = []
    if label_pdf_bytes:
        attachments.append({
            "filename": f"sendcloud-label-{order_number}.pdf",
            "content": base64.b64encode(label_pdf_bytes).decode('ascii'),
            "content_type": "application/pdf"
        })

    return send_email(
        BUSINESS_EMAIL,
        f"Sendcloud Label Fallback - {order_number}",
        html_body,
        order_number,
        attachments=attachments
    )

def process_shipping_label_after_payment(order, force_reprint=False):
    """Generate and print shipping label after payment confirmation."""
    if order.get('shippingLabelPrintedAt') and not force_reprint:
        return True, "Shipping label already printed"

    if SENDCLOUD_ENABLED and not AUTO_PRINT_LABELS:
        order['shippingLabelStatus'] = 'skipped'
        order['shippingLabelError'] = 'AUTO_PRINT_LABELS is disabled'
        order['shippingLabelLastAttemptAt'] = datetime.now().isoformat()
        return False, 'AUTO_PRINT_LABELS is disabled'

    if SENDCLOUD_ENABLED and AUTO_PRINT_LABELS:
        created, carrier_message, carrier_data = create_sendcloud_tracked24_label(order)

        if created:
            order['shippingCarrier'] = 'sendcloud'
            order['sendcloudParcelId'] = carrier_data.get('parcelId')
            order['shippingLabelUrl'] = carrier_data.get('labelUrl', '')
            order['shippingTrackingNumber'] = carrier_data.get('trackingNumber', '')
            order['shippingTrackingUrl'] = carrier_data.get('trackingUrl', '')

            label_pdf_bytes = carrier_data.get('labelPdfBytes', b"")
            printed, print_error = send_pdf_label_to_printnode(order, label_pdf_bytes, 'Royal Mail Tracked 24')
            if printed:
                order['shippingLabelStatus'] = 'printed'
                order['shippingLabelPrintedAt'] = datetime.now().isoformat()
                order['shippingLabelError'] = ''
                return True, "Sendcloud Tracked 24 label auto-printed"

            order['shippingLabelStatus'] = 'print_failed'
            order['shippingLabelError'] = print_error
            order['shippingLabelLastAttemptAt'] = datetime.now().isoformat()
            if AUTO_PRINT_LABELS:
                send_sendcloud_label_fallback_email(
                    order,
                    print_error,
                    label_url=carrier_data.get('labelUrl', ''),
                    label_pdf_bytes=label_pdf_bytes
                )
            return False, print_error

        order['shippingLabelStatus'] = 'carrier_failed'
        order['shippingLabelError'] = carrier_message
        order['shippingLabelLastAttemptAt'] = datetime.now().isoformat()
        if AUTO_PRINT_LABELS:
            send_sendcloud_label_fallback_email(order, carrier_message, label_url=carrier_data.get('labelUrl', ''))
        return False, carrier_message

    label_text = build_shipping_label_text(order)
    printed, print_error = send_shipping_label_to_printnode(order, label_text)

    if printed:
        order['shippingLabelStatus'] = 'printed'
        order['shippingLabelPrintedAt'] = datetime.now().isoformat()
        order['shippingLabelError'] = ''
        return True, "Shipping label auto-printed"

    order['shippingLabelStatus'] = 'print_failed'
    order['shippingLabelError'] = print_error
    order['shippingLabelLastAttemptAt'] = datetime.now().isoformat()

    if AUTO_PRINT_LABELS:
        send_shipping_label_fallback_email(order, label_text, print_error)

    return False, print_error

def reprint_shipping_label_for_order(order):
    """Reprint an order label, preferring existing carrier label URL when available."""
    if not order.get('paymentConfirmed'):
        return False, "Payment must be confirmed before printing a label"

    if not AUTO_PRINT_LABELS:
        return False, "AUTO_PRINT_LABELS is disabled"

    existing_label_url = str(order.get('shippingLabelUrl') or '').strip()
    if existing_label_url:
        downloaded, download_error, pdf_bytes = _download_sendcloud_label_pdf(existing_label_url)
        if downloaded:
            printed, print_error = send_pdf_label_to_printnode(order, pdf_bytes, 'Royal Mail Tracked 24 Reprint')
            if printed:
                order['shippingLabelStatus'] = 'reprinted'
                order['shippingLabelReprintedAt'] = datetime.now().isoformat()
                order['shippingLabelError'] = ''
                return True, "Existing Sendcloud label reprinted"
            order['shippingLabelStatus'] = 'print_failed'
            order['shippingLabelError'] = print_error
            order['shippingLabelLastAttemptAt'] = datetime.now().isoformat()
            return False, print_error

    # No reusable URL available; regenerate through the standard pipeline.
    return process_shipping_label_after_payment(order, force_reprint=True)

def verify_printnode_printer():
    """Check that configured PrintNode printer exists and is reachable."""
    if not PRINTNODE_API_KEY or not PRINTNODE_PRINTER_ID:
        return False, "PrintNode credentials are missing"

    try:
        printer_id = int(PRINTNODE_PRINTER_ID)
    except (TypeError, ValueError):
        return False, "PRINTNODE_PRINTER_ID must be a number"

    try:
        response = requests.get(
            "https://api.printnode.com/printers",
            auth=(PRINTNODE_API_KEY, ""),
            timeout=15
        )
        if response.status_code != 200:
            return False, f"PrintNode printer lookup failed: {response.status_code}"

        printers = response.json() if response.content else []
        if not isinstance(printers, list):
            return False, "PrintNode returned unexpected printer payload"

        found = any(int(p.get('id', -1)) == printer_id for p in printers if isinstance(p, dict))
        if not found:
            return False, f"Configured printer ID {printer_id} was not found in PrintNode account"

        return True, "PrintNode printer is reachable"
    except Exception as e:
        return False, f"PrintNode printer lookup exception: {str(e)}"

# ==================== ADMIN ENDPOINTS ====================

def verify_token(token):
    """Verify admin token"""
    return token in ADMIN_TOKENS

@app.route('/api/admin/test-shipping-label', methods=['POST', 'OPTIONS'])
def test_shipping_label_setup():
    """Run a dry-run diagnostics test for Sendcloud + PrintNode setup."""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        data = request.json or {}
        print_test = bool(data.get('printTest', True))

        checks = []

        def add_check(name, ok, detail):
            checks.append({'check': name, 'ok': bool(ok), 'detail': str(detail)})

        add_check('AUTO_PRINT_LABELS', AUTO_PRINT_LABELS, 'AUTO_PRINT_LABELS must be true for automatic label printing')
        add_check('SENDCLOUD_ENABLED', SENDCLOUD_ENABLED, 'SENDCLOUD_ENABLED must be true for carrier labels')

        has_sendcloud_keys = bool(SENDCLOUD_PUBLIC_KEY and SENDCLOUD_SECRET_KEY)
        add_check('Sendcloud API keys', has_sendcloud_keys, 'Set SENDCLOUD_PUBLIC_KEY and SENDCLOUD_SECRET_KEY')

        has_printnode_keys = bool(PRINTNODE_API_KEY and PRINTNODE_PRINTER_ID)
        add_check('PrintNode config', has_printnode_keys, 'Set PRINTNODE_API_KEY and PRINTNODE_PRINTER_ID')

        if SENDCLOUD_ENABLED and has_sendcloud_keys:
            resolved, method_id, method_error = resolve_sendcloud_shipping_method_id()
            if resolved:
                add_check('Sendcloud Tracked method', True, f"Resolved shipping method ID: {method_id}")
            else:
                add_check('Sendcloud Tracked method', False, method_error)

        if has_printnode_keys:
            printer_ok, printer_msg = verify_printnode_printer()
            add_check('PrintNode printer', printer_ok, printer_msg)

        if print_test and AUTO_PRINT_LABELS and has_printnode_keys:
            test_order = {
                'orderNumber': f"TEST-{int(time.time())}",
                'customerName': 'Label Test',
                'deliveryAddress': '123 Test Street',
                'city': 'London',
                'postcode': 'SW1A 1AA',
                'customerPhone': '00000000000',
                'items': [{'name': 'Test Item', 'option': 'Diagnostics', 'quantity': 1}]
            }
            test_label_text = build_shipping_label_text(test_order) + "\nDIAGNOSTIC TEST PRINT ONLY\n"
            printed, print_error = send_shipping_label_to_printnode(test_order, test_label_text)
            add_check('PrintNode test print', printed, 'Test page sent to printer' if printed else print_error)

        success = all(check.get('ok') for check in checks)
        return jsonify({
            'success': success,
            'checks': checks,
            'printTest': print_test,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reprint-label', methods=['POST', 'OPTIONS'])
def admin_reprint_label():
    """Reprint shipping label for a paid order."""
    if request.method == 'OPTIONS':
        return '', 200

    try:
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

        orders = load_orders_data()
        order = next((o for o in orders if o.get('orderNumber') == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        printed, message = reprint_shipping_label_for_order(order)
        save_orders_data(orders)

        if not printed:
            return jsonify({
                'success': False,
                'labelPrinted': False,
                'message': message
            }), 400

        return jsonify({
            'success': True,
            'labelPrinted': True,
            'message': message
        }), 200
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/admin/payment-reminder', methods=['POST', 'OPTIONS'])
def send_payment_reminder():
    """Send a payment reminder without changing the order payment status."""
    if request.method == 'OPTIONS':
        return '', 200

    try:
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

        orders = load_orders_data()
        order = next((o for o in orders if o.get('orderNumber') == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        customer_email = order.get('customerEmail') or order.get('email')
        if not customer_email:
            return jsonify({'error': 'Customer email not found for this order'}), 400

        item_rows = ''.join(
            f"<tr><td style='padding: 8px; border-bottom: 1px solid #e2e8f0;'>{item.get('name', 'Item')} ({item.get('option', 'N/A')})</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: center;'>{item.get('quantity', 0)}</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: right;'>£{float(item.get('price', 0)) * int(item.get('quantity', 0)):.2f}</td></tr>"
            for item in order.get('items', [])
        )
        discount_amount = float(order.get('discountAmount', 0) or 0)
        subtotal = float(order.get('subtotal', 0) or 0)
        postage = float(order.get('postage', 0) or 0)
        total = float(order.get('total', subtotal) or subtotal)
        discount_row = (
            f"<p style='color: #10b981;'><strong>Discount:</strong> -£{discount_amount:.2f}</p>"
            if discount_amount > 0 else ''
        )

        payment_reminder_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background: linear-gradient(135deg, #0052cc, #ec4899); color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .payment-section {{ background: #fffbeb; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ec4899; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th {{ background: #f1f5f9; padding: 8px; text-align: left; }}
                </style>
            </head>
            <body>
                <div class="header"><h1>Payment Reminder</h1></div>
                <div class="content">
                    <p>Hi {order.get('customerName', 'there')},</p>
                    <p>This is a friendly reminder that payment is still outstanding for your LEANr order.</p>
                    <h2>Order Number: {order_number}</h2>
                    <table>
                        <tr><th>Product</th><th>Qty</th><th>Total</th></tr>
                        {item_rows}
                    </table>
                    <div style="text-align: right; margin: 20px 0;">
                        <p><strong>Subtotal:</strong> £{subtotal:.2f}</p>
                        {discount_row}
                        <p><strong>Postage:</strong> £{postage:.2f}</p>
                        <p style="font-size: 1.2em;"><strong>Amount due: £{total:.2f}</strong></p>
                    </div>
                    <div class="payment-section">
                        <h3>Payment Details</h3>
                        <p><strong>PayPal:</strong> ellaclegg232@gmail.com</p>
                        <p><strong>Bank Transfer:</strong> E Clegg<br>Sort code: 20-30-02<br>Account number: 90677582</p>
                    </div>
                    <p>Please reply to this email if you have already paid or need any help.</p>
                    <p>Thank you,<br>The LEANr Team</p>
                </div>
            </body>
        </html>
        """

        sent, send_error = send_email(
            customer_email,
            f"Payment Reminder - Order {order_number}",
            payment_reminder_body,
            order_number
        )
        if not sent:
            return jsonify({
                'error': 'Payment reminder could not be delivered immediately',
                'details': send_error
            }), 502

        print(f"✓ Payment reminder sent for order {order_number}")
        return jsonify({'success': True, 'message': 'Payment reminder sent to customer'}), 200
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

        label_printed, label_message = process_shipping_label_after_payment(order)
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
        return jsonify({
            'success': True,
            'message': 'Payment confirmed and email sent to customer',
            'labelPrinted': label_printed,
            'labelMessage': label_message
        }), 200
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

        # Virtual bundle stock is derived from component availability.
        stock_list.append({
            'name': BUNDLE_PRODUCT_NAME,
            'stock': _calculate_bundle_stock(stock_data),
            'isVirtual': True
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

        if product_name == BUNDLE_PRODUCT_NAME:
            return jsonify({'error': 'Bundle stock is calculated automatically'}), 400
        
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

        # Virtual bundle stock is derived from component availability.
        stock_list.append({
            'name': BUNDLE_PRODUCT_NAME,
            'stock': _calculate_bundle_stock(stock_data)
        })
        
        return jsonify({'stock': stock_list}), 200
    except Exception as e:
        print(f"ERROR fetching stock: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/public/discount-settings', methods=['GET'])
def get_public_discount_settings():
    """Public discount settings used by checkout and site popup."""
    try:
        settings = get_discount_settings()
        public_settings = {key: settings[key] for key in ('enabled', 'code', 'percent', 'starts_at', 'ends_at')}
        return jsonify({'discount': public_settings}), 200
    except Exception as e:
        print(f"ERROR fetching discount settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/public/product-visibility', methods=['GET'])
def get_public_product_visibility():
    try:
        return jsonify({'visibility': get_product_visibility()}), 200
    except Exception as e:
        print(f"ERROR fetching product visibility: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/discount-settings', methods=['GET', 'POST', 'OPTIONS'])
def admin_discount_settings():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        if request.method == 'GET':
            return jsonify({'discount': get_discount_settings()}), 200

        data = request.json or {}
        if 'enabled' not in data and 'secret_enabled' not in data:
            return jsonify({'error': 'Missing discount setting'}), 400

        settings = get_discount_settings()
        if 'enabled' in data:
            settings['enabled'] = bool(data.get('enabled'))
        if 'secret_enabled' in data:
            settings['secret_enabled'] = bool(data.get('secret_enabled'))
        save_discount_settings_data(settings)
        return jsonify({'success': True, 'discount': settings}), 200
    except Exception as e:
        print(f"ERROR updating discount settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/product-visibility', methods=['GET', 'POST', 'OPTIONS'])
def admin_product_visibility():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        if request.method == 'GET':
            return jsonify({'visibility': get_product_visibility()}), 200

        data = request.json or {}
        visibility = data.get('visibility')
        if not isinstance(visibility, dict):
            return jsonify({'error': 'Visibility must be an object'}), 400

        settings = set_product_visibility(visibility)
        return jsonify({'success': True, 'visibility': settings}), 200
    except Exception as e:
        print(f"ERROR updating product visibility: {str(e)}")
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

@app.route('/api/suggestions', methods=['POST', 'OPTIONS'])
def submit_product_suggestion():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(silent=True) or {}
        suggestion_text = str(data.get('suggestion', '')).strip()

        if len(suggestion_text) < 2:
            return jsonify({'error': 'Please enter a product suggestion'}), 400
        if len(suggestion_text) > 1000:
            return jsonify({'error': 'Suggestion must be 1000 characters or fewer'}), 400

        suggestions = load_product_suggestions_data()
        suggestions.append({
            'id': secrets.token_urlsafe(8),
            'suggestion': suggestion_text,
            'timestamp': datetime.now().isoformat()
        })
        save_product_suggestions_data(suggestions)

        return jsonify({'success': True, 'message': 'Thanks, your suggestion has been sent'}), 201
    except Exception as e:
        print(f"ERROR saving product suggestion: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/suggestions', methods=['GET'])
def get_product_suggestions():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        suggestions = load_product_suggestions_data()
        return jsonify({'suggestions': list(reversed(suggestions))}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/delete-suggestion', methods=['POST', 'OPTIONS'])
def delete_product_suggestion():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401

        token = auth_header.replace('Bearer ', '')
        if not verify_token(token):
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json(silent=True) or {}
        suggestion_id = data.get('id')
        if not suggestion_id:
            return jsonify({'error': 'Suggestion id is required'}), 400

        suggestions = load_product_suggestions_data()
        filtered = [item for item in suggestions if item.get('id') != suggestion_id]
        if len(filtered) == len(suggestions):
            return jsonify({'error': 'Suggestion not found'}), 404

        save_product_suggestions_data(filtered)
        return jsonify({'success': True}), 200
    except Exception as e:
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
    with open('index.html', encoding='utf-8') as f:
        return f.read()

@app.route('/index.html')
def serve_index_explicit():
    """Serve index.html (explicit route)"""
    with open('index.html', encoding='utf-8') as f:
        return f.read()

@app.route('/cart.html')
def serve_cart():
    """Serve cart.html"""
    with open('cart.html', encoding='utf-8') as f:
        return f.read()

@app.route('/order-confirmation.html')
def serve_order_confirmation():
    """Serve the post-checkout order confirmation page."""
    with open('order-confirmation.html', encoding='utf-8') as f:
        return f.read()

@app.route('/admin.html')
def serve_admin():
    """Serve admin.html"""
    with open('admin.html', encoding='utf-8') as f:
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
    with open('styles.css', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/css'}

@app.route('/script.js')
def serve_script():
    """Serve script.js"""
    with open('script.js', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}

@app.route('/cart-script.js')
def serve_cart_script():
    """Serve cart-script.js"""
    with open('cart-script.js', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}

@app.route('/<path:filename>')
def serve_image_asset(filename):
    """Serve only image assets from the project root."""
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico'}
    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host=host, port=port)
