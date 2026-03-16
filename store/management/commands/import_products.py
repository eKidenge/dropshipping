import csv
from django.core.management.base import BaseCommand
from store.models import Product, Category, Supplier
from django.utils.text import slugify
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import products from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                category = None
                if row.get('category'):
                    category, _ = Category.objects.get_or_create(name=row['category'])
                
                supplier = None
                if row.get('supplier'):
                    supplier, _ = Supplier.objects.get_or_create(name=row['supplier'])
                
                product, created = Product.objects.get_or_create(
                    sku=row['sku'],
                    defaults={
                        'name': row['name'],
                        'slug': slugify(row['name']),
                        'cost_price': Decimal(row['cost_price']),
                        'selling_price': Decimal(row['selling_price']),
                        'stock_quantity': int(row['stock_quantity']),
                        'category': category,
                        'supplier': supplier,
                    }
                )
                if created:
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'{count} products imported.'))