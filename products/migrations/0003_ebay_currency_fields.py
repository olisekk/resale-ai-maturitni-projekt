from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_productrequest_productmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="ebay_currency",
            field=models.CharField(blank=True, default="USD", max_length=3),
        ),
        migrations.AddField(
            model_name="generatedlisting",
            name="ebay_currency",
            field=models.CharField(blank=True, default="USD", max_length=3),
        ),
    ]