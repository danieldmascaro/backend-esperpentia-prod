# Pruebas de Endpoints

## Alcance
La suite valida el backend completo con el esquema nuevo:
- Auth (`/auth/...`)
- Usuarios (`/users/...`)
- Geografia de usuarios (`/users/regiones/...`, `/users/comunas/...`)
- Catalogo de libros y recursos relacionados (`/productos/...`, `/catalog/...`)
- Checkout (`/checkout/...`)
- Inventory (`/inventory/...`)
- Orders (`/orders/...`)
- Shipping (`/shipping/...`)
- Payments (`/payments/...`)
- Ventas (`/ventas/...`)

## Datos creados en tests
En `setUpTestData` se crean automaticamente:
- 1 admin y 2 usuarios cliente.
- 2 regiones y 3 comunas enlazadas.
- 2 generos, 2 editoriales, 2 autores y 2 obras.
- 2 libros conectados al nuevo grafo `Autor -> Obra <- Genero` y `Libro -> Editorial`.
- 2 metodos de envio.

Durante la ejecucion de tests tambien se crean via API:
- Nuevos usuarios.
- Nuevos autores, generos, editoriales, obras y libros.
- Carritos, direcciones, ordenes, pagos y ventas derivados del flujo ecommerce.

## Archivos
- Suite principal: `backend/usuarios/tests.py`

## Cobertura funcional
- Registro, login JWT, refresh, verify, perfil y ubicacion (`region_id`, `comuna_id`).
- CRUD base de usuarios.
- Catalogos de regiones y comunas, con filtro `region_id`.
- Lectura y alta de autores, generos, editoriales, obras y libros.
- Filtros de libros por `titulo`, `autor`, `editorial` y `genero`.
- Flujo de carrito usando `book_id` como item vendible.
- Inventario por libro.
- Conversion de carrito a venta y orden.
- Direcciones de envio.
- Pagos `mockpay` y endpoints Webpay con mocks.
- Reportes de ventas del nuevo esquema.

## Ejecucion
Desde `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Para ejecutar solo la suite principal:

```powershell
.\.venv\Scripts\python.exe manage.py test usuarios.tests.BackendEndpointsV2Tests
```

## Nota sobre Webpay
Los endpoints `commit`, `status` y `refund` se prueban con `unittest.mock.patch` para evitar dependencia de red o del servicio externo.
