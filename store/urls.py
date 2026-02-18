# store/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'store'

urlpatterns = [
    # Home and Main Pages
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('page/<slug:slug>/', views.page_view, name='page'),
    
    # Cart URLs
    path('cart/', views.cart, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    
    # Checkout and Orders
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('order/invoice/<str:order_number>/', views.order_invoice, name='order_invoice'),
    path('order/track/', views.track_order, name='track_order'),
    #path('orders/', views.user_orders, name='user_orders'),
    path('orders/', views.user_orders, name='orders'),
    path('orders/', views.user_orders, name='user_orders'),


    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    
    # User Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Password Reset (using Django's built-in views)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='password_reset.html',
             email_template_name='password_reset_email.html',
             subject_template_name='password_reset_subject.txt'
         ), name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Reviews
    path('review/add/<int:product_id>/', views.add_review, name='add_review'),
    path('review/edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/helpful/', views.helpful_review, name='helpful_review'),
    
    # Address Management
    path('addresses/', views.address_list, name='address_list'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('address/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
    
    # Coupons
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
    
    # Search and Suggestions
    path('search/', views.search, name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    
    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/<str:email>/', views.newsletter_unsubscribe, name='newsletter_unsubscribe'),
    
    # Contact
    path('contact/', views.contact, name='contact'),
    path('contact/success/', views.contact_success, name='contact_success'),
    
    # Static Pages
    path('about/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('shipping/', views.shipping_info, name='shipping_info'),
    path('returns/', views.returns_policy, name='returns_policy'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_conditions, name='terms_conditions'),
    
    # Admin Dashboard URLs
    #path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    # store/urls.py
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('admin/chart-data/', views.admin_chart_data, name='admin_chart_data'),
    path('admin/order/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/order/update-status/', views.admin_update_order_status, name='admin_update_order_status'),
    path('admin/export-report/', views.admin_export_report, name='admin_export_report'),
    path('admin/dashboard/stream/', views.admin_dashboard_stream, name='admin_dashboard_stream'),
    
    # API-like endpoints for AJAX
    path('api/product/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/product-variants/<int:product_id>/', views.api_product_variants, name='api_product_variants'),
    path('api/check-stock/', views.api_check_stock, name='api_check_stock'),
    path('api/calculate-shipping/', views.api_calculate_shipping, name='api_calculate_shipping'),
    path('api/validate-coupon/', views.api_validate_coupon, name='api_validate_coupon'),
    
    # Webhook endpoints (for payment gateways, suppliers, etc.)
    path('webhook/payment/', views.webhook_payment, name='webhook_payment'),
    path('webhook/supplier/', views.webhook_supplier, name='webhook_supplier'),
    
    # Sitemap and SEO
    path('sitemap.xml/', views.sitemap, name='sitemap'),
    path('robots.txt/', views.robots_txt, name='robots_txt'),

    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # API endpoints
    path('api/check-username/', views.api_check_username, name='api_check_username'),
]

# Additional URL patterns for specific functionality
handler404 = 'store.views.handler404'
handler500 = 'store.views.handler500'