# Dropshipping E-Commerce Platform

A full-featured dropshipping e-commerce platform built with Django, designed to help entrepreneurs start and manage their dropshipping business efficiently.

## 🚀 Features

### For Customers

- **User Authentication**: Secure registration and login system
- **Product Browsing**: Browse products by categories, search functionality
- **Shopping Cart**: Add/remove items, update quantities
- **Wishlist**: Save favorite products for later
- **Order Tracking**: Real-time order status updates
- **Reviews & Ratings**: Leave feedback on purchased products

### For Admin/Store Owners

- **Product Management**: Add, edit, delete products with images
- **Inventory Management**: Track stock levels, low stock alerts
- **Supplier Integration**: Manage supplier information and product sourcing
- **Order Management**: View, update, and process orders
- **Customer Management**: View customer details and order history
- **Analytics Dashboard**: Sales reports, popular products, revenue analytics
- **Discount & Coupon System**: Create and manage promotional offers

### Technical Features

- Responsive design (mobile-friendly)
- Secure payment processing ready (Stripe/PayPal integration)
- Email notifications for orders and account activities
- SEO-friendly URLs
- Caching for improved performance
- REST API for mobile app integration (optional)

## 🛠️ Technology Stack

- **Backend**: Django 4.x, Python 3.9+
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Payment Gateway**: Stripe / PayPal integration ready
- **Image Processing**: Pillow
- **Task Queue**: Celery (for background tasks)
- **Caching**: Redis
- **Version Control**: Git

## 📋 Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- virtualenv (recommended)
- Git

## 🔧 Installation & Setup

1. **Clone the repository**

```bash
git clone https://github.com/eKidenge/dropshipping.git
cd dropshipping

python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```
