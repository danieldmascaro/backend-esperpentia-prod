# API Reference

Base URL: `http://localhost:8000/`
Auth: JWT Bearer token (`Authorization: Bearer <access_token>`)

## Convenciones generales

- Content-Type: `application/json`
- Listados con ViewSet usan paginacion DRF:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

- Para carrito anonimo:
  - Header recomendado: `X-Guest-Token: <token>`
- Para idempotencia en mutaciones de carrito:
  - Header opcional: `Idempotency-Key: <key-unica>`

---

## Auth (`/auth/`)

### POST `/auth/users/`
Crear usuario (registro).

Request:
```json
{
  "email": "cliente@mail.com",
  "nombre": "Juan",
  "apellido": "Perez",
  "direccion_entrega": "Av. Siempre Viva 123",
  "region_id": 1,
  "comuna_id": 3,
  "password": "PasswordSegura123",
  "re_password": "PasswordSegura123"
}
```

Response (201):
```json
{
  "id": 10,
  "email": "cliente@mail.com",
  "nombre": "Juan",
  "apellido": "Perez",
  "direccion_entrega": "Av. Siempre Viva 123",
  "region": {
    "id": 1,
    "nombre": "Region Metropolitana"
  },
  "comuna": {
    "id": 3,
    "nombre": "Santiago",
    "region": {
      "id": 1,
      "nombre": "Region Metropolitana"
    }
  }
}
```

### POST `/auth/jwt/create/`
Login por email/password.

Request:
```json
{
  "email": "cliente@mail.com",
  "password": "PasswordSegura123"
}
```

Response (200):
```json
{
  "access": "<access_token>"
}
```

Set-Cookie:
```http
refresh_token=<refresh_token>; HttpOnly; Path=/auth/jwt/; SameSite=Lax
```

### POST `/auth/jwt/refresh/`

Usa la cookie `refresh_token` enviada por el login.

Response (200):
```json
{
  "access": "<nuevo_access_token>"
}
```

### POST `/auth/jwt/logout/`

Limpia la cookie `refresh_token`.

Response (204): sin body

### POST `/auth/jwt/verify/`

Request:
```json
{
  "token": "<access_token>"
}
```

Response (200):
```json
{}
```

### GET `/auth/users/me/`
Usuario autenticado actual.

Response (200, ejemplo):
```json
{
  "id": 10,
  "email": "cliente@mail.com",
  "nombre": "Juan",
  "apellido": "Perez",
  "direccion_entrega": "Av. Siempre Viva 123",
  "region": {
    "id": 1,
    "nombre": "Region Metropolitana"
  },
  "region_id": 1,
  "comuna": {
    "id": 3,
    "nombre": "Santiago",
    "region": {
      "id": 1,
      "nombre": "Region Metropolitana"
    }
  },
  "comuna_id": 3
}
```

### PATCH `/auth/users/me/`
Actualizar perfil propio.

Request:
```json
{
  "nombre": "Juan Carlos",
  "direccion_entrega": "Nueva direccion 456",
  "region_id": 2,
  "comuna_id": 8
}
```

Response (200):
```json
{
  "id": 10,
  "email": "cliente@mail.com",
  "nombre": "Juan Carlos",
  "apellido": "Perez",
  "direccion_entrega": "Nueva direccion 456",
  "region": {
    "id": 2,
    "nombre": "Region de Valparaiso"
  },
  "region_id": 2,
  "comuna": {
    "id": 8,
    "nombre": "Valparaiso",
    "region": {
      "id": 2,
      "nombre": "Region de Valparaiso"
    }
  },
  "comuna_id": 8
}
```

### POST `/auth/users/set_password/`
Cambio de password logueado.

Request:
```json
{
  "current_password": "PasswordSegura123",
  "new_password": "OtraPasswordSegura123",
  "re_new_password": "OtraPasswordSegura123"
}
```

Response (204): sin body

### POST `/auth/users/reset_password/`
Solicitar email de recuperacion.

Request:
```json
{
  "email": "cliente@mail.com"
}
```

Response (204): sin body

### POST `/auth/users/reset_password_confirm/`

Request:
```json
{
  "uid": "<uid>",
  "token": "<token>",
  "new_password": "NuevaPassword123",
  "re_new_password": "NuevaPassword123"
}
```

Response (204): sin body

### POST `/auth/users/activation/`

Request:
```json
{
  "uid": "<uid>",
  "token": "<token>"
}
```

Response (204): sin body

### POST `/auth/users/resend_activation/`

Request:
```json
{
  "email": "cliente@mail.com"
}
```

Response (204): sin body

---

## Usuarios custom (`/users/`)

## Geografia de usuarios

### GET `/users/regiones/`
Lista regiones disponibles.

### GET `/users/regiones/{id}/`
Detalle de una region.

Response (200):
```json
{
  "id": 1,
  "nombre": "Region Metropolitana"
}
```

### GET `/users/comunas/`
Lista comunas disponibles.

Filtro opcional:
- `region_id`

Ejemplo:
- `GET /users/comunas/?region_id=1`

### GET `/users/comunas/{id}/`
Detalle de una comuna.

Response (200):
```json
{
  "id": 3,
  "nombre": "Santiago",
  "region": {
    "id": 1,
    "nombre": "Region Metropolitana"
  }
}
```

## Normal users

### GET `/users/usuarios/`
Lista usuarios no superuser.

Response (200):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12,
      "email": "cliente@mail.com",
      "nombre": "Juan",
      "apellido": "Perez",
      "direccion_entrega": "Av. Siempre Viva 123",
      "region": {
        "id": 1,
        "nombre": "Region Metropolitana"
      },
      "region_id": 1,
      "comuna": {
        "id": 3,
        "nombre": "Santiago",
        "region": {
          "id": 1,
          "nombre": "Region Metropolitana"
        }
      },
      "comuna_id": 3
    }
  ]
}
```

### POST `/users/usuarios/`

Request:
```json
{
  "email": "nuevo@mail.com",
  "nombre": "Ana",
  "apellido": "Lopez",
  "direccion_entrega": "",
  "region_id": 1,
  "comuna_id": 4,
  "password": "Password123"
}
```

Response (201):
```json
{
  "id": 15,
  "email": "nuevo@mail.com",
  "nombre": "Ana",
  "apellido": "Lopez",
  "direccion_entrega": "",
  "region": {
    "id": 1,
    "nombre": "Region Metropolitana"
  },
  "region_id": 1,
  "comuna": {
    "id": 4,
    "nombre": "Providencia",
    "region": {
      "id": 1,
      "nombre": "Region Metropolitana"
    }
  },
  "comuna_id": 4
}
```

### GET `/users/usuarios/{id}/`
### PUT `/users/usuarios/{id}/`
### PATCH `/users/usuarios/{id}/`
### DELETE `/users/usuarios/{id}/`

PUT/PATCH request ejemplo:
```json
{
  "nombre": "Ana Maria",
  "direccion_entrega": "Calle 100",
  "region_id": 2,
  "comuna_id": 8
}
```

PUT/PATCH response (200):
```json
{
  "id": 15,
  "email": "nuevo@mail.com",
  "nombre": "Ana Maria",
  "apellido": "Lopez",
  "direccion_entrega": "Calle 100",
  "region": {
    "id": 2,
    "nombre": "Region de Valparaiso"
  },
  "region_id": 2,
  "comuna": {
    "id": 8,
    "nombre": "Valparaiso",
    "region": {
      "id": 2,
      "nombre": "Region de Valparaiso"
    }
  },
  "comuna_id": 8
}
```

DELETE response (204): sin body

## Superusers

### GET `/users/superusuarios/`
### POST `/users/superusuarios/`
### GET `/users/superusuarios/{id}/`
### PUT `/users/superusuarios/{id}/`
### PATCH `/users/superusuarios/{id}/`
### DELETE `/users/superusuarios/{id}/`

POST request ejemplo:
```json
{
  "email": "admin@mail.com",
  "nombre": "Admin",
  "apellido": "Principal",
  "direccion_entrega": "",
  "region_id": 1,
  "comuna_id": 3,
  "password": "AdminPassword123",
  "is_active": true,
  "is_staff": true,
  "is_superuser": true
}
```

POST response (201):
```json
{
  "id": 1,
  "email": "admin@mail.com",
  "nombre": "Admin",
  "apellido": "Principal",
  "direccion_entrega": "",
  "region": {
    "id": 1,
    "nombre": "Region Metropolitana"
  },
  "region_id": 1,
  "comuna": {
    "id": 3,
    "nombre": "Santiago",
    "region": {
      "id": 1,
      "nombre": "Region Metropolitana"
    }
  },
  "comuna_id": 3,
  "is_active": true,
  "is_staff": true,
  "is_superuser": true
}
```

---

## Productos (`/productos/`)

## Libros

### GET `/productos/libros/`

Response (200):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "nombre": "Don Quijote",
      "slug": "don-quijote",
      "sku": "LIB-001",
      "imagen": "/media/productos/quijote.jpg",
      "descripcion": "Novela clasica",
      "descripcion_corta": "Edicion especial",
      "precio": "12990",
      "precio_referencia": "14990",
      "moneda": "CLP",
      "stock": 20,
      "gestionar_stock": true,
      "peso_kg": "0.500",
      "alto_cm": "21.00",
      "ancho_cm": "14.00",
      "largo_cm": "3.00",
      "activo": true,
      "destacado": true,
      "obra": {
        "id": 1,
        "titulo": "Don Quijote",
        "slug": "don-quijote",
        "descripcion": "Novela clasica",
        "descripcion_corta": "Obra esencial",
        "autor": {
          "id": 1,
          "nombre": "Miguel de Cervantes",
          "slug": "miguel-de-cervantes",
          "biografia": ""
        },
        "genero": {
          "id": 1,
          "nombre": "Novela",
          "slug": "novela",
          "descripcion": ""
        },
        "creado_en": "2026-03-10T01:00:00Z",
        "actualizado_en": "2026-03-10T01:00:00Z"
      },
      "autor": {
        "id": 1,
        "nombre": "Miguel de Cervantes",
        "slug": "miguel-de-cervantes",
        "biografia": ""
      },
      "genero": {
        "id": 1,
        "nombre": "Novela",
        "slug": "novela",
        "descripcion": ""
      },
      "tipo_tapa": "DURA",
      "cantidad_paginas": 860,
      "isbn": "9780000000",
      "idioma": "es",
      "anio_publicacion": 2024,
      "editorial": {
        "id": 1,
        "nombre": "Editorial X",
        "slug": "editorial-x",
        "descripcion": "",
        "sitio_web": ""
      },
      "creado_en": "2026-03-10T01:00:00Z",
      "actualizado_en": "2026-03-10T01:00:00Z"
    }
  ]
}
```

### POST `/productos/libros/`

Request:
```json
{
  "slug": "don-quijote",
  "sku": "LIB-001",
  "descripcion": "Novela clasica",
  "descripcion_corta": "Edicion especial",
  "precio": "12990",
  "precio_referencia": "14990",
  "moneda": "CLP",
  "stock": 20,
  "gestionar_stock": true,
  "activo": true,
  "destacado": false,
  "obra_id": 1,
  "editorial_id": 1,
  "tipo_tapa": "DURA",
  "cantidad_paginas": 860,
  "isbn": "9780000000",
  "idioma": "es",
  "anio_publicacion": 2024
}
```

Response (201): estructura de libro

### GET `/productos/libros/{id}/`
### PUT `/productos/libros/{id}/`
### PATCH `/productos/libros/{id}/`
### DELETE `/productos/libros/{id}/`

PUT/PATCH request ejemplo:
```json
{
  "precio": "11990",
  "stock": 30,
  "destacado": true
}
```

PUT/PATCH response (200): estructura de libro
DELETE response (204): sin body

## Recursos relacionados

### GET `/productos/autores/`
### GET `/productos/generos/`
### GET `/productos/editoriales/`
### GET `/productos/obras/`

Response (200, ejemplo `/productos/obras/`):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "titulo": "Don Quijote",
      "slug": "don-quijote",
      "descripcion": "Novela clasica",
      "descripcion_corta": "Obra esencial",
      "autor": {
        "id": 1,
        "nombre": "Miguel de Cervantes",
        "slug": "miguel-de-cervantes",
        "biografia": ""
      },
      "genero": {
        "id": 1,
        "nombre": "Novela",
        "slug": "novela",
        "descripcion": ""
      },
      "creado_en": "2026-03-10T01:00:00Z",
      "actualizado_en": "2026-03-10T01:00:00Z"
    }
  ]
}
```

### POST `/productos/autores/`
### POST `/productos/generos/`
### POST `/productos/editoriales/`
### POST `/productos/obras/`

Request ejemplo `/productos/obras/`:
```json
{
  "titulo": "Don Quijote",
  "slug": "don-quijote",
  "descripcion": "Novela clasica",
  "descripcion_corta": "Obra esencial",
  "autor_id": 1,
  "genero_id": 1
}
```

Response (201): estructura del recurso

Cada uno expone tambien:
- `GET /productos/{recurso}/{id}/`
- `PUT /productos/{recurso}/{id}/`
- `PATCH /productos/{recurso}/{id}/`
- `DELETE /productos/{recurso}/{id}/`

---

## Catalog alias (`/catalog/`)

Los mismos recursos de `productos` tambien estan publicados bajo `/catalog/` para compatibilidad ecommerce.

Endpoints principales:
- `GET /catalog/books/`
- `GET /catalog/books/{id}/`
- `GET /catalog/authors/`
- `GET /catalog/genres/`
- `GET /catalog/publishers/`
- `GET /catalog/works/`
- Admin: `POST /catalog/books/`, `PATCH /catalog/books/{id}/`, `DELETE /catalog/books/{id}/`

### Filtros (Django Filter) para libros/catalogo

Campos filtrables en `books/libros`:
- `activo`
- `destacado`
- `moneda`
- `tipo_tapa`
- `titulo`
- `autor`
- `editorial`
- `genero`

Ejemplos (equivalen para `/catalog/books/` y `/productos/libros/`):

- Solo activos:
`GET /catalog/books/?activo=true`

- Solo destacados:
`GET /catalog/books/?destacado=true`

- Solo CLP:
`GET /catalog/books/?moneda=CLP`

- Solo tapa dura:
`GET /catalog/books/?tipo_tapa=DURA`

- Por editorial:
`GET /catalog/books/?editorial=Editorial%20X`

- Por titulo:
`GET /catalog/books/?titulo=Don%20Quijote`

- Por autor:
`GET /catalog/books/?autor=Miguel%20de%20Cervantes`

- Combinando filtros:
`GET /catalog/books/?activo=true&tipo_tapa=BLANDA&autor=Cervantes&editorial=Editorial%20Y`

Notas:
- `true/false` para booleanos.
- Se puede combinar con paginacion:
`GET /catalog/books/?activo=true&page=2`

---

## Inventory (`/inventory/`)

### GET `/inventory/`
Listado de inventario por libro.

Response (200):
```json
[
  {
    "book_id": 1,
    "book_title": "Don Quijote",
    "author_name": "Miguel de Cervantes",
    "editorial_name": "Editorial X",
    "genre_name": "Novela",
    "stock": 15,
    "reserved_stock": 2,
    "available_stock": 13,
    "updated_at": "2026-03-10T02:00:00Z"
  }
]
```

### GET `/inventory/{book_id}/`

Response (200): un objeto con la misma estructura anterior.

### PATCH `/inventory/{book_id}/` (admin)

Request:
```json
{
  "stock": 20,
  "reserved_stock": 1
}
```

Response (200):
```json
{
  "book_id": 1,
  "book_title": "Don Quijote",
  "author_name": "Miguel de Cervantes",
  "editorial_name": "Editorial X",
  "genre_name": "Novela",
  "stock": 20,
  "reserved_stock": 1,
  "available_stock": 19,
  "updated_at": "2026-03-10T02:30:00Z"
}
```

### GET `/inventory/admin/monitor/` (admin)
Monitoreo agregado de inventario.

Response (200):
```json
{
  "total_stock": 120,
  "total_reserved_stock": 15,
  "low_stock_books": [
    {
      "book_id": 9,
      "book": "Libro X",
      "author": "Autor X",
      "editorial": "Editorial Z",
      "stock": 4,
      "reserved_stock": 1,
      "available_stock": 3
    }
  ]
}
```

---

## Checkout / Cart (`/checkout/carts/`)

## Estructura de respuesta de carrito

```json
{
  "id": "uuid-cart",
  "guest_token": "token-guest",
  "status": "active",
  "currency": "CLP",
  "subtotal_amount": "25000",
  "discount_amount": "1000",
  "tax_amount": "4560",
  "total_amount": "28560",
  "expires_at": "2026-03-20T01:00:00Z",
  "items": [
    {
      "id": 12,
      "book_id": 3,
      "quantity": 2,
      "unit_price_snapshot": "12500",
      "subtotal": "25000",
      "metadata_snapshot": {
        "libro_id": 3,
        "obra_id": 1,
        "obra": "Don Quijote",
        "autor": "Miguel de Cervantes",
        "genero": "Novela",
        "editorial": "Editorial X",
        "isbn": "9780000000",
        "idioma": "es",
        "tipo_tapa": "DURA"
      }
    }
  ],
  "discounts": [],
  "tax_lines": [],
  "version": 5,
  "created_at": "2026-03-09T00:00:00Z",
  "updated_at": "2026-03-09T00:05:00Z"
}
```

### POST `/checkout/carts/resolve/`
Crear/obtener carrito.

Request:
```json
{
  "guest_token": "guest-abc-123",
  "currency": "CLP"
}
```

Response (200): estructura de carrito

### GET `/checkout/carts/current/`
Obtiene carrito actual por usuario autenticado o `X-Guest-Token`.

Response (200): estructura de carrito

### POST `/checkout/carts/{cart_id}/add-item/`

Request:
```json
{
  "book_id": 3,
  "quantity": 2
}
```

Response (200): estructura de carrito

### PATCH `/checkout/carts/{cart_id}/items/{item_id}/`

Request:
```json
{
  "quantity": 4
}
```

Response (200): estructura de carrito

### DELETE `/checkout/carts/{cart_id}/items/{item_id}/`

Response (200): estructura de carrito

### POST `/checkout/carts/{cart_id}/apply-discount/`

Request:
```json
{
  "type": "percent",
  "value": "10",
  "code": "PROMO10",
  "metadata": {}
}
```

Tipos soportados:
- `percent`
- `fixed`
- `coupon`
- `qty_promo`

Response (200): estructura de carrito

### POST `/checkout/carts/{cart_id}/recalculate/`

Response (200): estructura de carrito

### POST `/checkout/carts/{cart_id}/convert/`
Convierte carrito a venta y deja carrito en estado `converted`.

Response (200): estructura de carrito con `status = converted`

---

## Orders (`/orders/`)

### GET `/orders/me/` (cliente autenticado)
Historial de compras del usuario.

Response (200):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "f9f3f1f0-2a6f-4f31-8cf8-90fd6d4aa100",
      "sale_id": "5f58e42e-703f-4d34-854f-c8590de07a28",
      "status": "pending",
      "currency": "CLP",
      "subtotal_amount": "25000",
      "discount_amount": "1000",
      "tax_amount": "4560",
      "total_amount": "28560",
      "created_at": "2026-03-10T03:00:00Z",
      "updated_at": "2026-03-10T03:00:00Z"
    }
  ]
}
```

### GET `/orders/{id}/`
Detalle de orden propia (o cualquiera si admin).

Response (200): objeto `Order`.

### GET `/orders/admin/` (admin)
Lista global de ordenes.

### PATCH `/orders/{id}/admin/status/` (admin)

Request:
```json
{
  "status": "shipped"
}
```

Response (200):
```json
{
  "id": "f9f3f1f0-2a6f-4f31-8cf8-90fd6d4aa100",
  "sale_id": "5f58e42e-703f-4d34-854f-c8590de07a28",
  "status": "shipped",
  "currency": "CLP",
  "subtotal_amount": "25000",
  "discount_amount": "1000",
  "tax_amount": "4560",
  "total_amount": "28560",
  "created_at": "2026-03-10T03:00:00Z",
  "updated_at": "2026-03-10T03:10:00Z"
}
```

Estados soportados:
- `pending`
- `paid`
- `processing`
- `shipped`
- `delivered`
- `cancelled`

---

## Shipping (`/shipping/`)

### GET `/shipping/methods/`

Response (200):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Despacho estandar",
      "price": "2990",
      "region": "RM",
      "active": true
    }
  ]
}
```

### GET `/shipping/address/` (auth)

Response (200):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "address": "Av. Siempre Viva 123",
      "city": "Santiago",
      "region": "RM",
      "country": "Chile",
      "postal_code": "8320000",
      "created_at": "2026-03-10T03:20:00Z",
      "updated_at": "2026-03-10T03:20:00Z"
    }
  ]
}
```

### POST `/shipping/address/` (auth)

Request:
```json
{
  "address": "Av. Siempre Viva 123",
  "city": "Santiago",
  "region": "RM",
  "country": "Chile",
  "postal_code": "8320000"
}
```

Response (201): objeto de direccion.

---

## Payments (`/payments/`)

### POST `/payments/create-intent/` (auth)
Crear intento de pago (mockpay o webpay sandbox).

Request:
```json
{
  "order_id": "f9f3f1f0-2a6f-4f31-8cf8-90fd6d4aa100",
  "provider": "webpay"
}
```

Response (201, webpay):
```json
{
  "payment_id": "cb1f8f7a-f761-4cca-8f4a-d009fa4280c4",
  "provider": "webpay",
  "provider_reference": "<token_ws>",
  "token": "<token_ws>",
  "redirect_url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction?token_ws=<token_ws>",
  "webpay_url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
  "amount": "28560",
  "currency": "CLP",
  "status": "pending",
  "sandbox": true
}
```

Response (201, mockpay): mantiene el formato previo con `client_secret`.

### POST `/payments/webhook/`
Actualiza estado de pago/orden segun callback del proveedor.

Request:
```json
{
  "provider_reference": "mockpay_7fb1bc73d22f4f07b626",
  "status": "paid"
}
```

Response (200):
```json
{
  "id": "cb1f8f7a-f761-4cca-8f4a-d009fa4280c4",
  "order": "f9f3f1f0-2a6f-4f31-8cf8-90fd6d4aa100",
  "provider": "mockpay",
  "status": "paid",
  "amount": "28560",
  "currency": "CLP",
  "provider_reference": "mockpay_7fb1bc73d22f4f07b626",
  "created_at": "2026-03-10T03:30:00Z",
  "updated_at": "2026-03-10T03:31:00Z"
}
```

Estados de pago:
- `pending`
- `authorized`
- `paid`
- `failed`
- `refunded`

### POST `/payments/webpay/commit/`
Confirma una transaccion Webpay con `token_ws`.

Request:
```json
{
  "token_ws": "<token_ws>"
}
```

Response (200):
```json
{
  "payment": {
    "id": "cb1f8f7a-f761-4cca-8f4a-d009fa4280c4",
    "order": "f9f3f1f0-2a6f-4f31-8cf8-90fd6d4aa100",
    "provider": "webpay",
    "status": "paid",
    "amount": "28560",
    "currency": "CLP",
    "provider_reference": "<token_ws>",
    "created_at": "2026-03-10T03:30:00Z",
    "updated_at": "2026-03-10T03:31:00Z"
  },
  "webpay": {
    "status": "AUTHORIZED",
    "response_code": 0
  }
}
```

### GET `/payments/webpay/status/?token_ws=<token_ws>`
Consulta estado directo en Webpay.

### POST `/payments/webpay/refund/`
Reversa/reembolsa un pago Webpay.

Request:
```json
{
  "token_ws": "<token_ws>",
  "amount": "28560"
}
```

---

## Ventas (`/ventas/`) - solo admin

## Estructura de venta (detalle)

```json
{
  "id": "uuid-venta",
  "cart_id": "uuid-cart",
  "user_id": 1,
  "guest_token": null,
  "status": "completed",
  "currency": "CLP",
  "subtotal_amount": "25000",
  "discount_amount": "1000",
  "tax_amount": "4560",
  "total_amount": "28560",
  "items_count": 1,
  "total_quantity": 2,
  "sold_at": "2026-03-09T00:10:00Z",
  "items": [
    {
      "id": 10,
      "libro_id": 1,
      "libro_nombre": "Don Quijote",
      "autor_nombre": "Miguel de Cervantes",
      "editorial_nombre": "Editorial X",
      "genero_nombre": "Novela",
      "isbn": "9780000000",
      "idioma": "es",
      "unit_price": "12500",
      "quantity": 2,
      "subtotal": "25000",
      "sold_at": "2026-03-09T00:10:00Z"
    }
  ]
}
```

### GET `/ventas/`

Response (200):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid-venta",
      "cart_id": "uuid-cart",
      "status": "completed",
      "currency": "CLP",
      "subtotal_amount": "25000",
      "discount_amount": "1000",
      "tax_amount": "4560",
      "total_amount": "28560",
      "items_count": 1,
      "total_quantity": 2,
      "sold_at": "2026-03-09T00:10:00Z",
      "items": []
    }
  ]
}
```

### GET `/ventas/{id}/`

Response (200): estructura de venta (detalle)

### GET `/ventas/stats/summary/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

Response (200):
```json
{
  "orders_count": 25,
  "total_subtotal": "850000",
  "total_discount": "30000",
  "total_tax": "155800",
  "total_amount": "975800",
  "total_items": 60,
  "total_quantity": 83,
  "average_order_value": "39032"
}
```

### GET `/ventas/stats/by-date/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&group_by=day|month`

Response (200):
```json
[
  {
    "period": "2026-03-09T00:00:00Z",
    "orders_count": 10,
    "total_amount": "300000",
    "total_quantity": 24
  }
]
```

### GET `/ventas/stats/by-book/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=20`

Response (200):
```json
[
  {
    "libro_id": 1,
    "libro_nombre": "Don Quijote",
    "total_quantity": 30,
    "gross_sales": "450000",
    "lines": 12,
    "authors_count": 1
  }
]
```

---

## Admin

- `GET /admin/`

---

## Errores comunes

### 400 Bad Request
Validacion de campos.

Ejemplo:
```json
{
  "comuna": [
    "La comuna debe pertenecer a la region seleccionada."
  ]
}
```

### 401 Unauthorized
Token faltante/invalido.

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
Usuario sin permisos (ej. endpoints de ventas o superusuarios).

```json
{
  "detail": "You do not have permission to perform this action."
}
```
