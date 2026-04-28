from ventas.models import Venta


class Despacho(Venta):
    class Meta:
        proxy = True
        verbose_name = "Pedido por despachar"
        verbose_name_plural = "Despachos"

