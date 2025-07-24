from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta, datetime, timezone
import uuid
import json
from database import get_db
from models.schemas import (
    UserBasicInfo, CompanyDetails, PaymentInfo, UserRegistration,
    UserLogin, Token, UserResponse, RegistrationStep1Response,
    RegistrationStep2Response, RegistrationCompleteResponse
)
from auth.jwt_handler import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from auth.dependencies import get_current_user

router = APIRouter()

@router.post("/register/step1", response_model=RegistrationStep1Response)
async def register_step1(basic_info: UserBasicInfo):
    """Step 1: Basic Information"""
    db = get_db()
    
    # Validate passwords match
    if basic_info.password != basic_info.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Check if user already exists
    existing_user = await db.user.find_unique(where={"email": basic_info.workEmail})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create registration session
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)  # Session expires in 1 hour
    
    # Store basic info (without password in plain text)
    basic_info_data = {
        "firstName": basic_info.firstName,
        "lastName": basic_info.lastName,
        "workEmail": basic_info.workEmail,
        "passwordHash": get_password_hash(basic_info.password)
    }
    
    await db.registrationsession.create(
        data={
            "sessionId": session_id,
            "step": 1,
            "basicInfo": json.dumps(basic_info_data),
            "expiresAt": expires_at
        }
    )
    
    return RegistrationStep1Response(
        message="Basic information saved successfully",
        step=1,
        sessionId=session_id
    )

@router.post("/register/step2", response_model=RegistrationStep2Response)
async def register_step2(company_details: CompanyDetails, session_id: str):
    """Step 2: Company Details"""
    db = get_db()
    
    # Find registration session
    session = await db.registrationsession.find_unique(
        where={"sessionId": session_id}
    )
    
    if not session or session.expiresAt < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration session"
        )
    
    # Update session with company details
    company_data = {
        "companyName": company_details.companyName,
        "companySize": company_details.companySize,
        "industry": company_details.industry,
        "hiringVolume": company_details.hiringVolume,
        "primaryHiringNeeds": company_details.primaryHiringNeeds
    }
    
    await db.registrationsession.update(
        where={"sessionId": session_id},
        data={
            "step": 2,
            "companyDetails": json.dumps(company_data)
        }
    )
    
    return RegistrationStep2Response(
        message="Company details saved successfully",
        step=2,
        sessionId=session_id
    )

@router.post("/register/step3", response_model=RegistrationCompleteResponse)
async def register_step3(payment_info: PaymentInfo, session_id: str):
    """Step 3: Payment Information & Complete Registration"""
    db = get_db()

    # ✅ Step 0: Validate terms agreement
    if not payment_info.termsAgreement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must agree to the Terms of Service and Privacy Policy"
        )

    # ✅ Step 1: Fetch session and validate
    session = await db.registrationsession.find_unique(
        where={"sessionId": session_id}
    )

    if not session or session.expiresAt < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration session"
        )

    if not session.basicInfo or not session.companyDetails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Previous registration steps not completed"
        )

    # ✅ Step 2: Parse stored session data
    basic_info = session.basicInfo
    company_details = session.companyDetails
    # Check if user already exists to avoid UniqueViolationError
    existing_user = await db.user.find_unique(where={"email": basic_info["workEmail"]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # ✅ Step 3: Create the user
    trial_ends_at = datetime.utcnow() + timedelta(days=14)  # 14-day trial

    user = await db.user.create(
        data={
            "email": basic_info["workEmail"],
            "firstName": basic_info["firstName"],
            "lastName": basic_info["lastName"],
            "password": basic_info["passwordHash"],
            "companyName": company_details["companyName"],
            "companySize": company_details["companySize"],
            "industry": company_details["industry"],
            "hiringVolume": company_details["hiringVolume"],
            "primaryHiringNeeds": company_details["primaryHiringNeeds"],
            "trialEndsAt": trial_ends_at,
            "isTrialActive": True,
            "subscriptionActive": False
        }
    )

    await db.company.create(
        data={
            "user": {  # ✅ relation required
                "connect": {
                    "id": user.id
                }
            },
            "name": company_details["companyName"],
            "companySize": company_details["companySize"],
            "industry": company_details["industry"],
            "description": "",
            "founded": None,
            "website": "",
            "email": user.email,
            "phone": "",
            "taxId": "",
            "logo": "",
            "coverImage": "",
            "primaryColor": "#10b981",
            "secondaryColor": "#3b82f6",
            "careerHeadline": "",
            "careerDescription": "",
            "remoteHiringRegions": []     # ✅ valid list
        }
    )
    # ✅ Step 4: Create default user settings
    await db.usersettings.create(
        data={
            "user": {
                "connect": {
                    "id": user.id
                }
            },
            "language": "en-US",
            "timezone": "UTC",
            "dateFormat": "MM/DD/YYYY",
            "autoSave": True,
            "emailDailyDigest": True,
            "emailNewCandidateAlerts": True,
            "emailMarketingEmails": False,
            "emailNewApplications": True,
            "pushNewApplications": True,
            "emailInterviewReminders": True,
            "pushInterviewReminders": True,
            "emailTaskDeadlines": True,
            "pushTaskDeadlines": False,
            "emailProductUpdates": True,
            "pushProductUpdates": False,
            "emailSecurityAlerts": True,
            "pushSecurityAlerts": True
        }
    )

    print("user.id:", user.id, type(user.id))
    print("featuredImages type:", type([]))

    # ✅ Step 5: Clean up session
    await db.registrationsession.delete(where={"sessionId": session_id})

    # ✅ Step 6: Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )

    user_response = UserResponse(
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
        primaryHiringNeeds=user.primaryHiringNeeds,
        createdAt=user.createdAt,
        updatedAt=user.updatedAt
    )

    token = Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

    return RegistrationCompleteResponse(
        message="Registration completed successfully! Welcome to your 14-day free trial.",
        user=user_response,
        token=token,
        trialEndsAt=trial_ends_at
    )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login user"""
    db = get_db()
    
    # Find user
    user = await db.user.find_unique(where={"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
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
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.get("/trial-status")
async def get_trial_status(current_user: UserResponse = Depends(get_current_user)):
    """Get user's trial status"""
    db = get_db()
    
    user = await db.user.find_unique(where={"id": current_user.id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    days_remaining = 0
    if user.trialEndsAt and user.isTrialActive:
        days_remaining = max(0, (user.trialEndsAt - datetime.utcnow()).days)
    
    return {
        "isTrialActive": user.isTrialActive,
        "trialEndsAt": user.trialEndsAt,
        "daysRemaining": days_remaining,
        "subscriptionActive": user.subscriptionActive
    }
