"""
Limpieza única: elimina los acumulados registrados con línea de negocio "desconocido".

Se generaron porque Pólizas no tenía configurada la URL de Analítica en Render y los eventos
policy.issued no llegaban; los pagos de esas pólizas no se podían clasificar por producto.
Tras configurar ANALYTICS_SERVICE_URL en Pólizas, los nuevos datos se clasifican correctamente.
"""
from django.db import migrations


def limpiar(apps, schema_editor):
    for modelo in ("LossRatioByProduct", "ClaimsByType", "AvgResolutionTime"):
        apps.get_model("analitica", modelo).objects.filter(product_type="desconocido").delete()


class Migration(migrations.Migration):
    dependencies = [("analitica", "0001_initial")]
    operations = [migrations.RunPython(limpiar, migrations.RunPython.noop)]
