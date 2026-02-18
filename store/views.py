from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum, F
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from .models import *
from .forms import *
import json
import uuid
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io

# Home page view
def home(request):
    featured_products = Product.objects.filter(status='active', is_featured=True)[:8]
    new_products = Product.objects.filter(status='active', is_new=True)[:8]
    bestsellers = Product.objects.filter(status='active', is_bestseller=True)[:8]
    categories = Category.objects.filter(is_active=True, parent=None)[:6]
    
    # Get statistics
    total_products = Product.objects.filter(status='active').count()
    happy_customers = Order.objects.filter(status='delivered').values('user').distinct().count()
    
    # Get recent reviews
    recent_reviews = Review.objects.filter(is_approved=True).order_by('-created_at')[:6]
    
    # Handle newsletter subscription
    if request.method == 'POST' and 'newsletter' in request.POST:
        email = request.POST.get('email')
        if email:
            subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, 'Successfully subscribed to newsletter!')
            else:
                messages.info(request, 'Email already subscribed.')
            return redirect('store:home')
    
    context = {
        'featured_products': featured_products,
        'new_products': new_products,
        'bestsellers': bestsellers,
        'categories': categories,
        'total_products': total_products,
        'happy_customers': happy_customers,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'store/home.html', context)

# Product listing view with filtering
def products(request):
    # Base queryset
    products_list = Product.objects.filter(status='active').select_related('category', 'supplier')
    
    # Get filter parameters
    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'newest')
    in_stock = request.GET.get('in_stock')
    supplier_id = request.GET.get('supplier')
    search_query = request.GET.get('q')
    
    # Apply filters
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # Get category and all subcategories
        category_ids = [category.id]
        category_ids.extend([c.id for c in category.children.all()])
        products_list = products_list.filter(category_id__in=category_ids)
    
    if min_price:
        products_list = products_list.filter(selling_price__gte=min_price)
    if max_price:
        products_list = products_list.filter(selling_price__lte=max_price)
    
    if in_stock == 'true':
        products_list = products_list.filter(stock_quantity__gt=0)
    
    if supplier_id:
        products_list = products_list.filter(supplier_id=supplier_id)
    
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(supplier__name__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'price_low':
        products_list = products_list.order_by('selling_price')
    elif sort_by == 'price_high':
        products_list = products_list.order_by('-selling_price')
    elif sort_by == 'name_asc':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    elif sort_by == 'bestsellers':
        products_list = products_list.order_by('-is_bestseller', '-created_at')
    elif sort_by == 'newest':
        products_list = products_list.order_by('-published_at', '-created_at')
    elif sort_by == 'rating':
        products_list = products_list.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # Get filter options
    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related('children')
    suppliers = Supplier.objects.filter(is_active=True)
    
    # Get price range
    price_range = products_list.aggregate(
        min_price=models.Min('selling_price'),
        max_price=models.Max('selling_price')
    )
    
    # Pagination
    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    context = {
        'products': products,
        'categories': categories,
        'suppliers': suppliers,
        'current_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'search_query': search_query,
        'price_range': price_range,
        'total_products': paginator.count,
    }
    return render(request, 'store/products.html', context)

# Product detail view
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, status='active')
    
    # Get related products (same category)
    related_products = Product.objects.filter(
        category=product.category, 
        status='active'
    ).exclude(id=product.id)[:4]
    
    # Get product reviews
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Check if user has purchased this product
    user_purchased = False
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        user_purchased = Order.objects.filter(
            user=request.user,
            items__product=product,
            status='delivered'
        ).exists()
    
    # Get variants by attribute
    variants_by_attribute = {}
    for variant in product.variants.filter(is_active=True):
        for attr, value in variant.attributes.items():
            if attr not in variants_by_attribute:
                variants_by_attribute[attr] = []
            if value not in [v['value'] for v in variants_by_attribute[attr]]:
                variants_by_attribute[attr].append({
                    'value': value,
                    'variant_id': variant.id,
                    'in_stock': variant.stock_quantity > 0
                })
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'reviews_count': reviews.count(),
        'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
        'user_purchased': user_purchased,
        'user_review': user_review,
        'variants_by_attribute': variants_by_attribute,
    }
    return render(request, 'store/product_detail.html', context)

# Add to cart view
@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    variant_id = request.POST.get('variant_id')
    
    product = get_object_or_404(Product, id=product_id, status='active')
    
    # Check stock
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        if variant.stock_quantity < quantity:
            return JsonResponse({'success': False, 'error': 'Not enough stock'})
    else:
        if product.stock_quantity < quantity:
            return JsonResponse({'success': False, 'error': 'Not enough stock'})
    
    # Get or create cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_id=session_id, user=None)
    
    # Check if item already in cart
    cart_item = cart.items.filter(product=product, variant_id=variant_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            variant_id=variant_id,
            quantity=quantity,
            price=variant.price_adjustment + product.selling_price if variant else product.selling_price
        )
    
    return JsonResponse({
        'success': True,
        'cart_count': cart.get_item_count(),
        'cart_total': str(cart.get_total()),
        'message': f'{product.name} added to cart'
    })

# Cart view
def cart(request):
    cart = None
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id, user=None).first()
    
    if not cart:
        cart = Cart.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key if not request.user.is_authenticated else None
        )
    
    # Handle quantity updates
    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        
        if action == 'update':
            quantity = int(request.POST.get('quantity'))
            item = get_object_or_404(CartItem, id=item_id, cart=cart)
            if quantity > 0:
                item.quantity = quantity
                item.save()
            else:
                item.delete()
            messages.success(request, 'Cart updated successfully')
        elif action == 'remove':
            item = get_object_or_404(CartItem, id=item_id, cart=cart)
            item.delete()
            messages.success(request, 'Item removed from cart')
        elif action == 'clear':
            cart.items.all().delete()
            messages.success(request, 'Cart cleared')
        
        return redirect('store:cart')
    
    # Get recommendations
    if cart.items.exists():
        cart_products = cart.items.values_list('product_id', flat=True)
        recommendations = Product.objects.filter(
            status='active',
            category__in=cart.items.values_list('product__category', flat=True)
        ).exclude(id__in=cart_products)[:4]
    else:
        recommendations = Product.objects.filter(status='active', is_featured=True)[:4]
    
    context = {
        'cart': cart,
        'items': cart.items.select_related('product', 'variant').all(),
        'recommendations': recommendations,
    }
    return render(request, 'store/cart.html', context)

# Checkout view
def checkout(request):
    # Get cart
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
    
    if not cart or not cart.items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('store:cart')
    
    # Get site settings for shipping and tax
    settings = SiteSettings.objects.first()
    
    # Calculate totals
    subtotal = cart.get_total()
    shipping = settings.default_shipping_cost if settings else 0
    if settings and subtotal >= settings.shipping_threshold:
        shipping = 0
    tax = (subtotal + shipping) * (settings.tax_rate / 100) if settings else 0
    total = subtotal + shipping + tax
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                shipping_first_name=form.cleaned_data['shipping_first_name'],
                shipping_last_name=form.cleaned_data['shipping_last_name'],
                shipping_address=form.cleaned_data['shipping_address'],
                shipping_address2=form.cleaned_data['shipping_address2'],
                shipping_city=form.cleaned_data['shipping_city'],
                shipping_state=form.cleaned_data['shipping_state'],
                shipping_zipcode=form.cleaned_data['shipping_zipcode'],
                shipping_country=form.cleaned_data['shipping_country'],
                billing_first_name=form.cleaned_data['billing_first_name'],
                billing_last_name=form.cleaned_data['billing_last_name'],
                billing_address=form.cleaned_data['billing_address'],
                billing_address2=form.cleaned_data['billing_address2'],
                billing_city=form.cleaned_data['billing_city'],
                billing_state=form.cleaned_data['billing_state'],
                billing_zipcode=form.cleaned_data['billing_zipcode'],
                billing_country=form.cleaned_data['billing_country'],
                payment_method=form.cleaned_data['payment_method'],
                subtotal=subtotal,
                shipping_cost=shipping,
                tax=tax,
                total=total,
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    product_name=cart_item.product.name,
                    product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                    quantity=cart_item.quantity,
                    price=cart_item.price,
                    supplier=cart_item.product.supplier
                )
                
                # Update stock
                if cart_item.variant:
                    cart_item.variant.stock_quantity -= cart_item.quantity
                    cart_item.variant.save()
                else:
                    cart_item.product.stock_quantity -= cart_item.quantity
                    cart_item.product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            # Send order confirmation email
            send_order_confirmation_email(order)
            
            messages.success(request, 'Order placed successfully!')
            return redirect('store:order_success', order_number=order.order_number)
    else:
        # Pre-fill form if user is logged in
        initial = {}
        if request.user.is_authenticated:
            initial['email'] = request.user.email
            # Get default shipping address
            default_address = ShippingAddress.objects.filter(user=request.user, is_default=True).first()
            if default_address:
                initial.update({
                    'shipping_first_name': default_address.first_name,
                    'shipping_last_name': default_address.last_name,
                    'shipping_address': default_address.address,
                    'shipping_address2': default_address.address2,
                    'shipping_city': default_address.city,
                    'shipping_state': default_address.state,
                    'shipping_zipcode': default_address.zipcode,
                    'shipping_country': default_address.country,
                    'phone': default_address.phone,
                })
        
        form = CheckoutForm(initial=initial)
    
    context = {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'total': total,
        'settings': settings,
    }
    return render(request, 'checkout.html', context)

# Order success view
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    context = {
        'order': order,
        'settings': SiteSettings.objects.first(),
    }
    return render(request, 'order_success.html', context)

# Order invoice PDF
def order_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    settings = SiteSettings.objects.first()
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, settings.site_name if settings else "Dropshipping Store")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, "Invoice")
    p.drawString(50, height - 85, f"Invoice Number: INV-{order.order_number}")
    p.drawString(50, height - 100, f"Date: {order.created_at.strftime('%B %d, %Y')}")
    
    # Company Info
    p.drawString(400, height - 70, "From:")
    p.drawString(400, height - 85, settings.site_name if settings else "Dropshipping Store")
    p.drawString(400, height - 100, settings.address if settings else "")
    
    # Billing Info
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 150, "Bill To:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 165, f"{order.billing_first_name} {order.billing_last_name}")
    p.drawString(50, height - 180, order.billing_address)
    if order.billing_address2:
        p.drawString(50, height - 195, order.billing_address2)
    p.drawString(50, height - 210, f"{order.billing_city}, {order.billing_state} {order.billing_zipcode}")
    p.drawString(50, height - 225, order.billing_country)
    
    # Shipping Info
    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, height - 150, "Ship To:")
    p.setFont("Helvetica", 10)
    p.drawString(300, height - 165, f"{order.shipping_first_name} {order.shipping_last_name}")
    p.drawString(300, height - 180, order.shipping_address)
    if order.shipping_address2:
        p.drawString(300, height - 195, order.shipping_address2)
    p.drawString(300, height - 210, f"{order.shipping_city}, {order.shipping_state} {order.shipping_zipcode}")
    p.drawString(300, height - 225, order.shipping_country)
    
    # Table Header
    y = height - 280
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Item")
    p.drawString(250, y, "SKU")
    p.drawString(350, y, "Quantity")
    p.drawString(420, y, "Price")
    p.drawString(500, y, "Total")
    
    p.line(50, y - 5, 550, y - 5)
    
    # Items
    y = height - 310
    p.setFont("Helvetica", 10)
    for item in order.items.all():
        p.drawString(50, y, item.product_name[:30])
        p.drawString(250, y, item.product_sku)
        p.drawString(370, y, str(item.quantity))
        p.drawString(420, y, f"${item.price}")
        p.drawString(500, y, f"${item.get_subtotal()}")
        y -= 20
        
        if y < 100:  # New page if needed
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)
    
    # Totals
    y = max(y - 20, 100)
    p.line(350, y, 550, y)
    y -= 20
    
    p.drawString(350, y, f"Subtotal: ${order.subtotal}")
    y -= 15
    p.drawString(350, y, f"Shipping: ${order.shipping_cost}")
    y -= 15
    p.drawString(350, y, f"Tax: ${order.tax}")
    y -= 15
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, y, f"Total: ${order.total}")
    
    # Footer
    p.setFont("Helvetica", 8)
    p.drawString(50, 50, "Thank you for your business!")
    
    p.showPage()
    p.save()
    
    # Get PDF value
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_number}.pdf"'
    response.write(pdf)
    
    return response

# Helper function to send order confirmation email
def send_order_confirmation_email(order):
    subject = f'Order Confirmation - {order.order_number}'
    html_message = render_to_string('emails/order_confirmation.html', {'order': order})
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to = order.email
    
    send_mail(subject, plain_message, from_email, [to], html_message=html_message)

# User registration
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('store:home')
    else:
        form = UserCreationForm()
    
    context = {'form': form}
    return render(request, 'store/register.html', context)

# User login
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Transfer guest cart to user
                session_id = request.session.session_key
                if session_id:
                    guest_cart = Cart.objects.filter(session_id=session_id, user=None).first()
                    if guest_cart:
                        user_cart, created = Cart.objects.get_or_create(user=user)
                        for item in guest_cart.items.all():
                            item.cart = user_cart
                            item.save()
                        guest_cart.delete()
                
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'store:home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    context = {'form': form}
    return render(request, 'store/login.html', context)

# User logout
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('store:home')

# User profile
@login_required
def profile(request):
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at')
    addresses = ShippingAddress.objects.filter(user=user)
    wishlist = Wishlist.objects.filter(user=user).select_related('product')
    
    # Get user reviews
    reviews = Review.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'user': user,
        'orders': orders,
        'addresses': addresses,
        'wishlist': wishlist,
        'reviews': reviews,
    }
    return render(request, 'profile.html', context)

# Add to wishlist
@login_required
@require_POST
def add_to_wishlist(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        message = f'{product.name} added to wishlist'
    else:
        wishlist_item.delete()
        message = f'{product.name} removed from wishlist'
    
    return JsonResponse({'success': True, 'message': message})

# Add review
@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            # Check if user already reviewed
            existing_review = Review.objects.filter(product=product, user=request.user).first()
            if existing_review:
                messages.error(request, 'You have already reviewed this product.')
                return redirect('store:product_detail', slug=product.slug)
            
            # Check if user purchased product
            purchased = Order.objects.filter(
                user=request.user,
                items__product=product,
                status='delivered'
            ).exists()
            
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.verified_purchase = purchased
            review.save()
            
            messages.success(request, 'Review submitted successfully! It will be visible after approval.')
            return redirect('store:product_detail', slug=product.slug)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'add_review.html', context)

# Apply coupon
@require_POST
def apply_coupon(request):
    code = request.POST.get('code')
    
    try:
        coupon = Coupon.objects.get(code=code.upper(), is_active=True)
        
        if not coupon.is_valid():
            return JsonResponse({'success': False, 'error': 'Coupon is expired or invalid'})
        
        # Get cart total
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_id = request.session.session_key
            cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
        
        if not cart:
            return JsonResponse({'success': False, 'error': 'Cart not found'})
        
        cart_total = cart.get_total()
        
        if cart_total < coupon.minimum_order:
            return JsonResponse({'success': False, 'error': f'Minimum order amount is ${coupon.minimum_order}'})
        
        # Calculate discount
        if coupon.discount_type == 'percentage':
            discount = (cart_total * coupon.discount_value / 100)
        else:
            discount = coupon.discount_value
        
        # Store coupon in session
        request.session['coupon_code'] = code
        request.session['coupon_discount'] = float(discount)
        
        return JsonResponse({
            'success': True,
            'discount': float(discount),
            'message': f'Coupon applied! You saved ${discount}'
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid coupon code'})

# Search suggestions
def search_suggestions(request):
    query = request.GET.get('q', '')
    suggestions = []
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        ).filter(status='active')[:5]
        
        suggestions = [{
            'id': p.id,
            'name': p.name,
            'price': str(p.selling_price),
            'image': p.main_image.url if p.main_image else '',
            'url': reverse('store:product_detail', args=[p.slug])
        } for p in products]
    
    return JsonResponse({'suggestions': suggestions})

# Track order
def track_order(request):
    order = None
    
    if request.method == 'POST':
        order_number = request.POST.get('order_number')
        email = request.POST.get('email')
        
        try:
            order = Order.objects.get(order_number=order_number, email=email)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found')
    
    context = {'order': order}
    return render(request, 'track_order.html', context)

# Static pages
def page_view(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, 'page.html', {'page': page})

# Category products view
def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Get all subcategories
    category_ids = [category.id]
    category_ids.extend([c.id for c in category.children.all()])
    
    products = Product.objects.filter(
        category_id__in=category_ids,
        status='active'
    )
    
    # Get subcategories for sidebar
    subcategories = category.children.filter(is_active=True)
    
    context = {
        'category': category,
        'products': products,
        'subcategories': subcategories,
        'total_products': products.count(),
    }
    return render(request, 'category_products.html', context)

# Admin dashboard
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied')
        return redirect('store:home')
    
    # Get statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum('total'))['total__sum'] or 0
    total_products = Product.objects.count()
    total_customers = User.objects.filter(is_active=True).count()
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    # Low stock products
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('low_stock_threshold'),
        stock_quantity__gt=0
    )[:5]
    
    out_of_stock_products = Product.objects.filter(stock_quantity=0)[:5]
    
    # Sales by day (last 7 days)
    last_7_days = timezone.now() - timezone.timedelta(days=7)
    daily_sales = Order.objects.filter(
        created_at__gte=last_7_days
    ).extra(
        {'day': "date(created_at)"}
    ).values('day').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('day')
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'daily_sales': daily_sales,
    }
    return render(request, 'store/admin_dashboard.html', context)

# Add these methods to views.py to support the URLs

def update_cart(request):
    """Update cart item quantity via AJAX"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            cart_item = CartItem.objects.get(id=item_id)
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                return JsonResponse({'success': True})
            else:
                cart_item.delete()
                return JsonResponse({'success': True})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(id=item_id)
            cart_item.delete()
            return JsonResponse({'success': True})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def clear_cart(request):
    """Clear entire cart"""
    if request.method == 'POST':
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_id = request.session.session_key
            cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
        
        if cart:
            cart.items.all().delete()
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def cart_count(request):
    """Get cart item count via AJAX"""
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
    
    if cart:
        count = cart.get_item_count()
    
    return JsonResponse({'count': count})

def user_orders(request):
    """Display user's orders"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'store/user_orders.html', context)

def order_detail(request, order_number):
    """Display order details"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Security check - only allow user or admin to view
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this order')
        return redirect('store:home')
    
    context = {'order': order}
    return render(request, 'order_detail.html', context)

def edit_profile(request):
    """Edit user profile"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('store:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {'form': form}
    return render(request, 'edit_profile.html', context)

def change_password(request):
    """Change user password"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully')
            return redirect('store:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {'form': form}
    return render(request, 'change_password.html', context)

def wishlist(request):
    """Display user's wishlist"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {'wishlist_items': wishlist_items}
    return render(request, 'wishlist.html', context)

def remove_from_wishlist(request, product_id):
    """Remove item from wishlist"""
    if request.method == 'POST' and request.user.is_authenticated:
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

def edit_review(request, review_id):
    """Edit a review"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Review updated successfully')
            return redirect('store:product_detail', slug=review.product.slug)
    else:
        form = ReviewForm(instance=review)
    
    context = {'form': form, 'review': review}
    return render(request, 'edit_review.html', context)

def delete_review(request, review_id):
    """Delete a review"""
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id, user=request.user)
        product_slug = review.product.slug
        review.delete()
        messages.success(request, 'Review deleted successfully')
        return redirect('store:product_detail', slug=product_slug)
    
    return JsonResponse({'success': False})

def address_list(request):
    """List user's addresses"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    addresses = ShippingAddress.objects.filter(user=request.user)
    context = {'addresses': addresses}
    return render(request, 'address_list.html', context)

def add_address(request):
    """Add new address"""
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully')
            return redirect('store:address_list')
    else:
        form = ShippingAddressForm()
    
    context = {'form': form}
    return render(request, 'add_address.html', context)

def edit_address(request, address_id):
    """Edit address"""
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully')
            return redirect('store:address_list')
    else:
        form = ShippingAddressForm(instance=address)
    
    context = {'form': form, 'address': address}
    return render(request, 'edit_address.html', context)

def delete_address(request, address_id):
    """Delete address"""
    if request.method == 'POST':
        address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        address.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

def set_default_address(request, address_id):
    """Set default shipping address"""
    if request.method == 'POST':
        address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        
        # Remove default from all other addresses
        ShippingAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Set this as default
        address.is_default = True
        address.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

def remove_coupon(request):
    """Remove applied coupon"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
        del request.session['coupon_discount']
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

def search(request):
    """Search products"""
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        ).filter(status='active').distinct()
    else:
        products = Product.objects.none()
    
    context = {
        'query': query,
        'products': products,
        'count': products.count()
    }
    return render(request, 'search_results.html', context)

def newsletter_subscribe(request):
    """Subscribe to newsletter"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                return JsonResponse({'success': True, 'message': 'Subscribed successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Email already subscribed'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def newsletter_unsubscribe(request, email):
    """Unsubscribe from newsletter"""
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email)
        subscriber.is_active = False
        subscriber.save()
        return render(request, 'newsletter_unsubscribe.html', {'success': True})
    except NewsletterSubscriber.DoesNotExist:
        return render(request, 'newsletter_unsubscribe.html', {'success': False})

def contact(request):
    """Contact form"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Send email
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            from_email = form.cleaned_data['email']
            name = form.cleaned_data['name']
            
            full_message = f"From: {name}\nEmail: {from_email}\n\n{message}"
            
            send_mail(
                subject,
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, 'Message sent successfully')
            return redirect('store:contact_success')
    else:
        form = ContactForm()
    
    context = {'form': form}
    return render(request, 'contact.html', context)

def contact_success(request):
    """Contact form success page"""
    return render(request, 'contact_success.html')

def about(request):
    """About page"""
    return render(request, 'about.html', {'settings': SiteSettings.objects.first()})

def faq(request):
    """FAQ page"""
    return render(request, 'faq.html')

def shipping_info(request):
    """Shipping information page"""
    return render(request, 'shipping_info.html', {'settings': SiteSettings.objects.first()})

def returns_policy(request):
    """Returns policy page"""
    return render(request, 'returns_policy.html')

def privacy_policy(request):
    """Privacy policy page"""
    return render(request, 'privacy_policy.html')

def terms_conditions(request):
    """Terms and conditions page"""
    return render(request, 'terms_conditions.html')

# API View methods
def api_product_detail(request, product_id):
    """API endpoint for product details"""
    try:
        product = Product.objects.get(id=product_id, status='active')
        data = {
            'id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'stock': product.stock_quantity,
            'description': product.short_description,
            'image': product.main_image.url if product.main_image else None,
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

def api_product_variants(request, product_id):
    """API endpoint for product variants"""
    try:
        product = Product.objects.get(id=product_id)
        variants = []
        for variant in product.variants.filter(is_active=True):
            variants.append({
                'id': variant.id,
                'name': variant.name,
                'price': float(variant.price_adjustment + product.selling_price),
                'stock': variant.stock_quantity,
                'attributes': variant.attributes,
            })
        return JsonResponse({'variants': variants})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

def api_check_stock(request):
    """API endpoint to check stock availability"""
    product_id = request.GET.get('product_id')
    quantity = int(request.GET.get('quantity', 1))
    variant_id = request.GET.get('variant_id')
    
    try:
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id, is_active=True)
            in_stock = variant.stock_quantity >= quantity
            stock = variant.stock_quantity
        else:
            product = Product.objects.get(id=product_id)
            in_stock = product.stock_quantity >= quantity
            stock = product.stock_quantity
        
        return JsonResponse({
            'in_stock': in_stock,
            'stock': stock,
            'quantity': quantity
        })
    except (Product.DoesNotExist, ProductVariant.DoesNotExist):
        return JsonResponse({'error': 'Product not found'}, status=404)

def api_calculate_shipping(request):
    """API endpoint to calculate shipping cost"""
    # Get cart total and items
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
    
    if not cart:
        return JsonResponse({'error': 'Cart not found'}, status=404)
    
    settings = SiteSettings.objects.first()
    subtotal = cart.get_total()
    
    # Calculate shipping
    if settings and subtotal >= settings.shipping_threshold:
        shipping_cost = 0
    else:
        shipping_cost = float(settings.default_shipping_cost) if settings else 10.00
    
    return JsonResponse({
        'subtotal': float(subtotal),
        'shipping': shipping_cost,
        'total': float(subtotal) + shipping_cost
    })

def api_validate_coupon(request):
    """API endpoint to validate coupon"""
    code = request.GET.get('code', '').upper()
    
    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
        
        if not coupon.is_valid():
            return JsonResponse({'valid': False, 'error': 'Coupon expired'})
        
        # Get cart total
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_id = request.session.session_key
            cart = Cart.objects.filter(session_id=session_id, user=None).first() if session_id else None
        
        if cart:
            cart_total = cart.get_total()
            if cart_total < coupon.minimum_order:
                return JsonResponse({
                    'valid': False, 
                    'error': f'Minimum order amount is ${coupon.minimum_order}'
                })
            
            # Calculate discount
            if coupon.discount_type == 'percentage':
                discount = float(cart_total * coupon.discount_value / 100)
            else:
                discount = float(coupon.discount_value)
            
            return JsonResponse({
                'valid': True,
                'discount': discount,
                'type': coupon.discount_type,
                'value': float(coupon.discount_value)
            })
        
        return JsonResponse({'valid': False, 'error': 'Cart not found'})
        
    except Coupon.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Invalid coupon code'})

def webhook_payment(request):
    """Handle payment gateway webhooks"""
    if request.method == 'POST':
        # Verify webhook signature
        # Process payment confirmation
        # Update order status
        pass
    return HttpResponse(status=200)

def webhook_supplier(request):
    """Handle supplier webhooks for order updates"""
    if request.method == 'POST':
        # Update supplier order status
        # Update tracking information
        pass
    return HttpResponse(status=200)

def sitemap(request):
    """Generate sitemap.xml"""
    products = Product.objects.filter(status='active')
    categories = Category.objects.filter(is_active=True)
    pages = Page.objects.filter(is_published=True)
    
    return render(request, 'sitemap.xml', {
        'products': products,
        'categories': categories,
        'pages': pages
    }, content_type='application/xml')

def robots_txt(request):
    """Generate robots.txt"""
    return render(request, 'robots.txt', content_type='text/plain')

# Error handlers
def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

# Admin API endpoints
def admin_chart_data(request):
    """API endpoint for admin chart data"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    period = request.GET.get('period', 'daily')
    
    # Generate data based on period
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    
    if period == 'daily':
        days = 30
        data = []
        labels = []
        for i in range(days):
            date = timezone.now() - timedelta(days=days-1-i)
            daily_total = Order.objects.filter(
                created_at__date=date.date()
            ).aggregate(Sum('total'))['total__sum'] or 0
            data.append(float(daily_total))
            labels.append(date.strftime('%b %d'))
    
    return JsonResponse({'labels': labels, 'values': data})

def admin_order_detail(request, order_id):
    """API endpoint for admin order details"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        order = Order.objects.get(id=order_id)
        data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'payment_status': order.payment_status,
            'tracking_number': order.items.first().tracking_number if order.items.exists() else '',
            'notes': order.notes,
        }
        return JsonResponse(data)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

def admin_update_order_status(request):
    """API endpoint to update order status"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        status = request.POST.get('status')
        tracking_number = request.POST.get('tracking_number')
        notes = request.POST.get('notes')
        
        try:
            order = Order.objects.get(id=order_id)
            order.status = status
            order.notes = notes
            order.save()
            
            # Update tracking number on order items
            if tracking_number:
                order.items.update(tracking_number=tracking_number)
            
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def admin_export_report(request):
    """Export admin report as CSV/PDF"""
    if not request.user.is_staff:
        return redirect('store:home')
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Order #', 'Customer', 'Total', 'Status'])
    
    orders = Order.objects.all().order_by('-created_at')
    for order in orders:
        writer.writerow([
            order.created_at.date(),
            order.order_number,
            order.get_full_name(),
            order.total,
            order.get_status_display()
        ])
    
    return response

def admin_dashboard_stream(request):
    """SSE endpoint for real-time dashboard updates"""
    from django.http import StreamingHttpResponse
    import json
    import time
    
    def event_stream():
        while True:
            # Check for new orders
            recent_order = Order.objects.filter(created_at__gte=timezone.now() - timedelta(seconds=30)).first()
            if recent_order:
                yield f"data: {json.dumps({'new_order': {'order_number': recent_order.order_number}})}\n\n"
            
            # Check for low stock
            low_stock = Product.objects.filter(
                stock_quantity__lte=F('low_stock_threshold'),
                stock_quantity__gt=0
            ).first()
            if low_stock:
                yield f"data: {json.dumps({'low_stock': {'product_name': low_stock.name}})}\n\n"
            
            time.sleep(30)
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

from django.shortcuts import get_object_or_404, redirect
from .models import Review  # make sure you have a Review model

def helpful_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    
    # Example: increment a 'helpful_count' field
    review.helpful_count = (review.helpful_count or 0) + 1
    review.save()
    
    # Redirect back to the product page
    return redirect('store:product_detail', slug=review.product.slug)



# LOGIN AND REGISTRATION VIEWS
# Add these to your existing views.py

from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import NewsletterSubscriber, UserProfile
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm

def register(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Handle newsletter subscription
            if request.POST.get('newsletter'):
                NewsletterSubscriber.objects.get_or_create(
                    email=user.email,
                    defaults={'is_active': True}
                )
            
            # Log the user in
            login(request, user)
            
            messages.success(request, 'Registration successful! Welcome to our store!')
            
            # Send welcome email
            send_welcome_email(user)
            
            return redirect('store:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Register - Dropshipping Store'
    }
    return render(request, 'store/register.html', context)

def user_login(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = request.POST.get('remember_me')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Handle remember me
                if not remember_me:
                    request.session.set_expiry(0)
                
                # Transfer guest cart to user
                transfer_guest_cart(request, user)
                
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to next page if specified
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('store:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    context = {
        'form': form,
        'next': request.GET.get('next', ''),
        'title': 'Login - Dropshipping Store'
    }
    return render(request, 'store/login.html', context)

@login_required
def user_logout(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('store:login')

@login_required
def profile(request):
    """
    User profile view
    """
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    # Get user statistics
    total_orders = user.orders.count()
    total_spent = user.orders.aggregate(total=models.Sum('total'))['total'] or 0
    wishlist_count = user.wishlist.count()
    review_count = user.review_set.count()
    
    # Get recent orders
    recent_orders = user.orders.order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'profile': profile,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'wishlist_count': wishlist_count,
        'review_count': review_count,
        'recent_orders': recent_orders,
        'title': f'{user.username}\'s Profile'
    }
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    """
    Edit user profile view
    """
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            
            # Update user model fields
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('store:profile')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        })
    
    context = {
        'form': form,
        'title': 'Edit Profile'
    }
    return render(request, 'edit_profile.html', context)

# Helper functions
def transfer_guest_cart(request, user):
    """
    Transfer guest cart items to user's cart after login
    """
    from .models import Cart
    
    session_id = request.session.session_key
    if session_id:
        try:
            guest_cart = Cart.objects.get(session_id=session_id, user__isnull=True)
            user_cart, created = Cart.objects.get_or_create(user=user)
            
            # Transfer items
            for item in guest_cart.items.all():
                item.cart = user_cart
                item.save()
            
            # Delete guest cart
            guest_cart.delete()
            
        except Cart.DoesNotExist:
            pass

def send_welcome_email(user):
    """
    Send welcome email to new user
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    subject = 'Welcome to Dropshipping Store!'
    html_message = render_to_string('store/welcome_email.html', {'user': user})
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")

# API endpoint for username availability
def api_check_username(request):
    """
    Check if username is available
    """
    from django.contrib.auth.models import User
    from django.http import JsonResponse
    
    username = request.GET.get('username', '')
    if username:
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'available': not exists})
    return JsonResponse({'available': False})

@login_required
def wishlist(request):
    """Display user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    # Get recommended products (products from same categories as wishlist items)
    recommended_products = Product.objects.none()
    if wishlist_items.exists():
        category_ids = wishlist_items.values_list('product__category_id', flat=True)
        recommended_products = Product.objects.filter(
            category_id__in=category_ids,
            status='active'
        ).exclude(
            id__in=wishlist_items.values_list('product_id', flat=True)
        ).distinct()[:4]
    
    context = {
        'wishlist_items': wishlist_items,
        'recommended_products': recommended_products
    }
    return render(request, 'store/wishlist.html', context)

@login_required
def profile(request):
    """User profile view"""
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    # Get default address
    default_address = ShippingAddress.objects.filter(user=user, is_default=True).first()
    
    # Get statistics
    total_orders = Order.objects.filter(user=user).count()
    total_spent = Order.objects.filter(user=user, status='delivered').aggregate(total=models.Sum('total'))['total'] or 0
    wishlist_count = Wishlist.objects.filter(user=user).count()
    review_count = Review.objects.filter(user=user).count()
    
    # Get recent orders
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'profile': profile,
        'default_address': default_address,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'wishlist_count': wishlist_count,
        'review_count': review_count,
        'recent_orders': recent_orders,
    }
    return render(request, 'store/profile.html', context)