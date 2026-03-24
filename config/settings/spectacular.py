SPECTACULAR_SETTINGS = {
    "TITLE": "Delivery App API",
    "DESCRIPTION": """
## 🚚 Delivery App API Documentation

A complete authentication system for a delivery application.

### Features:
- **Users**: Registration, Login, Password Reset
- **Drivers**: Login only (added by Admin)
- **Admins**: Full dashboard access

### 🔐 Authentication
Use JWT Bearer Token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### 📱 OTP Verification
In development mode (`DEBUG=True`), the OTP code is returned in the response as `debug_otp`.
In production, OTP is sent via WhatsApp using Green API.

### 🏠 Addresses
Users can have multiple addresses with one marked as `current` for orders.
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "disableSearch": False,
    },
    "SECURITY": [{"Bearer": []}],
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User registration, login, and password management",
        },
        {"name": "Addresses", "description": "Manage user delivery addresses"},
    ],
    "SCHEMA_PATH_PREFIX": "/api/",
    "ENUM_NAME_OVERRIDES": {
        "RoleEnum": "accounts.models.User.Role",
        "GovernorateEnum": "accounts.models.User.Governorate",
        "OTPTypeEnum": "accounts.models.OTP.OTPType",
    },
    "PREPROCESSING_HOOKS": [],
    "POSTPROCESSING_HOOKS": [],
}
