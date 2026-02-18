from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.db.models import Count, Sum, F
from django.urls import reverse
from django.utils import timezone
from .models import (
    Category, Supplier, Product, ProductImage, ProductVariant,
    Cart, CartItem, Order, OrderItem, ShippingAddress,
    Review, Wishlist, Coupon, NewsletterSubscriber, 
    SiteSettings, Page
)

class StockFilter(SimpleListFilter):
    title = 'stock status'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock'),
            ('out_of_stock', 'Out of Stock'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock_quantity__gt=F('low_stock_threshold'))
        if self.value() == 'low_stock':
            return queryset.filter(stock_quantity__lte=F('low_stock_threshold'), stock_quantity__gt=0)
        if self.value() == 'out_of_stock':
            return queryset.filter(stock_quantity=0)
        return queryset

class ProfitFilter(SimpleListFilter):
    title = 'profit margin'
    parameter_name = 'profit'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High (>50%%)'),
            ('medium', 'Medium (20-50%%)'),
            ('low', 'Low (<20%%)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(profit_margin__gt=50)
        if self.value() == 'medium':
            return queryset.filter(profit_margin__gte=20, profit_margin__lte=50)
        if self.value() == 'low':
            return queryset.filter(profit_margin__lt=20)
        return queryset

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt_text', 'is_featured', 'order']
    classes = ['collapse']

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['name', 'sku', 'attributes', 'price_adjustment', 'stock_quantity', 'is_active']
    classes = ['collapse']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['parent']
    actions = ['activate_categories', 'deactivate_categories']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)
    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_categories.short_description = "Deactivate selected categories"

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_name', 'email', 'phone', 'is_active', 'product_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'company_name', 'email']
    actions = ['activate_suppliers', 'deactivate_suppliers']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'company_name', 'email', 'phone', 'website', 'address')
        }),
        ('API Configuration', {
            'fields': ('api_endpoint', 'api_key'),
            'classes': ('collapse',)
        }),
        ('Shipping Details', {
            'fields': ('shipping_time_min', 'shipping_time_max', 'shipping_cost', 'minimum_order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

    def activate_suppliers(self, request, queryset):
        queryset.update(is_active=True)
    activate_suppliers.short_description = "Activate selected suppliers"

    def deactivate_suppliers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_suppliers.short_description = "Deactivate selected suppliers"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'supplier', 'category', 'selling_price', 'stock_quantity', 'status', 'profit_margin', 'product_image']
    list_filter = ['status', 'is_featured', 'is_bestseller', 'category', 'supplier', 'created_at', StockFilter, ProfitFilter]
    search_fields = ['name', 'sku', 'description', 'supplier_sku']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['profit_margin', 'created_at', 'updated_at', 'published_at']
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ['mark_as_active', 'mark_as_draft', 'mark_as_featured', 'update_prices']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('supplier', 'category', 'name', 'slug', 'sku', 'supplier_sku')
        }),
        ('Description', {
            'fields': ('short_description', 'description', 'features', 'specifications')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'compare_at_price', 'profit_margin')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'track_inventory', 'allow_backorder')
        }),
        ('Shipping', {
            'fields': ('weight', 'dimensions', 'shipping_cost')
        }),
        ('Images', {
            'fields': ('main_image',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'is_bestseller', 'is_new', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_image(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.main_image.url)
        return "No Image"
    product_image.short_description = 'Image'

    def mark_as_active(self, request, queryset):
        queryset.update(status='active', published_at=timezone.now())
    mark_as_active.short_description = "Mark selected as active"

    def mark_as_draft(self, request, queryset):
        queryset.update(status='draft')
    mark_as_draft.short_description = "Mark selected as draft"

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected as featured"

    def update_prices(self, request, queryset):
        for product in queryset:
            product.selling_price = product.cost_price * 1.3  # 30% markup
            product.save()
    update_prices.short_description = "Update prices (30%% markup)"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_sku', 'quantity', 'price', 'get_subtotal']
    fields = ['product_name', 'product_sku', 'quantity', 'price', 'get_subtotal', 'supplier_status', 'tracking_number']
    can_delete = False

    def get_subtotal(self, obj):
        return obj.get_subtotal()
    get_subtotal.short_description = 'Subtotal'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'get_full_name', 'email', 'total', 'status', 'payment_status', 'created_at', 'order_actions']
    list_filter = ['status', 'payment_status', 'created_at', 'shipping_country']
    search_fields = ['order_number', 'email', 'shipping_first_name', 'shipping_last_name']
    readonly_fields = ['order_number', 'subtotal', 'total', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'notes', 'admin_notes')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Shipping Address', {
            'fields': ('shipping_first_name', 'shipping_last_name', 'shipping_address', 'shipping_address2', 
                      'shipping_city', 'shipping_state', 'shipping_zipcode', 'shipping_country')
        }),
        ('Billing Address', {
            'fields': ('billing_first_name', 'billing_last_name', 'billing_address', 'billing_address2',
                      'billing_city', 'billing_state', 'billing_zipcode', 'billing_country')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_id')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'shipping_cost', 'tax', 'discount', 'total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Customer'
    get_full_name.admin_order_field = 'shipping_first_name'

    def order_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">View</a>&nbsp;'
            '<a class="button" href="{}">Invoice</a>',
            reverse('admin:store_order_change', args=[obj.pk]),
            reverse('store:order_invoice', args=[obj.order_number])
        )
    order_actions.short_description = 'Actions'

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
    mark_as_processing.short_description = "Mark selected as processing"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped', shipped_at=timezone.now())
    mark_as_shipped.short_description = "Mark selected as shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered', delivered_at=timezone.now())
    mark_as_delivered.short_description = "Mark selected as delivered"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "Mark selected as cancelled"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'title', 'verified_purchase', 'is_approved', 'helpful_votes', 'created_at']
    list_filter = ['rating', 'is_approved', 'verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'comment']
    actions = ['approve_reviews', 'disapprove_reviews']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'order', 'rating', 'title')
        }),
        ('Review Content', {
            'fields': ('comment', 'pros', 'cons')
        }),
        ('Status', {
            'fields': ('verified_purchase', 'is_approved', 'helpful_votes')
        }),
    )

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Disapprove selected reviews"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'minimum_order', 'valid_from', 'valid_to', 'is_valid', 'used_count']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    filter_horizontal = ['products', 'categories']
    actions = ['activate_coupons', 'deactivate_coupons']
    
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'discount_type', 'discount_value', 'minimum_order')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'used_count')
        }),
        ('Restrictions', {
            'fields': ('products', 'categories')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.short_description = 'Valid'
    is_valid.boolean = True

    def activate_coupons(self, request, queryset):
        queryset.update(is_active=True)
    activate_coupons.short_description = "Activate selected coupons"

    def deactivate_coupons(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_coupons.short_description = "Deactivate selected coupons"

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email']
    actions = ['activate_subscribers', 'deactivate_subscribers']

    def activate_subscribers(self, request, queryset):
        queryset.update(is_active=True)
    activate_subscribers.short_description = "Activate selected subscribers"

    def deactivate_subscribers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_subscribers.short_description = "Deactivate selected subscribers"

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'contact_email', 'contact_phone', 'currency', 'updated_at']
    fieldsets = (
        ('Site Information', {
            'fields': ('site_name', 'site_description', 'contact_email', 'contact_phone', 'address')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url')
        }),
        ('Store Settings', {
            'fields': ('shipping_threshold', 'default_shipping_cost', 'tax_rate', 'currency')
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_published', 'published_at', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    actions = ['publish_pages', 'unpublish_pages']
    
    fieldsets = (
        ('Page Information', {
            'fields': ('title', 'slug', 'content')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_published', 'published_at')
        }),
    )

    def publish_pages(self, request, queryset):
        queryset.update(is_published=True, published_at=timezone.now())
    publish_pages.short_description = "Publish selected pages"

    def unpublish_pages(self, request, queryset):
        queryset.update(is_published=False)
    unpublish_pages.short_description = "Unpublish selected pages"

# Register remaining models with basic admin
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image', 'is_featured', 'order']
    list_filter = ['is_featured']

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'sku', 'price_adjustment', 'stock_quantity', 'is_active']
    list_filter = ['is_active']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'get_item_count', 'get_total', 'created_at']
    readonly_fields = ['created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'

    def get_total(self, obj):
        return obj.get_total()
    get_total.short_description = 'Total'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'variant', 'quantity', 'price', 'get_subtotal']

    def get_subtotal(self, obj):
        return obj.get_subtotal()
    get_subtotal.short_description = 'Subtotal'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'product_sku', 'quantity', 'price', 'get_subtotal']
    list_filter = ['supplier_status']

    def get_subtotal(self, obj):
        return obj.get_subtotal()
    get_subtotal.short_description = 'Subtotal'

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_full_address', 'is_default']
    list_filter = ['is_default']

    def get_full_address(self, obj):
        return f"{obj.address}, {obj.city}, {obj.state} {obj.zipcode}"
    get_full_address.short_description = 'Address'

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']