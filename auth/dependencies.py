from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional, Union
from datetime import datetime, timezone
import logging
import json
import re
from pydantic import ValidationError

from auth.jwt_handler import verify_token
from database import get_db
from models.schemas import UserResponse, Question, InterviewQuestionsFromJobCandidateRequest, InterviewQuestionsFromJobCandidateResponse
from prisma import Prisma

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 for user login - make it optional for mixed auth scenarios
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ✅ Get the current user using JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    user = await db.user.find_unique(where={"id": user_id})

    if not user:
        raise credentials_exception

    return UserResponse(
        id=user.id,
        email=user.email,
        firstName=user.firstName,
        lastName=user.lastName,
        name=f"{user.firstName} {user.lastName}",
        avatar=user.avatar,
        role=user.role,
        companyName=user.companyName,
        companySize=user.companySize,
        industry=user.industry,
        hiringVolume=user.hiringVolume,
        primaryHiringNeeds=user.primaryHiringNeeds or [],
        createdAt=user.createdAt,
        updatedAt=user.updatedAt
    )

# ✅ Optional: Require admin users
async def get_admin_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user



# ✅ Get the current user using JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    user = await db.user.find_unique(where={"id": user_id})

    if not user:
        raise credentials_exception

    return UserResponse(
        id=user.id,
        email=user.email,
        firstName=user.firstName,
        lastName=user.lastName,
        name=f"{user.firstName} {user.lastName}",
        avatar=user.avatar,
        role=user.role,
        companyName=user.companyName,
        companySize=user.companySize,
        industry=user.industry,
        hiringVolume=user.hiringVolume,
        primaryHiringNeeds=user.primaryHiringNeeds or [],
        createdAt=user.createdAt,
        updatedAt=user.updatedAt
    )

# ✅ Admin user dependency
async def get_admin_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# ✅ Interview token validation - token only
async def verify_interview_token(token: str) -> dict:
    """Verify interview token and return interview data"""
    db = get_db()
    
    # Find interview by joinToken only
    interview = await db.interview.find_first(
        where={"joinToken": token},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True,
                    "user": True
                }
            }
        }
    )

    if not interview:
        raise HTTPException(status_code=401, detail="Invalid interview token")

    # Check token expiry
    if interview.tokenExpiry:
        current_time = datetime.now(timezone.utc)
        token_expiry = interview.tokenExpiry
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        if current_time > token_expiry:
            raise HTTPException(status_code=401, detail="Interview token has expired")

    return {
        "interview": interview,
        "candidate": interview.candidate,
        "job": interview.application.job,
        "recruiter": interview.application.user
    }

# ✅ Combined user OR interview token auth - token only
async def get_user_or_interview_auth(
    user_token: Optional[str] = Depends(oauth2_scheme),
    interview_token: Optional[str] = Header(None, alias="X-Interview-Token"),
) -> Union[UserResponse, dict]:
    """
    Authenticate using either:
    1. Authorization: Bearer <jwt_token> header
    2. X-Interview-Token: <interview_token> header
    """
    
    # Priority 1: Interview token auth
    if interview_token:
        try:
            logger.info("🔐 Attempting interview token auth")
            result = await verify_interview_token(interview_token)
            logger.info("✅ Interview token verified")
            return result
        except HTTPException as e:
            logger.warning(f"❌ Interview token failed: {e.detail}")
            # Don't raise here, try user token next

    # Priority 2: User token auth
    if user_token:
        try:
            logger.info("🔐 Attempting user token auth")
            result = await get_current_user(user_token)
            logger.info("✅ User token verified")
            return result
        except HTTPException as e:
            logger.warning(f"❌ User token failed: {e.detail}")

    logger.error("❌ No valid token provided")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either Authorization Bearer token or X-Interview-Token header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ✅ Interview token only auth
async def get_interview_auth_only(
    interview_token: str = Header(..., alias="X-Interview-Token")
) -> dict:
    """Validate interview token only - for public interview access"""
    try:
        logger.info("🔐 Validating interview token")
        result = await verify_interview_token(interview_token)
        logger.info("✅ Interview token verified")
        return result
    except HTTPException as e:
        logger.error(f"❌ Interview token validation failed: {e.detail}")
        raise e
