from django.core.management.base import BaseCommand
from checkout.services import cleanup_expired_operation_logs


class Command(BaseCommand):
    help = "Limpia los registros de operaciones de carrito expirados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cuántos registros serían eliminados sin hacerlo realmente.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from checkout.models import CartOperationLog
            from django.utils import timezone

            count = CartOperationLog.objects.filter(
                expires_at__lt=timezone.now()
            ).count()
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Se eliminarían {count} registros de operación expirados."
                )
            )
        else:
            deleted = cleanup_expired_operation_logs()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Se eliminaron {deleted} registros de operación expirados."
                )
            )
