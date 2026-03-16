# Tutorial Backend Ecommerce (Postman + Webpay Sandbox)

Este tutorial esta pensado para aprender el backend desde cero usando Postman.

## 1. Qué tiene este backend

Dominios:
- Auth (`/auth/`)
- Usuarios (`/users/`)
- Geografia de usuarios (`/users/regiones/`, `/users/comunas/`)
- Catalogo de libros (`/productos/` y alias `/catalog/`)
- Inventario (`/inventory/`)
- Carrito y checkout (`/checkout/`)
- Ordenes (`/orders/`)
- Pagos (`/payments/`)
- Ventas y analitica (`/ventas/`)
- Envio (`/shipping/`)

Flujo principal ecommerce:
1. Usuario se autentica.
2. Consulta catalogo y libros.
3. Crea carrito y agrega items.
4. Convierte carrito a venta (crea orden).
5. Crea intento de pago.
6. Confirma pago (Webpay commit o webhook mock).
7. Consulta historial de ordenes y reportes.

---

## 2. Preparación local

En `backend/.env` deben existir (ya configurado):

```env
DB_URL=...
WEBPAY_COMMERCE_CODE=597055555532
WEBPAY_API_KEY=579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C
WEBPAY_RETURN_URL=http://localhost:8000/payments/webpay/commit/
```

Comandos:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Base URL en Postman:
- `http://localhost:8000`

---

## 3. Configurar Postman

Crear un Environment con variables:
- `base_url` = `http://localhost:8000`
- `access_token` = (vacio)
- `user_id` = (vacio)
- `region_id` = (vacio)
- `comuna_id` = (vacio)
- `cart_id` = (vacio)
- `order_id` = (vacio)
- `payment_reference` = (vacio)
- `guest_token` = `guest-demo-123`

Header global para requests autenticadas:
- `Authorization: Bearer {{access_token}}`

Importante para auth local:
- Antes de `POST /auth/jwt/create/`, `POST /auth/jwt/refresh/` y `POST /auth/jwt/logout/` primero llama `GET /auth/csrf/`.
- El backend devuelve `access` en el body y guarda el `refresh_token` en cookie HttpOnly. No esperes `refresh` en JSON.

---

## 4. Auth y usuarios

## 4.0 Consultar regiones y comunas
`GET {{base_url}}/users/regiones/`

Luego:

`GET {{base_url}}/users/comunas/?region_id={region_id}`

Guarda ids validos en `region_id` y `comuna_id`.

## 4.1 Registrar usuario
`POST {{base_url}}/auth/users/`

Body:
```json
{
  "email": "cliente1@mail.com",
  "nombre": "Cliente",
  "apellido": "Demo",
  "direccion_entrega": "Calle 123",
  "region_id": {{region_id}},
  "comuna_id": {{comuna_id}},
  "password": "Password123!",
  "re_password": "Password123!"
}
```

## 4.2 Login JWT
`POST {{base_url}}/auth/jwt/create/`

Antes llama:

`GET {{base_url}}/auth/csrf/`

Body:
```json
{
  "email": "cliente1@mail.com",
  "password": "Password123!"
}
```

Guarda `access` en `access_token`.

El `refresh_token` queda en cookie HttpOnly del cliente HTTP.

Para Postman:
- activa cookies del dominio `localhost`
- envia `X-CSRFToken` con el valor de la cookie `csrftoken` en login, refresh y logout

## 4.2.1 Refresh JWT por cookie
`POST {{base_url}}/auth/jwt/refresh/`

Requiere:
- cookie `refresh_token`
- header `X-CSRFToken`

Respuesta:
- nuevo `access`

## 4.3 Ver usuario actual
`GET {{base_url}}/auth/users/me/`

## 4.4 Actualizar perfil con nueva ubicacion
`PATCH {{base_url}}/auth/users/me/`

Body:
```json
{
  "direccion_entrega": "Otra calle 456",
  "region_id": {{region_id}},
  "comuna_id": {{comuna_id}}
}
```

---

## 5. Catalogo y libros

Lectura publica:
- `GET {{base_url}}/catalog/books/`
- `GET {{base_url}}/catalog/books/{book_id}/`
- `GET {{base_url}}/catalog/authors/`
- `GET {{base_url}}/catalog/genres/`
- `GET {{base_url}}/catalog/publishers/`
- `GET {{base_url}}/catalog/works/`

Admin (requiere superuser):
- `POST/PATCH/DELETE` sobre `/catalog/books/...`

Tip:
- Usa un `book_id` real para pasos de carrito.

---

## 6. Inventario

Endpoints:
- `GET {{base_url}}/inventory/`
- `GET {{base_url}}/inventory/{book_id}/`

Admin:
- `PATCH {{base_url}}/inventory/{book_id}/`
- `GET {{base_url}}/inventory/admin/monitor/`

Importante:
- `available_stock = stock - reserved_stock`
- Al agregar al carrito se reserva stock.

---

## 7. Carrito y checkout

## 7.1 Resolver carrito (usuario anonimo o logueado)
`POST {{base_url}}/checkout/carts/resolve/`

Body:
```json
{
  "guest_token": "{{guest_token}}",
  "currency": "CLP"
}
```

Guarda `id` como `cart_id`.

## 7.2 Agregar item
`POST {{base_url}}/checkout/carts/{{cart_id}}/add-item/`

Body:
```json
{
  "book_id": 3,
  "quantity": 1
}
```

Si no hay stock disponible devuelve error.

## 7.3 Modificar item
`PATCH {{base_url}}/checkout/carts/{{cart_id}}/items/{item_id}/`

Body:
```json
{
  "quantity": 2
}
```

## 7.4 Aplicar descuento
`POST {{base_url}}/checkout/carts/{{cart_id}}/apply-discount/`

Body:
```json
{
  "type": "percent",
  "value": "10",
  "code": "PROMO10",
  "metadata": {}
}
```

## 7.5 Convertir carrito
`POST {{base_url}}/checkout/carts/{{cart_id}}/convert/`

Efectos:
- Consume stock reservado.
- Crea `Venta`.
- Crea `Order` con estado inicial `pending`.

---

## 8. Ordenes

## 8.1 Historial del cliente
`GET {{base_url}}/orders/me/`

Guarda el `id` de una orden como `order_id`.

## 8.2 Ver detalle de orden
`GET {{base_url}}/orders/{{order_id}}/`

Admin:
- `GET {{base_url}}/orders/admin/`
- `PATCH {{base_url}}/orders/{{order_id}}/admin/status/`

Body ejemplo:
```json
{
  "status": "shipped"
}
```

---

## 9. Pagos

Hay 2 providers:
- `mockpay` (simple para pruebas API puras)
- `webpay` (SDK oficial Transbank, sandbox)

## 9.1 Crear intent de pago (Webpay)
`POST {{base_url}}/payments/create-intent/`

Body:
```json
{
  "order_id": "{{order_id}}",
  "provider": "webpay"
}
```

Respuesta trae:
- `token`
- `webpay_url`
- `redirect_url`

Guarda `provider_reference` (o `token`) como `payment_reference`.

## 9.2 Confirmar pago Webpay (commit)
En un flujo real, Webpay redirige al `return_url` con `token_ws`.
Para aprender con Postman, puedes llamar manualmente:

`POST {{base_url}}/payments/webpay/commit/`

Body:
```json
{
  "token_ws": "{{payment_reference}}"
}
```

Si aprueba:
- `payment.status` cambia a `paid`
- `order.status` cambia a `paid`

## 9.3 Consultar estado en Webpay
`GET {{base_url}}/payments/webpay/status/?token_ws={{payment_reference}}`

## 9.4 Reembolso en Webpay
`POST {{base_url}}/payments/webpay/refund/`

Body:
```json
{
  "token_ws": "{{payment_reference}}",
  "amount": "1000"
}
```

## 9.5 Flujo mock (alternativo)
1. `POST /payments/create-intent/` con `provider=mockpay`
2. `POST /payments/webhook/` con:
```json
{
  "provider_reference": "mockpay_xxx",
  "status": "paid"
}
```

---

## 10. Shipping

## 10.1 Metodos de envio
`GET {{base_url}}/shipping/methods/`

## 10.2 Crear direccion
`POST {{base_url}}/shipping/address/`

Body:
```json
{
  "address": "Calle 123",
  "city": "Santiago",
  "region": "RM",
  "country": "Chile",
  "postal_code": "8320000"
}
```

## 10.3 Listar direcciones
`GET {{base_url}}/shipping/address/`

---

## 11. Ventas y analitica (admin)

- `GET {{base_url}}/ventas/`
- `GET {{base_url}}/ventas/stats/summary/?date_from=2026-03-01&date_to=2026-03-31`
- `GET {{base_url}}/ventas/stats/by-date/?group_by=day`
- `GET {{base_url}}/ventas/stats/by-book/`

---

## 12. Errores comunes y cómo leerlos

`401 Unauthorized`
- Falta `Authorization` o token expirado.

`403 Forbidden`
- Usuario sin permisos (admin endpoint).

`400 Bad Request`
- Body invalido o regla de negocio (ej. stock insuficiente).

`404 Not Found`
- Recurso no existe (`order_id`, `book_id`, etc).

---

## 13. Checklist de aprendizaje recomendado

1. Registrar usuario y loguear.
2. Consultar catalogo y elegir un libro.
3. Ajustar inventario por admin.
4. Crear carrito, agregar items, aplicar descuento.
5. Convertir carrito.
6. Ver orden en `/orders/me/`.
7. Pagar con `mockpay`.
8. Repetir con `webpay` sandbox.
9. Revisar ventas y reportes admin.

---

## 14. Referencias oficiales Webpay

- SDK Python oficial: https://github.com/TransbankDevelopers/transbank-sdk-python
- Documentacion Webpay Plus: https://www.transbankdevelopers.cl/documentacion/webpay-plus
- Credenciales de integracion y datos de prueba: https://www.transbankdevelopers.cl/documentacion/como_empezar#credenciales-de-prueba
