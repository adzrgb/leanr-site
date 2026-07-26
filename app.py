from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os
import secrets
import hashlib
from dotenv import load_dotenv

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
BUSINESS_EMAIL_PASSWORD = os.getenv("BUSINESS_EMAIL_PASSWORD", "ugxb naur dasv pkeg")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", hashlib.sha256("Qx7m#K2$pL9@vN4b".encode()).hexdigest())
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
        
        total = data['subtotal']
        
        # Create HTML email for business
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
                        <p>{data['deliveryAddress']}<br>
                           {data['city']}<br>
                           {data['postcode']}</p>
                    </div>
                    
                    <h3>Order Items</h3>
                    <table>
                        <th>Product</th>
                        <th>Option</th>
                        <th>Qty</th>
                        <th>Total</th>
                        {items_html}
                    </table>
                    
                    <div class="total">
                        Total: £{total:.2f}
                    </div>
                    
                    <p style="margin-top: 30px; color: #666;">
                        Customer will receive a separate confirmation email with payment details.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Create HTML email for customer
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
                <div class="header">
                    <h1>LEANr Order Confirmation</h1>
                </div>
                <div class="content">
                    <p>Hi {data['customerName']},</p>
                    <p>Thank you for your order! Here are your order details:</p>
                    
                    <h2>Order Number: {data['orderNumber']}</h2>
                    <p>Order Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    
                    <div class="order-details">
                        <h3>Delivery Address</h3>
                        <p>{data['deliveryAddress']}<br>
                           {data['city']}<br>
                           {data['postcode']}</p>
                    </div>
                    
                    <h3>Order Items</h3>
                    <table>
                        <th>Product</th>
                        <th>Option</th>
                        <th>Qty</th>
                        <th>Total</th>
                        {items_html}
                    </table>
                    
                    <div class="total">
                        Total: £{total:.2f}
                    </div>
                    
                    <div class="payment-section">
                        <h3>Payment Information</h3>
                        <p><strong>Payment Options:</strong></p>
                        
                        <p><strong>Option 1: PayPal</strong><br>
                        PayPal: <strong>leanrwellness@gmail.com</strong></p>
                        
                        <p style="margin-left: 20px; font-size: 14px;">
                            <strong>Friends and Family:</strong> No fees, fastest option. Use this if you're comfortable with no buyer protection.<br><br>
                            <strong>Goods and Services:</strong> Includes buyer protection. <u>If you choose this option, you MUST add the PayPal fee to your payment or your order will be refunded.</u> The fee is typically 3.49% + £0.20 for UK transactions.
                        </p>
                        
                        <p><strong>Option 2: Bank Transfer</strong><br>
                        Please use your order number <strong>{data['orderNumber']}</strong> as the reference when making payment.</p>
                        
                        <p style="color: #ec4899; font-weight: bold;">⚠️ If paying by PayPal Goods and Services, the fee must be included in your payment or your order will be automatically refunded.</p>
                        
                        <p>If you have any questions, please reply to this email.</p>
                    </div>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 12px;">
                        ELEVATE. TRANSFORM. BECOME LEANr.<br>
                        Thank you for your purchase!
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email to business
        send_email(
            BUSINESS_EMAIL,
            f"New Order: {data['orderNumber']}",
            business_email_body
        )
        
        # Send confirmation email to customer
        send_email(
            data['customerEmail'],
            f"Order Confirmation: {data['orderNumber']}",
            customer_email_body
        )
        
        # Save order to JSON file
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
            'postage': data.get('postage', 0),
            'total': data.get('total', data['subtotal']),
            'timestamp': data['timestamp'],
            'trackingNumber': None
        }
        
        orders.append(order_record)
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=2)
        
        print(f"✓ Order saved to database")
        
        return jsonify({'success': True, 'orderNumber': data['orderNumber']}), 200
    
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

def send_email(recipient, subject, html_body):
    try:
        print(f"Sending email to {recipient}...")
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"LEANr Wellness <{BUSINESS_EMAIL}>"
        msg['To'] = recipient
        msg['Reply-To'] = BUSINESS_EMAIL
        
        # Attach HTML
        part = MIMEText(html_body, 'html')
        msg.attach(part)
        
        # Send via SMTP
        print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            print("Starting TLS...")
            server.starttls()
            print(f"Logging in as {BUSINESS_EMAIL}...")
            server.login(BUSINESS_EMAIL, BUSINESS_EMAIL_PASSWORD)
            print(f"Sending mail...")
            server.sendmail(BUSINESS_EMAIL, recipient, msg.as_string())
        
        print(f"✓ Email sent successfully to {recipient}")
    except Exception as e:
        import traceback
        print(f"✗ Failed to send email to {recipient}: {str(e)}")
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host=host, port=port)
