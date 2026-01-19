"""
B2B Authentication endpoints for business users
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from app.core import logger, settings
from app.db import mongodb_manager

router = APIRouter(prefix="/b2b/auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    phone: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    B2B Login endpoint for business users
    
    - **email**: Business user email
    - **password**: User password
    
    Returns JWT token and user info
    """
    try:
        logger.info(f"🔐 B2B Login attempt: {request.email}")
        
        # Get business users collection
        users_col = mongodb_manager.get_collection("business_users")
        if users_col is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )
        
        # Find user by email
        user = users_col.find_one({"email": request.email})
        
        if not user:
            logger.warning(f"❌ User not found: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(request.password, user.get("password_hash", "")):
            logger.warning(f"❌ Invalid password for: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": str(user["_id"]),
                "email": user["email"],
                "type": "business"
            }
        )
        
        # Update last login
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Prepare user data (remove sensitive info)
        user_data = {
            "id": str(user["_id"]),
            "email": user["email"],
            "business_name": user.get("business_name", ""),
            "phone": user.get("phone"),
            "created_at": user.get("created_at"),
            "role": user.get("role", "business_user")
        }
        
        logger.info(f"✅ B2B Login successful: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ B2B Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """
    B2B Register endpoint for new business users
    
    - **email**: Business email
    - **password**: Password (will be hashed)
    - **business_name**: Name of the business
    - **phone**: Contact phone (optional)
    
    Returns JWT token and user info
    """
    try:
        logger.info(f"📝 B2B Register attempt: {request.email}")
        
        # Get business users collection
        users_col = mongodb_manager.get_collection("business_users")
        if users_col is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )
        
        # Check if user already exists
        existing_user = users_col.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = get_password_hash(request.password)
        
        # Create new user
        new_user = {
            "email": request.email,
            "password_hash": password_hash,
            "business_name": request.business_name,
            "phone": request.phone,
            "role": "business_user",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = users_col.insert_one(new_user)
        user_id = str(result.inserted_id)
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": request.email,
                "type": "business"
            }
        )
        
        # Prepare user data
        user_data = {
            "id": user_id,
            "email": request.email,
            "business_name": request.business_name,
            "phone": request.phone,
            "created_at": new_user["created_at"],
            "role": "business_user"
        }
        
        logger.info(f"✅ B2B Registration successful: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ B2B Register error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me")
async def get_current_user():
    """Get current authenticated business user (requires JWT token)"""
    # TODO: Implement JWT token verification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token verification not implemented yet"
    )
