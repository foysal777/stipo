# Cleanup migration: remove PreDefinedScholarship_Sv from migration state.
#
# Why this exists:
#   Migration 0025 originally had a DeleteModel for this model but failed on
#   some database setups (KeyError in state_forwards). That operation was removed
#   from 0025 to unblock deployment. This migration performs the deletion safely:
#
#   - state_operations: removes the model from Django's migration state
#   - database_operations: uses DROP TABLE IF EXISTS so it works whether the
#     table already exists (fresh DB) or has already been dropped (existing DB).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_delete_predefinedscholarship_sv_coupon_created_at_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='PreDefinedScholarship_Sv',
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="DROP TABLE IF EXISTS app_predefinedscholarship_sv;",
                    reverse_sql="",
                ),
            ],
        ),
    ]
