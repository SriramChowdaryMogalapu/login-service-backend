# Login Service Backend

A secure, production-ready Flask-based authentication and login service backend. This service provides user authentication, authorization, token management, password reset functionality, and multi-app support.

## Features

- **User Authentication**: Email-based user registration and login
- **JWT Token Management**: Access and refresh token generation with configurable expiration
- **Secure Password Handling**: Password strength validation, hashing with Werkzeug
- **Password Reset Flow**: Secure password reset with email verification
- **Multi-App Support**: Manage multiple authorized applications with client secrets
- **Role-Based Access Control**: Super user and standard user roles
- **Email Notifications**: Automated emails for signup, password reset, and password change
- **Refresh Token Management**: Token revocation, session management with IP and device tracking
- **CORS Support**: Configured CORS for cross-origin requests
- **Audit Logging**: All authentication events are logged for security and compliance
- **Database Connection Pooling**: PostgreSQL with configurable connection pool
- **JWT Flexibility**: Tokens can be stored in cookies or headers

## Technology Stack

- **Framework**: Flask 3.0+
- **Authentication**: Flask-JWT-Extended
- **Database**: PostgreSQL (psycopg2)
- **Email**: Flask-Mail
- **Validation**: Pydantic, email-validator
- **Security**: Werkzeug
- **API Documentation**: Flasgger (Swagger)
- **CORS**: Flask-CORS
- **Environment**: python-dotenv

## Prerequisites

- Python 3.9 or higher
- PostgreSQL database
- SMTP server for email notifications (Gmail or custom)

## Installation

### 1. Clone the Repository

```bash
cd login-service-backend
```

### 2. Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/login_service

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ACCESS_TOKEN_MINUTES=15
JWT_REFRESH_TOKEN_DAYS=30
JWT_COOKIE_SECURE=false  # Set to true in production with HTTPS
JWT_COOKIE_SAMESITE=Lax
JWT_COOKIE_CSRF_PROTECT=true

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourapp.com
FROM_NAME=Login Service
EMAIL_BRAND_NAME=Login Service
EMAIL_PRIMARY_COLOR=#0F766E

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# Database Connection Pool
DB_POOL_MIN_CONN=1
DB_POOL_MAX_CONN=10

# Password Reset
PASSWORD_RESET_BASE_URL=https://yourapp.com/reset-password
```

## Database Setup

### Create PostgreSQL Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    super_user BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authorized apps table
CREATE TABLE authorized_apps (
    app_name VARCHAR(100) PRIMARY KEY,
    client_secret_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    app_name VARCHAR(100) NOT NULL REFERENCES authorized_apps(app_name),
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    device_info TEXT,
    is_revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens table
CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Running the Application

### Development Server

```bash
python app.py
```

The server will start at `http://localhost:5000`

### Production Server

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

## API Endpoints

### Authentication Endpoints

#### 1. **Signup (Register New User)**

```
POST /auth/signup
Content-Type: application/json

{
    "app_name": "MyApp",
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "super_user": false
}

Response: 201 Created
{
    "message": "Signup successful",
    "user_id": "uuid",
    "refresh_token": "jwt_token"
}
```

#### 2. **Login**

```
POST /auth/login
Content-Type: application/json

{
    "app_name": "MyApp",
    "email": "user@example.com",
    "password": "SecurePassword123!"
}

Response: 200 OK
{
    "access_token": "jwt_token",
    "refresh_token": "jwt_token",
    "user_id": "uuid",
    "email": "user@example.com"
}
```

#### 3. **Refresh Access Token**

```
POST /auth/refresh
Authorization: Bearer <refresh_token>

Response: 200 OK
{
    "access_token": "new_jwt_token"
}
```

#### 4. **Logout**

```
POST /auth/logout
Authorization: Bearer <access_token>

Response: 200 OK
{
    "message": "Logout successful"
}
```

#### 5. **Request Password Reset**

```
POST /auth/request-password-reset
Content-Type: application/json

{
    "app_name": "MyApp",
    "email": "user@example.com"
}

Response: 200 OK
{
    "message": "Password reset email sent"
}
```

#### 6. **Reset Password**

```
POST /auth/reset-password
Content-Type: application/json

{
    "app_name": "MyApp",
    "reset_token": "token_from_email",
    "new_password": "NewSecurePassword123!"
}

Response: 200 OK
{
    "message": "Password reset successful"
}
```

#### 7. **Get Current User**

```
GET /auth/me
Authorization: Bearer <access_token>

Response: 200 OK
{
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "User Name",
    "super_user": false
}
```

#### 8. **Update MPIN**

```
PUT /auth/mpin
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "mpin": "1234"
}

Response: 200 OK
{
    "message": "MPIN updated successfully"
}
```

### Admin Endpoints

#### 1. **Create Authorized App**

```
POST /auth/app/authorize
Content-Type: application/json

{
    "app_name": "MyApp"
}

Response: 201 Created
{
    "app_name": "MyApp",
    "client_secret": "secret_key"
}
```

#### 2. **Promote User to Super User**

```
PUT /auth/promote-super-user
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "user_id": "uuid"
}

Response: 200 OK
{
    "message": "User promoted to super user"
}
```

## Security Features

- **Password Strength Validation**: Enforces strong passwords
- **Password Hashing**: Werkzeug-based secure hashing
- **JWT Protection**: Signed tokens with expiration
- **Token Revocation**: Refresh tokens can be revoked
- **CSRF Protection**: JWT CSRF protection enabled
- **Secure Cookies**: Configurable secure cookie flags
- **Audit Logging**: All authentication events logged
- **Email Verification**: Passwords reset via email verification
- **Session Management**: IP and device tracking for tokens
- **Rate Limiting**: Ready for integration with Flask-Limiter

## Project Structure

```
app/
├── __init__.py              # Flask app factory
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration settings
├── db.py                    # Database connection management
├── extensions.py            # Flask extensions initialization
├── middleware/
│   └── app_auth.py          # Authentication middleware
├── models/
│   └── schemas.py           # Request validation schemas
├── routes/
│   └── auth.py              # Authentication routes
├── services/
│   └── auth_service.py      # Business logic for auth
└── utils/
    ├── audit.py             # Audit logging
    ├── email_service.py     # Email notifications
    └── security.py          # Security utilities
```

## Configuration

### Environment-Specific Settings

The application supports multiple environments:

- **development**: Debug mode enabled, relaxed security
- **production**: Debug disabled, strict security settings

Toggle via `FLASK_ENV` environment variable.

### JWT Configuration

- **Access Token Expiry**: Configurable via `JWT_ACCESS_TOKEN_MINUTES` (default: 15 minutes)
- **Refresh Token Expiry**: Configurable via `JWT_REFRESH_TOKEN_DAYS` (default: 30 days)
- **Token Location**: Can be stored in cookies or headers via `JWT_TOKEN_LOCATION`
- **CSRF Protection**: Enabled by default for cookie-based tokens

## Email Templates

The service sends transactional emails for:

1. **Signup Confirmation**: Welcome email with verification
2. **Password Reset**: Secure reset link with expiration
3. **Password Change**: Confirmation of password update

Customize email templates in `utils/email_service.py`

## Monitoring & Logging

All authentication events are logged to the `audit_logs` table including:

- User login/logout
- Password changes
- Token generation/revocation
- Failed authentication attempts
- Authorization changes

Access audit logs programmatically or via your database queries.

## Error Handling

The API returns standardized error responses:

```json
{
  "error": "Error message",
  "status_code": 400
}
```

Common status codes:

- `400`: Bad request (validation errors)
- `401`: Unauthorized (authentication failed)
- `403`: Forbidden (insufficient permissions)
- `409`: Conflict (duplicate email)
- `500`: Server error

## Testing

Run tests (when added):

```bash
pytest tests/
```

## Deployment

### Docker

Create a `Dockerfile` for containerized deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:create_app()"]
```

### Cloud Deployment

The service can be deployed to:

- AWS (Lambda, EC2, ECS)
- Azure (App Service, Container Instances)
- Google Cloud (Cloud Run, App Engine)
- Heroku
- DigitalOcean

## Best Practices

1. **Environment Variables**: Never commit `.env` files; use `.env.example` template
2. **HTTPS Only**: Always use HTTPS in production
3. **JWT Secret**: Use strong, randomly generated secrets
4. **Database Backups**: Regular backups of PostgreSQL database
5. **Rate Limiting**: Implement rate limiting on auth endpoints
6. **Monitoring**: Set up logging and monitoring in production
7. **CORS**: Strictly configure allowed origins
8. **Password Reset**: Tokens expire after a set time (typically 24 hours)

## Troubleshooting

### Common Issues

1. **Database Connection Failed**: Verify `DATABASE_URL` and PostgreSQL is running
2. **Email Not Sending**: Check SMTP credentials and `MAIL_SERVER` configuration
3. **JWT Validation Failed**: Ensure `JWT_SECRET_KEY` is consistent across instances
4. **CORS Errors**: Add frontend URL to `CORS_ORIGINS` in environment variables

## License

[Add your license here]

## Support

For issues and questions, please open an issue in the repository.

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

---

**Version**: 1.0.0  
**Last Updated**: March 2026
