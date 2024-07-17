# tracker/migrations/0002_add_default_categories.py

from django.db import migrations

def add_default_categories(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    default_categories = [
        "Housing", "Transportation", "Food", "Utilities", "Insurance",
        "Healthcare", "Savings", "Debt Payments", "Personal", "Entertainment",
        "Education", "Gifts/Donations", "Clothing", "Miscellaneous"
    ]
    for category_name in default_categories:
        Category.objects.get_or_create(name=category_name)

def remove_default_categories(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    Category.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),  # Replace this with your actual previous migration name
    ]

    operations = [
        migrations.RunPython(add_default_categories, remove_default_categories),
    ]
