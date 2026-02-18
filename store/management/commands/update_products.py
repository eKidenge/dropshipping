# store/management/commands/update_products.py
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import mail_admins
from store.models import Product, Supplier, Category
from django.db import transaction
import requests
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import time
from typing import Dict, List, Any, Optional
import hashlib
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates product information from supplier APIs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--supplier-id',
            type=int,
            help='Specific supplier ID to update (updates all if not specified)'
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Specific product ID to update'
        )
        parser.add_argument(
            '--full-sync',
            action='store_true',
            help='Perform full sync instead of just updates'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate updates without saving to database'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recently updated'
        )
        parser.add_argument(
            '--max-products',
            type=int,
            default=1000,
            help='Maximum number of products to process'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between API calls in seconds'
        )
    
    def handle(self, *args, **options):
        """
        Main command handler
        """
        supplier_id = options.get('supplier_id')
        product_id = options.get('product_id')
        full_sync = options.get('full_sync', False)
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        max_products = options.get('max_products', 1000)
        delay = options.get('delay', 0.5)
        
        self.stdout.write(self.style.SUCCESS('Starting product update process...'))
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write(f"Full sync: {'Yes' if full_sync else 'No'}")
        self.stdout.write(f"Force update: {'Yes' if force else 'No'}")
        
        # Statistics tracking
        stats = {
            'total': 0,
            'updated': 0,
            'created': 0,
            'failed': 0,
            'skipped': 0,
            'out_of_stock': 0,
            'price_changes': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            if product_id:
                # Update single product
                try:
                    product = Product.objects.get(id=product_id)
                    self.update_single_product(product, stats, dry_run, force)
                except Product.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Product with ID {product_id} not found'))
            
            elif supplier_id:
                # Update products from specific supplier
                try:
                    supplier = Supplier.objects.get(id=supplier_id, is_active=True)
                    self.stdout.write(f"Updating products from supplier: {supplier.name}")
                    self.update_supplier_products(supplier, stats, full_sync, dry_run, force, max_products, delay)
                except Supplier.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Supplier with ID {supplier_id} not found'))
            
            else:
                # Update all active suppliers
                suppliers = Supplier.objects.filter(is_active=True)
                self.stdout.write(f"Found {suppliers.count()} active suppliers")
                
                for supplier in suppliers:
                    self.stdout.write(f"\nProcessing supplier: {supplier.name}")
                    try:
                        self.update_supplier_products(supplier, stats, full_sync, dry_run, force, max_products, delay)
                    except Exception as e:
                        error_msg = f"Error updating supplier {supplier.name}: {str(e)}"
                        stats['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                    
                    # Add delay between suppliers to avoid rate limiting
                    if delay > 0:
                        time.sleep(delay * 2)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nProcess interrupted by user'))
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            stats['errors'].append(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
            
            # Notify admins
            self.notify_admins_of_failure(error_msg)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Print summary
        self.print_summary(stats, execution_time)
        
        # Send email report
        self.send_report_email(stats, execution_time)
    
    def update_supplier_products(self, supplier: Supplier, stats: Dict, full_sync: bool, 
                                 dry_run: bool, force: bool, max_products: int, delay: float):
        """
        Update products for a specific supplier
        """
        if not supplier.api_endpoint:
            self.stdout.write(self.style.WARNING(f"Supplier {supplier.name} has no API endpoint, skipping"))
            return
        
        try:
            # Fetch products from supplier API
            products_data = self.fetch_supplier_products(supplier, full_sync, max_products)
            
            if not products_data:
                self.stdout.write(self.style.WARNING(f"No products received from {supplier.name}"))
                return
            
            self.stdout.write(f"Received {len(products_data)} products from API")
            
            # Process each product
            for product_data in products_data:
                try:
                    self.process_product(supplier, product_data, stats, dry_run, force)
                    
                    # Add delay between API calls
                    if delay > 0:
                        time.sleep(delay)
                    
                    stats['total'] += 1
                    
                    # Progress indicator
                    if stats['total'] % 10 == 0:
                        self.stdout.write(f"Processed {stats['total']} products...", ending='\r')
                
                except Exception as e:
                    stats['failed'] += 1
                    error_msg = f"Error processing product: {str(e)}"
                    stats['errors'].append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
            
            self.stdout.write(f"\nCompleted {supplier.name}: {stats['updated']} updated, {stats['created']} created")
        
        except requests.RequestException as e:
            error_msg = f"API request failed for {supplier.name}: {str(e)}"
            stats['errors'].append(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
    
    def fetch_supplier_products(self, supplier: Supplier, full_sync: bool, max_products: int) -> List[Dict]:
        """
        Fetch products from supplier API
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Dropshipping-Store/1.0'
        }
        
        # Add API key if provided
        if supplier.api_key:
            headers['Authorization'] = f'Bearer {supplier.api_key}'
        
        params = {
            'limit': min(max_products, 100),  # API pagination
            'page': 1
        }
        
        if not full_sync:
            # Only get products updated in the last 24 hours
            params['updated_since'] = (timezone.now() - timedelta(days=1)).isoformat()
        
        all_products = []
        
        try:
            while len(all_products) < max_products:
                response = requests.get(
                    supplier.api_endpoint,
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Handle different API response formats
                products = self.extract_products_from_response(data)
                
                if not products:
                    break
                
                all_products.extend(products)
                
                # Check if there are more pages
                if len(products) < params['limit']:
                    break
                
                params['page'] += 1
                
                # Rate limiting
                time.sleep(0.1)
            
            return all_products[:max_products]
        
        except requests.Timeout:
            raise Exception("API request timeout")
        except requests.ConnectionError:
            raise Exception("Connection error")
        except requests.HTTPError as e:
            raise Exception(f"HTTP error: {e.response.status_code}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response")
    
    def extract_products_from_response(self, data: Any) -> List[Dict]:
        """
        Extract products from various API response formats
        """
        if isinstance(data, dict):
            # Handle common API response structures
            if 'products' in data:
                return data['products']
            elif 'data' in data:
                return data['data']
            elif 'items' in data:
                return data['items']
            elif 'result' in data:
                return data['result']
            else:
                # Assume the whole response is a list of products
                return [data] if data.get('id') else []
        
        elif isinstance(data, list):
            return data
        
        return []
    
    def process_product(self, supplier: Supplier, product_data: Dict, stats: Dict, 
                        dry_run: bool, force: bool):
        """
        Process and update a single product
        """
        # Extract product details
        supplier_sku = self.extract_supplier_sku(product_data)
        if not supplier_sku:
            stats['skipped'] += 1
            return
        
        # Check if product exists
        try:
            product = Product.objects.get(supplier=supplier, supplier_sku=supplier_sku)
            action = 'update'
        except Product.DoesNotExist:
            if not self.should_create_product(product_data):
                stats['skipped'] += 1
                return
            product = Product(supplier=supplier, supplier_sku=supplier_sku)
            action = 'create'
        
        # Check if update is needed
        if action == 'update' and not force:
            last_update = product.updated_at
            if last_update and last_update > timezone.now() - timedelta(hours=1):
                stats['skipped'] += 1
                return
        
        # Extract product data
        new_data = self.map_product_data(product_data, supplier)
        
        # Track changes
        changes = self.get_changes(product, new_data) if action == 'update' else None
        
        if dry_run:
            self.log_dry_run(product, action, new_data, changes)
            if action == 'update':
                stats['updated'] += 1
            else:
                stats['created'] += 1
            return
        
        # Update product
        with transaction.atomic():
            try:
                # Update fields
                for field, value in new_data.items():
                    setattr(product, field, value)
                
                # Handle special fields
                if 'category' in new_data:
                    product.category = self.get_or_create_category(new_data['category'])
                
                # Calculate selling price based on markup
                if 'cost_price' in new_data:
                    product.selling_price = self.calculate_selling_price(
                        product.cost_price, supplier
                    )
                
                # Check stock status
                if product.stock_quantity == 0:
                    stats['out_of_stock'] += 1
                
                # Save product
                product.save()
                
                # Handle additional images if provided
                if 'additional_images' in new_data:
                    self.update_product_images(product, new_data['additional_images'])
                
                # Update statistics
                if action == 'update':
                    stats['updated'] += 1
                    if changes and 'selling_price' in changes:
                        stats['price_changes'] += 1
                else:
                    stats['created'] += 1
                
                self.stdout.write(
                    f"{'Updated' if action == 'update' else 'Created'}: {product.name} "
                    f"(SKU: {product.sku})",
                    level=2
                )
            
            except Exception as e:
                raise Exception(f"Failed to save product: {str(e)}")
    
    def extract_supplier_sku(self, product_data: Dict) -> Optional[str]:
        """
        Extract supplier SKU from product data
        """
        # Common SKU field names
        sku_fields = ['sku', 'supplier_sku', 'product_code', 'id', 'product_id', 'code']
        
        for field in sku_fields:
            if field in product_data and product_data[field]:
                return str(product_data[field])
        
        return None
    
    def map_product_data(self, product_data: Dict, supplier: Supplier) -> Dict:
        """
        Map API product data to model fields
        """
        # Common field mappings
        field_mappings = {
            'name': ['name', 'title', 'product_name', 'product_title'],
            'description': ['description', 'product_description', 'details', 'desc'],
            'short_description': ['short_description', 'summary', 'excerpt', 'brief'],
            'cost_price': ['price', 'cost', 'supplier_price', 'wholesale_price'],
            'stock_quantity': ['stock', 'quantity', 'inventory', 'stock_quantity', 'qty'],
            'weight': ['weight', 'product_weight'],
            'dimensions': ['dimensions', 'size', 'product_dimensions'],
            'main_image': ['image', 'main_image', 'featured_image', 'primary_image'],
            'category': ['category', 'categories', 'product_category'],
            'brand': ['brand', 'manufacturer', 'vendor'],
            'supplier_sku': ['sku', 'supplier_sku', 'product_code'],
        }
        
        mapped_data = {}
        
        for model_field, api_fields in field_mappings.items():
            for api_field in api_fields:
                if api_field in product_data and product_data[api_field]:
                    value = product_data[api_field]
                    
                    # Type conversions
                    if model_field in ['cost_price', 'selling_price', 'weight']:
                        try:
                            value = Decimal(str(value))
                        except (ValueError, TypeError, Decimal.InvalidOperation):
                            continue
                    
                    elif model_field == 'stock_quantity':
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            continue
                    
                    mapped_data[model_field] = value
                    break
        
        # Handle additional images
        if 'images' in product_data and isinstance(product_data['images'], list):
            mapped_data['additional_images'] = product_data['images']
        
        # Handle variants
        if 'variants' in product_data and isinstance(product_data['variants'], list):
            mapped_data['variants'] = product_data['variants']
        
        # Generate SKU if not provided
        if 'supplier_sku' not in mapped_data:
            mapped_data['supplier_sku'] = self.generate_sku(product_data, supplier)
        
        # Generate slug
        if 'name' in mapped_data:
            from django.utils.text import slugify
            base_slug = slugify(mapped_data['name'])
            mapped_data['slug'] = f"{base_slug}-{mapped_data['supplier_sku'][:8]}"
        
        return mapped_data
    
    def generate_sku(self, product_data: Dict, supplier: Supplier) -> str:
        """
        Generate a unique SKU for products without one
        """
        # Create a hash of product data
        data_string = f"{supplier.id}-{product_data.get('name', '')}-{timezone.now().timestamp()}"
        hash_object = hashlib.md5(data_string.encode())
        hash_short = hash_object.hexdigest()[:8].upper()
        
        return f"GEN-{supplier.id}-{hash_short}"
    
    def get_or_create_category(self, category_data: Any) -> Optional[Category]:
        """
        Get or create category from supplier data
        """
        if isinstance(category_data, dict):
            category_name = category_data.get('name', '')
        else:
            category_name = str(category_data)
        
        if not category_name:
            return None
        
        # Try to find existing category
        category, created = Category.objects.get_or_create(
            name__iexact=category_name,
            defaults={'name': category_name, 'is_active': True}
        )
        
        if created:
            self.stdout.write(f"Created new category: {category_name}", level=2)
        
        return category
    
    def calculate_selling_price(self, cost_price: Decimal, supplier: Supplier) -> Decimal:
        """
        Calculate selling price based on cost and markup
        """
        markup_percentage = getattr(settings, 'DROPSHIPPING_SETTINGS', {}).get(
            'DEFAULT_MARKUP_PERCENTAGE', 30
        )
        
        # Add supplier-specific markup if configured
        if hasattr(supplier, 'markup_percentage') and supplier.markup_percentage:
            markup_percentage = supplier.markup_percentage
        
        selling_price = cost_price * (1 + markup_percentage / 100)
        
        # Round to 2 decimal places
        return selling_price.quantize(Decimal('0.01'))
    
    def update_product_images(self, product: Product, image_urls: List[str]):
        """
        Update product images
        """
        from store.models import ProductImage
        from django.core.files.base import ContentFile
        import requests
        from io import BytesIO
        
        # Clear existing additional images
        product.additional_images.all().delete()
        
        for index, image_url in enumerate(image_urls[:5]):  # Limit to 5 images
            try:
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                
                # Create image file
                image_content = ContentFile(response.content)
                file_name = f"{product.sku}_{index}.jpg"
                
                # Create product image
                product_image = ProductImage(
                    product=product,
                    is_featured=(index == 0),
                    order=index
                )
                product_image.image.save(file_name, image_content, save=True)
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to download image {image_url}: {str(e)}"),
                    level=2
                )
    
    def get_changes(self, product: Product, new_data: Dict) -> Dict:
        """
        Get changes between current and new product data
        """
        changes = {}
        
        for field, new_value in new_data.items():
            if hasattr(product, field):
                old_value = getattr(product, field)
                
                # Compare values
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }
        
        return changes
    
    def should_create_product(self, product_data: Dict) -> bool:
        """
        Determine if a new product should be created
        """
        # Add your business logic here
        # For example: check if product has required fields
        required_fields = ['name', 'price']
        
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                return False
        
        return True
    
    def update_single_product(self, product: Product, stats: Dict, dry_run: bool, force: bool):
        """
        Update a single product
        """
        supplier = product.supplier
        
        if not supplier.api_endpoint:
            self.stdout.write(self.style.WARNING(f"Supplier has no API endpoint"))
            return
        
        # Fetch single product from API
        # This would need to be implemented based on supplier API
        self.stdout.write(self.style.WARNING("Single product update not yet implemented"))
    
    def log_dry_run(self, product: Product, action: str, new_data: Dict, changes: Dict = None):
        """
        Log dry run information
        """
        self.stdout.write(f"\n[DRY RUN] {'CREATE' if action == 'create' else 'UPDATE'}:")
        self.stdout.write(f"  Product: {new_data.get('name', 'Unknown')}")
        self.stdout.write(f"  SKU: {new_data.get('supplier_sku', 'Unknown')}")
        
        if changes:
            self.stdout.write("  Changes:")
            for field, change in changes.items():
                self.stdout.write(f"    {field}: {change['old']} -> {change['new']}")
    
    def print_summary(self, stats: Dict, execution_time: float):
        """
        Print execution summary
        """
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("UPDATE SUMMARY"))
        self.stdout.write("="*50)
        self.stdout.write(f"Total products processed: {stats['total']}")
        self.stdout.write(f"Products updated: {stats['updated']}")
        self.stdout.write(f"Products created: {stats['created']}")
        self.stdout.write(f"Products failed: {stats['failed']}")
        self.stdout.write(f"Products skipped: {stats['skipped']}")
        self.stdout.write(f"Out of stock: {stats['out_of_stock']}")
        self.stdout.write(f"Price changes: {stats['price_changes']}")
        self.stdout.write(f"Execution time: {execution_time:.2f} seconds")
        
        if stats['errors']:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for error in stats['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f"  - {error}")
            if len(stats['errors']) > 5:
                self.stdout.write(f"  ... and {len(stats['errors']) - 5} more errors")
        
        self.stdout.write("="*50)
    
    def send_report_email(self, stats: Dict, execution_time: float):
        """
        Send email report to admins
        """
        if stats['failed'] > 0 or stats['errors']:
            subject = f"Product Update Report - {stats['failed']} failures"
        else:
            subject = f"Product Update Report - Successful"
        
        message = f"""
Product Update Report
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
Execution Time: {execution_time:.2f} seconds

Summary:
- Total processed: {stats['total']}
- Updated: {stats['updated']}
- Created: {stats['created']}
- Failed: {stats['failed']}
- Skipped: {stats['skipped']}
- Out of stock: {stats['out_of_stock']}
- Price changes: {stats['price_changes']}

{f'Errors:\n' + chr(10).join(stats['errors'][:10]) if stats['errors'] else 'No errors occurred.'}
        """
        
        try:
            mail_admins(subject, message)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Failed to send email report: {e}"))
    
    def notify_admins_of_failure(self, error_msg: str):
        """
        Notify admins of critical failure
        """
        subject = "CRITICAL: Product Update Process Failed"
        message = f"""
The product update process failed with the following error:

{error_msg}

Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the logs for more details.
        """
        
        try:
            mail_admins(subject, message)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to notify admins: {e}"))