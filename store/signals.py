# store/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Order, Product, Review, NewsletterSubscriber
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """
    Handle order post-save events
    """
    if created:
        # Send order confirmation email
        try:
            send_mail(
                f'Order Confirmation - {instance.order_number}',
                f'Thank you for your order! Your order #{instance.order_number} has been received.',
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )
            logger.info(f"Order confirmation email sent for order {instance.order_number}")
        except Exception as e:
            logger.error(f"Failed to send order confirmation email: {e}")
    
    # Update product stock if order status changes to cancelled
    if instance.status == 'cancelled' and not created:
        for item in instance.items.all():
            product = item.product
            if product:
                product.stock_quantity += item.quantity
                product.save()
                logger.info(f"Stock updated for product {product.id} due to order cancellation")

@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    """
    Handle product pre-save events
    """
    # Check if stock is low
    if instance.track_inventory and instance.stock_quantity <= instance.low_stock_threshold:
        logger.warning(f"Low stock alert for product {instance.id}: {instance.name}")

@receiver(post_save, sender=Review)
def review_post_save(sender, instance, created, **kwargs):
    """
    Handle review post-save events
    """
    if created and not instance.is_approved:
        # Notify admin about new review
        send_mail(
            'New Review Awaiting Approval',
            f'A new review for {instance.product.name} is awaiting approval.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL],
            fail_silently=True,
        )

@receiver(post_save, sender=NewsletterSubscriber)
def newsletter_subscriber_post_save(sender, instance, created, **kwargs):
    """
    Handle newsletter subscriber post-save events
    """
    if created:
        # Send welcome email
        send_mail(
            'Welcome to our Newsletter!',
            'Thank you for subscribing to our newsletter. You will receive updates about new products and promotions.',
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=True,
        )

@receiver(post_delete, sender=Cart)
def cart_post_delete(sender, instance, **kwargs):
    """
    Clean up when cart is deleted
    """
    logger.info(f"Cart {instance.id} deleted")