from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("memories", "0004_daily_article_generation"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="capsule",
            constraint=models.UniqueConstraint(
                fields=("creator", "title"),
                name="unique_capsule_title_per_creator",
            ),
        ),
    ]
