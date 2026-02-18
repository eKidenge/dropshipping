# store/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    # Product API
    path('products/', api_views.ProductListAPI.as_view(), name='api_products'),
    path('products/<int:pk>/', api_views.ProductDetailAPI.as_view(), name='api_product_detail'),
    path('products/search/', api_views.ProductSearchAPI.as_view(), name='api_product_search'),
    
    # Category API
    path('categories/', api_views.CategoryListAPI.as_view(), name='api_categories'),
    path('categories/<int:pk>/', api_views.CategoryDetailAPI.as_view(), name='api_category_detail'),
    
    # Cart API
    path('cart/', api_views.CartAPI.as_view(), name='api_cart'),
    path('cart/add/', api_views.CartAddAPI.as_view(), name='api_cart_add'),
    path('cart/update/', api_views.CartUpdateAPI.as_view(), name='api_cart_update'),
    path('cart/remove/', api_views.CartRemoveAPI.as_view(), name='api_cart_remove'),
    
    # Order API
    path('orders/', api_views.OrderListAPI.as_view(), name='api_orders'),
    path('orders/<str:order_number>/', api_views.OrderDetailAPI.as_view(), name='api_order_detail'),
    path('orders/track/<str:order_number>/', api_views.OrderTrackAPI.as_view(), name='api_order_track'),
    
    # User API
    path('user/profile/', api_views.UserProfileAPI.as_view(), name='api_user_profile'),
    path('user/addresses/', api_views.UserAddressAPI.as_view(), name='api_user_addresses'),
    path('user/wishlist/', api_views.UserWishlistAPI.as_view(), name='api_user_wishlist'),
    
    # Review API
    path('reviews/', api_views.ReviewListAPI.as_view(), name='api_reviews'),
    path('reviews/<int:pk>/', api_views.ReviewDetailAPI.as_view(), name='api_review_detail'),
    
    # Checkout API
    path('checkout/', api_views.CheckoutAPI.as_view(), name='api_checkout'),
    path('checkout/validate/', api_views.CheckoutValidateAPI.as_view(), name='api_checkout_validate'),
    
    # Payment API
    path('payment/process/', api_views.PaymentProcessAPI.as_view(), name='api_payment_process'),
    path('payment/confirm/', api_views.PaymentConfirmAPI.as_view(), name='api_payment_confirm'),
    
    # Shipping API
    path('shipping/calculate/', api_views.ShippingCalculateAPI.as_view(), name='api_shipping_calculate'),
    path('shipping/methods/', api_views.ShippingMethodsAPI.as_view(), name='api_shipping_methods'),
    
    # Coupon API
    path('coupon/validate/', api_views.CouponValidateAPI.as_view(), name='api_coupon_validate'),
    path('coupon/apply/', api_views.CouponApplyAPI.as_view(), name='api_coupon_apply'),
    
    # Admin API
    path('admin/stats/', api_views.AdminStatsAPI.as_view(), name='api_admin_stats'),
    path('admin/sales-data/', api_views.AdminSalesDataAPI.as_view(), name='api_admin_sales'),
    path('admin/inventory-alerts/', api_views.AdminInventoryAlertsAPI.as_view(), name='api_admin_inventory'),
]