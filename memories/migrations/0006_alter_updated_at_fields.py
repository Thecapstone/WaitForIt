from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("memories", "0005_unique_capsule_title_per_creator"),
    ]

    operations = [
        migrations.AlterField(
            model_name="capsule",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="images",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="logs",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="teasers",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="videos",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
