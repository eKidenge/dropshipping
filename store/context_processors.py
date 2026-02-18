# store/context_processors.py
from .models import Cart, Category, SiteSettings

def cart_count(request):
    """Context processor to add cart count to all templates"""
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = cart.get_item_count()
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id, user=None).first()
            if cart:
                cart_count = cart.get_item_count()
    
    return {'cart_count': cart_count}

def categories(request):
    """Context processor to add categories to all templates"""
    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related('children')[:10]
    return {'categories': categories}

def site_settings(request):
    """Context processor to add site settings to all templates"""
    settings = SiteSettings.objects.first()
    return {'site_settings': settings}