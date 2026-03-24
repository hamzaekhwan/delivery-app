# Driver Completed Orders Count API

## Endpoint

```
GET /orders/driver/orders/completed_count/
```

## Authentication

```
Authorization: Bearer <token>
```

## Response

```json
{
  "orders_count": 42
}
```

## Example (Dart)

```dart
final response = await http.get(
  Uri.parse('$baseUrl/orders/driver/orders/completed_count/'),
  headers: {'Authorization': 'Bearer $token'},
);

final data = jsonDecode(response.body);
final int ordersCount = data['orders_count'];
```

## Notes

- للسائق المسجّل فقط
- يعيد عدد الطلبات بحالة `DELIVERED` فقط
