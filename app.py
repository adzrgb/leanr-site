from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import json
import os
import secrets
import hashlib
import time
import random
from dotenv import load_dotenv
import threading

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
# Resend sender email - use verified gmail account (domains require DNS verification)
# leanrwellness@gmail.com is verified as account owner email
RESEND_FROM_EMAIL = "leanrwellness@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

print(f"DEBUG: EMAIL CONFIG - Business email (for notifications): {BUSINESS_EMAIL}")
print(f"DEBUG: Resend sender email (from domain): {RESEND_FROM_EMAIL}")
print(f"DEBUG: Resend API Key present: {'Yes' if RESEND_API_KEY else 'No - will use API key from environment'}")

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("Qx7m#K2$pL9@vN4b".encode()).hexdigest()
ADMIN_TOKENS = {}  # Store active tokens

# File paths for data storage
ORDERS_FILE = "orders.json"
STOCK_FILE = "stock.json"
EMAILS_FILE = "newsletter_emails.json"

# Initialize stock file if it doesn't exist
if not os.path.exists(STOCK_FILE):
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
    with open(STOCK_FILE, 'w') as f:
        json.dump(default_stock, f)

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
        
        # Save order to JSON file FIRST
        orders = []
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        
        order_record = {
            'orderNumber': data['orderNumber'],
            'customerName': data['customerName'],
            'customerEmail': data['customerEmail'],
            'customerPhone': data['customerPhone'],
            'deliveryAddress': data['deliveryAddress'],
            'city': data['city'],
            'postcode': data['postcode'],
            'orderNotes': data.get('orderNotes', ''),
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
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        
        print(f"✓ Order saved to database")
        
        # Return success immediately - don't wait for emails
        result = jsonify({'success': True, 'orderNumber': data['orderNumber']})
        
        # Send emails in background thread (non-blocking)
        def send_emails_background():
            try:
                send_order_emails(data, items_html)
            except Exception as e:
                print(f"✗ Background email error: {str(e)}")
        
        email_thread = threading.Thread(target=send_emails_background, daemon=True)
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
        print(f"\n{'='*60}")
        print(f"STARTING EMAIL SEND FOR ORDER: {data['orderNumber']}")
        print(f"Customer: {data['customerEmail']}")
        print(f"Business email: {BUSINESS_EMAIL}")
        print(f"{'='*60}\n")
        
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
                        <p><strong>Option 2: Bank Transfer</strong><br>Sort: 23-01-20 | Account: 13050648<br>Reference: {data['orderNumber'][-4:]}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Send business email
        print(f"[1/2] Attempting to send BUSINESS email...")
        try:
            send_email(BUSINESS_EMAIL, f"New Order: {data['orderNumber']}", business_email_body)
            print(f"✓ Business email sent successfully")
        except Exception as e:
            print(f"✗ Business email FAILED: {str(e)}")
            raise
        
        # Send customer email
        print(f"[2/2] Attempting to send CUSTOMER email...")
        try:
            send_email(data['customerEmail'], f"Order Confirmation: {data['orderNumber']}", customer_email_body)
            print(f"✓ Customer email sent successfully")
        except Exception as e:
            print(f"✗ Customer email FAILED: {str(e)}")
            raise
        
        print(f"✓ ALL EMAILS SENT SUCCESSFULLY for order {data['orderNumber']}\n")
    except Exception as e:
        print(f"✗ Email sending failed: {str(e)}")
        import traceback
        print(traceback.format_exc())

def send_email(recipient, subject, html_body):
    """Send email via Resend API using requests library"""
    try:
        print(f"\n  → Sending email to {recipient}...")
        print(f"    Subject: {subject}")
        
        if not RESEND_API_KEY:
            print(f"    ⚠ WARNING: RESEND_API_KEY not configured yet")
            print(f"    → Email QUEUED but not sent (API key missing)")
            print(f"    → To: {recipient}")
            print(f"    → Add RESEND_API_KEY to Render environment variables to enable email delivery")
            return  # Gracefully continue without sending
        
        print(f"    Sending via Resend API...")
        print(f"    From: {RESEND_FROM_EMAIL}")
        print(f"    To: {recipient}")
        
        # Make direct HTTP call to Resend API
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": recipient,
                "subject": subject,
                "html": html_body,
                "reply_to": BUSINESS_EMAIL,  # Reply-To so customers reply to business email
            },
            timeout=10
        )
        
        print(f"    Resend API Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            print(f"    ✓ Email sent successfully to {recipient}")
            print(f"    Response ID: {response_data.get('id', 'N/A')}\n")
        else:
            print(f"    ✗ Email API Error Status {response.status_code}")
            print(f"    Full Response: {response.text}\n")
            try:
                error_data = response.json()
                print(f"    Error details: {error_data}\n")
            except:
                pass
            raise Exception(f"Resend API Error {response.status_code}: {response.text}")
        
    except Exception as e:
        import traceback
        print(f"    ✗ FAILED to send email to {recipient}")
        print(f"    Error: {str(e)}")
        print(f"    Traceback:")
        print(traceback.format_exc())
        raise

# ==================== ADMIN ENDPOINTS ====================

def verify_token(token):
    """Verify admin token"""
    return token in ADMIN_TOKENS

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
        
        orders = []
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        
        print(f"✓ Retrieved {len(orders)} orders")
        return jsonify({'orders': orders}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
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
        
        data = request.json
        order_number = data.get('orderNumber')
        tracking_number = data.get('trackingNumber')
        
        # Find order and update
        orders = []
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        
        order = next((o for o in orders if o['orderNumber'] == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Update tracking number
        order['trackingNumber'] = tracking_number
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        
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
        
        send_email(
            order['customerEmail'],
            f"Your Order {order_number} is on the Way! - Tracking: {tracking_number}",
            tracking_email_body
        )
        
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
        
        data = request.json
        order_number = data.get('orderNumber')
        
        # Find order and update
        orders = []
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        
        order = next((o for o in orders if o['orderNumber'] == order_number), None)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Mark payment as confirmed
        order['paymentConfirmed'] = True
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        
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
        
        send_email(
            order['customerEmail'],
            f"Payment Confirmed - Order {order_number}",
            payment_confirmation_body
        )
        
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
        
        with open(STOCK_FILE, 'r') as f:
            stock_data = json.load(f)
        
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
        
        data = request.json
        product_name = data.get('productName')
        variant = data.get('variant')
        new_stock = data.get('stock')
        
        with open(STOCK_FILE, 'r') as f:
            stock_data = json.load(f)
        
        if product_name not in stock_data:
            return jsonify({'error': 'Product not found'}), 404
        
        if variant == 'default':
            stock_data[product_name]['stock'] = new_stock
        else:
            # Find and update variant
            product = stock_data[product_name]
            if isinstance(product, list):
                for v in product:
                    if v['name'] == variant:
                        v['stock'] = new_stock
                        break
        
        with open(STOCK_FILE, 'w') as f:
            json.dump(stock_data, f, indent=2)
        
        print(f"✓ Updated stock: {product_name} {variant} = {new_stock}")
        return jsonify({'success': True, 'message': 'Stock updated'}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Public endpoint for stock data (no auth required)
@app.route('/api/public/stock', methods=['GET'])
def get_public_stock():
    try:
        with open(STOCK_FILE, 'r') as f:
            stock_data = json.load(f)
        
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
        emails = []
        if os.path.exists(EMAILS_FILE):
            with open(EMAILS_FILE, 'r') as f:
                emails = json.load(f)
        
        # Check if already subscribed
        if email in emails:
            return jsonify({'success': True, 'message': 'Already subscribed'}), 200
        
        # Add new email
        emails.append(email)
        with open(EMAILS_FILE, 'w') as f:
            json.dump(emails, f, indent=2)
        
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
        
        orders = []
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        
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
        return f.read()

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
