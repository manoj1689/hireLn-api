from fastapi import APIRouter, HTTPException, status, Depends
from prisma import Json
from database import get_db
from models.schemas import (
    CompanyResponse, CompanyCreate, CompanyUpdate,
    CompanyLocationResponse, CompanyLocationCreate, CompanyLocationUpdate,
    TeamMemberResponse, TeamMemberInvite, TeamMemberUpdate,
    SubscriptionResponse, SubscriptionUpdate,
    PaymentMethodResponse, PaymentMethodCreate, PaymentMethodUpdate,
    BillingAddressResponse, BillingAddressCreate, BillingAddressUpdate,
    InvoiceResponse, PlanUsage, UserResponse
)
from auth.dependencies import get_current_user
from typing import List
import json

router = APIRouter()

# Company Profile Endpoints
@router.get("/profile", response_model=CompanyResponse)
async def get_company_profile(current_user: UserResponse = Depends(get_current_user)):
    """Get company profile"""
    db = get_db()
    
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        # Create default company profile if it doesn't exist
        company = await db.company.create(
            data={
                "userId": current_user.id,
                "name": current_user.companyName or "My Company",
                "industry": current_user.industry,
                "companySize": current_user.companySize,
                "socialMedia": {},
                "featuredImages": [],
                "remoteHiringRegions": []
            }
        )
    
    return CompanyResponse(
        id=company.id,
        userId=company.userId,
        name=company.name,
        description=company.description,
        industry=company.industry,
        founded=company.founded,
        companySize=company.companySize,
        website=company.website,
        email=company.email,
        phone=company.phone,
        taxId=company.taxId,
        logo=company.logo,
        coverImage=company.coverImage,
        primaryColor=company.primaryColor,
        secondaryColor=company.secondaryColor,
        careerHeadline=company.careerHeadline,
        careerDescription=company.careerDescription,
        featuredImages=company.featuredImages or [],
        socialMedia=company.socialMedia,
        remoteWorkPolicy=company.remoteWorkPolicy,
        remoteHiringRegions=company.remoteHiringRegions or [],
        createdAt=company.createdAt,
        updatedAt=company.updatedAt
    )

@router.put("/profile", response_model=CompanyResponse)
async def update_company_profile(
    company_update: CompanyUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update company profile"""
    db = get_db()
    
    # Ensure company exists
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company profile not found"
        )
    

    update_data = {}
    print("featuredImages:", update_data.get("featuredImages"))
    print("socialMedia:", update_data.get("socialMedia"))
    print(type(update_data.get("featuredImages")))
    print(type(update_data.get("socialMedia")))
    if company_update.name is not None:
        update_data["name"] = company_update.name
    if company_update.description is not None:
        update_data["description"] = company_update.description
    if company_update.industry is not None:
        update_data["industry"] = company_update.industry
    if company_update.founded is not None:
        update_data["founded"] = company_update.founded
    if company_update.companySize is not None:
        update_data["companySize"] = company_update.companySize
    if company_update.website is not None:
        update_data["website"] = company_update.website
    if company_update.email is not None:
        update_data["email"] = company_update.email
    if company_update.phone is not None:
        update_data["phone"] = company_update.phone
    if company_update.taxId is not None:
        update_data["taxId"] = company_update.taxId
    if company_update.logo is not None:
        update_data["logo"] = company_update.logo
    if company_update.coverImage is not None:
        update_data["coverImage"] = company_update.coverImage
    if company_update.primaryColor is not None:
        update_data["primaryColor"] = company_update.primaryColor
    if company_update.secondaryColor is not None:
        update_data["secondaryColor"] = company_update.secondaryColor
    if company_update.careerHeadline is not None:
        update_data["careerHeadline"] = company_update.careerHeadline
    if company_update.careerDescription is not None:
        update_data["careerDescription"] = company_update.careerDescription
   

    if company_update.featuredImages is not None:
       update_data["featuredImages"] = Json([img.dict() for img in company_update.featuredImages])

    if company_update.socialMedia is not None:
        update_data["socialMedia"] = Json(company_update.socialMedia.dict())
    if company_update.remoteWorkPolicy is not None:
        update_data["remoteWorkPolicy"] = company_update.remoteWorkPolicy
    if company_update.remoteHiringRegions is not None:
        update_data["remoteHiringRegions"] = company_update.remoteHiringRegions
    
    updated_company = await db.company.update(
        where={"userId": current_user.id},
        data=update_data
    )
    
    return CompanyResponse(
        id=updated_company.id,
        userId=updated_company.userId,
        name=updated_company.name,
        description=updated_company.description,
        industry=updated_company.industry,
        founded=updated_company.founded,
        companySize=updated_company.companySize,
        website=updated_company.website,
        email=updated_company.email,
        phone=updated_company.phone,
        taxId=updated_company.taxId,
        logo=updated_company.logo,
        coverImage=updated_company.coverImage,
        primaryColor=updated_company.primaryColor,
        secondaryColor=updated_company.secondaryColor,
        careerHeadline=updated_company.careerHeadline,
        careerDescription=updated_company.careerDescription,
        featuredImages=updated_company.featuredImages or [],
        socialMedia=updated_company.socialMedia,
        remoteWorkPolicy=updated_company.remoteWorkPolicy,
        remoteHiringRegions=updated_company.remoteHiringRegions or [],
        createdAt=updated_company.createdAt,
        updatedAt=updated_company.updatedAt
    )

# Company Locations Endpoints
@router.get("/locations", response_model=List[CompanyLocationResponse])
async def get_company_locations(current_user: UserResponse = Depends(get_current_user)):
    """Get all company locations"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    locations = await db.companylocation.find_many(
        where={"companyId": company.id},
        # order_by={"isHeadquarters": "desc"}
    )
    
    return [
        CompanyLocationResponse(
            id=location.id,
            companyId=location.companyId,
            name=location.name,
            type=location.type,
            address=location.address,
            city=location.city,
            state=location.state,
            country=location.country,
            zipCode=location.zipCode,
            phone=location.phone,
            email=location.email,
            isHeadquarters=location.isHeadquarters,
            createdAt=location.createdAt,
            updatedAt=location.updatedAt
        )
        for location in locations
    ]

@router.post("/locations", response_model=CompanyLocationResponse)
async def create_company_location(
    location_data: CompanyLocationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new company location"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # If this is set as headquarters, remove headquarters flag from other locations
    if location_data.isHeadquarters:
        await db.companylocation.update_many(
            where={"companyId": company.id},
            data={"isHeadquarters": False}
        )
    
    location = await db.companylocation.create(
        data={
            "companyId": company.id,
            "name": location_data.name,
            "type": location_data.type,
            "address": location_data.address,
            "city": location_data.city,
            "state": location_data.state,
            "country": location_data.country,
            "zipCode": location_data.zipCode,
            "phone": location_data.phone,
            "email": location_data.email,
            "isHeadquarters": location_data.isHeadquarters
        }
    )
    
    return CompanyLocationResponse(
        id=location.id,
        companyId=location.companyId,
        name=location.name,
        type=location.type,
        address=location.address,
        city=location.city,
        state=location.state,
        country=location.country,
        zipCode=location.zipCode,
        phone=location.phone,
        email=location.email,
        isHeadquarters=location.isHeadquarters,
        createdAt=location.createdAt,
        updatedAt=location.updatedAt
    )

@router.put("/locations/{location_id}", response_model=CompanyLocationResponse)
async def update_company_location(
    location_id: str,
    location_update: CompanyLocationUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update a company location"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if location exists and belongs to the company
    location = await db.companylocation.find_unique(
        where={"id": location_id}
    )
    
    if not location or location.companyId != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # If this is set as headquarters, remove headquarters flag from other locations
    if location_update.isHeadquarters:
        await db.companylocation.update_many(
            where={"companyId": company.id, "id": {"not": location_id}},
            data={"isHeadquarters": False}
        )
    
    update_data = {}
    if location_update.name is not None:
        update_data["name"] = location_update.name
    if location_update.type is not None:
        update_data["type"] = location_update.type
    if location_update.address is not None:
        update_data["address"] = location_update.address
    if location_update.city is not None:
        update_data["city"] = location_update.city
    if location_update.state is not None:
        update_data["state"] = location_update.state
    if location_update.country is not None:
        update_data["country"] = location_update.country
    if location_update.zipCode is not None:
        update_data["zipCode"] = location_update.zipCode
    if location_update.phone is not None:
        update_data["phone"] = location_update.phone
    if location_update.email is not None:
        update_data["email"] = location_update.email
    if location_update.isHeadquarters is not None:
        update_data["isHeadquarters"] = location_update.isHeadquarters
    
    updated_location = await db.companylocation.update(
        where={"id": location_id},
        data=update_data
    )
    
    return CompanyLocationResponse(
        id=updated_location.id,
        companyId=updated_location.companyId,
        name=updated_location.name,
        type=updated_location.type,
        address=updated_location.address,
        city=updated_location.city,
        state=updated_location.state,
        country=updated_location.country,
        zipCode=updated_location.zipCode,
        phone=updated_location.phone,
        email=updated_location.email,
        isHeadquarters=updated_location.isHeadquarters,
        createdAt=updated_location.createdAt,
        updatedAt=updated_location.updatedAt
    )

@router.delete("/locations/{location_id}")
async def delete_company_location(
    location_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete a company location"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if location exists and belongs to the company
    location = await db.companylocation.find_unique(
        where={"id": location_id}
    )
    
    if not location or location.companyId != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    await db.companylocation.delete(where={"id": location_id})
    
    return {"message": "Location deleted successfully"}

# Team Members Endpoints
@router.get("/team", response_model=List[TeamMemberResponse])
async def get_team_members(current_user: UserResponse = Depends(get_current_user)):
    """Get all team members"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    team_members = await db.teammember.find_many(
        where={"companyId": company.id},
        # order_by={"createdAt": "desc"}
    )
    
    return [
        TeamMemberResponse(
            id=member.id,
            companyId=member.companyId,
            name=member.name,
            email=member.email,
            role=member.role,
            department=member.department,
            phone=member.phone,
            avatar=member.avatar,
            status=member.status,
            accessLevel=member.accessLevel,
            invitedAt=member.invitedAt,
            joinedAt=member.joinedAt,
            invitedBy=member.invitedBy,
            createdAt=member.createdAt,
            updatedAt=member.updatedAt
        )
        for member in team_members
    ]

@router.post("/team/invite", response_model=TeamMemberResponse)
async def invite_team_member(
    invite_data: TeamMemberInvite,
    current_user: UserResponse = Depends(get_current_user)
):
    """Invite a new team member"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if email already exists in the company
    existing_member = await db.teammember.find_unique(
        where={
            "email_companyId": {
                "email": invite_data.email,
                "companyId": company.id
            }
        }
    )
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team member with this email already exists"
        )
    
    from datetime import datetime
    
    team_member = await db.teammember.create(
        data={
            "companyId": company.id,
            "name": invite_data.name,
            "email": invite_data.email,
            "role": invite_data.role,
            "department": invite_data.department,
            "accessLevel": invite_data.accessLevel,
            "status": "invited",
            "invitedAt": datetime.utcnow(),
            "invitedBy": current_user.id
        }
    )
    
    # TODO: Send invitation email here
    
    return TeamMemberResponse(
        id=team_member.id,
        companyId=team_member.companyId,
        name=team_member.name,
        email=team_member.email,
        role=team_member.role,
        department=team_member.department,
        phone=team_member.phone,
        avatar=team_member.avatar,
        status=team_member.status,
        accessLevel=team_member.accessLevel,
        invitedAt=team_member.invitedAt,
        joinedAt=team_member.joinedAt,
        invitedBy=team_member.invitedBy,
        createdAt=team_member.createdAt,
        updatedAt=team_member.updatedAt
    )

@router.put("/team/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: str,
    member_update: TeamMemberUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update a team member"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if member exists and belongs to the company
    member = await db.teammember.find_unique(
        where={"id": member_id}
    )
    
    if not member or member.companyId != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    update_data = {}
    if member_update.name is not None:
        update_data["name"] = member_update.name
    if member_update.role is not None:
        update_data["role"] = member_update.role
    if member_update.department is not None:
        update_data["department"] = member_update.department
    if member_update.phone is not None:
        update_data["phone"] = member_update.phone
    if member_update.avatar is not None:
        update_data["avatar"] = member_update.avatar
    if member_update.status is not None:
        update_data["status"] = member_update.status
    if member_update.accessLevel is not None:
        update_data["accessLevel"] = member_update.accessLevel
    
    updated_member = await db.teammember.update(
        where={"id": member_id},
        data=update_data
    )
    
    return TeamMemberResponse(
        id=updated_member.id,
        companyId=updated_member.companyId,
        name=updated_member.name,
        email=updated_member.email,
        role=updated_member.role,
        department=updated_member.department,
        phone=updated_member.phone,
        avatar=updated_member.avatar,
        status=updated_member.status,
        accessLevel=updated_member.accessLevel,
        invitedAt=updated_member.invitedAt,
        joinedAt=updated_member.joinedAt,
        invitedBy=updated_member.invitedBy,
        createdAt=updated_member.createdAt,
        updatedAt=updated_member.updatedAt
    )

@router.delete("/team/{member_id}")
async def delete_team_member(
    member_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete a team member"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if member exists and belongs to the company
    member = await db.teammember.find_unique(
        where={"id": member_id}
    )
    
    if not member or member.companyId != company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    await db.teammember.delete(where={"id": member_id})
    
    return {"message": "Team member removed successfully"}

# Subscription & Billing Endpoints
@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(current_user: UserResponse = Depends(get_current_user)):
    """Get current subscription"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    subscription = await db.subscription.find_unique(
        where={"companyId": company.id}
    )
    
    if not subscription:
        # Create default subscription if it doesn't exist
        from datetime import datetime, timedelta
        from decimal import Decimal
        
        subscription = await db.subscription.create(
            data={
                "companyId": company.id,
                "planName": "Business Plan",
                "planPrice": Decimal("199.00"),
                "billingCycle": "monthly",
                "status": "active",
                "currentPeriodStart": datetime.utcnow(),
                "currentPeriodEnd": datetime.utcnow() + timedelta(days=30),
                "teamMemberLimit": 25,
                "aiCreditsLimit": 1000,
                "storageLimit": 10
            }
        )
    
    return SubscriptionResponse(
        id=subscription.id,
        companyId=subscription.companyId,
        planName=subscription.planName,
        planPrice=subscription.planPrice,
        billingCycle=subscription.billingCycle,
        status=subscription.status,
        currentPeriodStart=subscription.currentPeriodStart,
        currentPeriodEnd=subscription.currentPeriodEnd,
        cancelAtPeriodEnd=subscription.cancelAtPeriodEnd,
        stripeSubscriptionId=subscription.stripeSubscriptionId,
        stripeCustomerId=subscription.stripeCustomerId,
        teamMemberLimit=subscription.teamMemberLimit,
        aiCreditsLimit=subscription.aiCreditsLimit,
        storageLimit=subscription.storageLimit,
        createdAt=subscription.createdAt,
        updatedAt=subscription.updatedAt
    )

@router.get("/subscription/usage", response_model=PlanUsage)
async def get_plan_usage(current_user: UserResponse = Depends(get_current_user)):
    """Get current plan usage"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Get subscription
    subscription = await db.subscription.find_unique(
        where={"companyId": company.id}
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Count team members
    team_member_count = await db.teammember.count(
        where={"companyId": company.id, "status": "active"}
    )
    
    # Mock AI credits and storage usage (replace with actual logic)
    ai_credits_used = 873  # This should come from actual usage tracking
    storage_used = 4.2  # This should come from actual storage calculation
    
    return PlanUsage(
        teamMembers={
            "current": team_member_count,
            "limit": subscription.teamMemberLimit
        },
        aiCredits={
            "current": ai_credits_used,
            "limit": subscription.aiCreditsLimit
        },
        storage={
            "current": storage_used,
            "limit": subscription.storageLimit,
            "unit": "GB"
        }
    )

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(current_user: UserResponse = Depends(get_current_user)):
    """Get all payment methods"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    payment_methods = await db.paymentmethod.find_many(
        where={"companyId": company.id},
        # order_by={"isDefault": "desc"}
    )
    
    return [
        PaymentMethodResponse(
            id=method.id,
            companyId=method.companyId,
            type=method.type,
            last4=method.last4,
            brand=method.brand,
            expiryMonth=method.expiryMonth,
            expiryYear=method.expiryYear,
            isDefault=method.isDefault,
            stripePaymentMethodId=method.stripePaymentMethodId,
            createdAt=method.createdAt,
            updatedAt=method.updatedAt
        )
        for method in payment_methods
    ]

@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    payment_method: PaymentMethodCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Add a new payment method"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # If this is set as default, remove default flag from other payment methods
    if payment_method.isDefault:
        await db.paymentmethod.update_many(
            where={"companyId": company.id},
            data={"isDefault": False}
        )
    
    new_payment_method = await db.paymentmethod.create(
        data={
            "companyId": company.id,
            "type": payment_method.type,
            "last4": payment_method.last4,
            "brand": payment_method.brand,
            "expiryMonth": payment_method.expiryMonth,
            "expiryYear": payment_method.expiryYear,
            "isDefault": payment_method.isDefault,
            "stripePaymentMethodId": payment_method.stripePaymentMethodId
        }
    )
    
    return PaymentMethodResponse(
        id=new_payment_method.id,
        companyId=new_payment_method.companyId,
        type=new_payment_method.type,
        last4=new_payment_method.last4,
        brand=new_payment_method.brand,
        expiryMonth=new_payment_method.expiryMonth,
        expiryYear=new_payment_method.expiryYear,
        isDefault=new_payment_method.isDefault,
        stripePaymentMethodId=new_payment_method.stripePaymentMethodId,
        createdAt=new_payment_method.createdAt,
        updatedAt=new_payment_method.updatedAt
    )

@router.get("/billing-address", response_model=BillingAddressResponse)
async def get_billing_address(current_user: UserResponse = Depends(get_current_user)):
    """Get billing address"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    billing_address = await db.billingaddress.find_unique(
        where={"companyId": company.id}
    )
    
    if not billing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing address not found"
        )
    
    return BillingAddressResponse(
        id=billing_address.id,
        companyId=billing_address.companyId,
        contactName=billing_address.contactName,
        contactEmail=billing_address.contactEmail,
        contactPhone=billing_address.contactPhone,
        companyName=billing_address.companyName,
        addressLine1=billing_address.addressLine1,
        addressLine2=billing_address.addressLine2,
        city=billing_address.city,
        state=billing_address.state,
        zipCode=billing_address.zipCode,
        country=billing_address.country,
        createdAt=billing_address.createdAt,
        updatedAt=billing_address.updatedAt
    )

@router.put("/billing-address", response_model=BillingAddressResponse)
async def update_billing_address(
    billing_update: BillingAddressUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update billing address"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Check if billing address exists
    billing_address = await db.billingaddress.find_unique(
        where={"companyId": company.id}
    )
    
    update_data = {}
    if billing_update.contactName is not None:
        update_data["contactName"] = billing_update.contactName
    if billing_update.contactEmail is not None:
        update_data["contactEmail"] = billing_update.contactEmail
    if billing_update.contactPhone is not None:
        update_data["contactPhone"] = billing_update.contactPhone
    if billing_update.companyName is not None:
        update_data["companyName"] = billing_update.companyName
    if billing_update.addressLine1 is not None:
        update_data["addressLine1"] = billing_update.addressLine1
    if billing_update.addressLine2 is not None:
        update_data["addressLine2"] = billing_update.addressLine2
    if billing_update.city is not None:
        update_data["city"] = billing_update.city
    if billing_update.state is not None:
        update_data["state"] = billing_update.state
    if billing_update.zipCode is not None:
        update_data["zipCode"] = billing_update.zipCode
    if billing_update.country is not None:
        update_data["country"] = billing_update.country
    
    if billing_address:
        # Update existing
        updated_billing = await db.billingaddress.update(
            where={"companyId": company.id},
            data=update_data
        )
    else:
        # Create new if doesn't exist
        updated_billing = await db.billingaddress.create(
            data={
                "companyId": company.id,
                **update_data
            }
        )
    
    return BillingAddressResponse(
        id=updated_billing.id,
        companyId=updated_billing.companyId,
        contactName=updated_billing.contactName,
        contactEmail=updated_billing.contactEmail,
        contactPhone=updated_billing.contactPhone,
        companyName=updated_billing.companyName,
        addressLine1=updated_billing.addressLine1,
        addressLine2=updated_billing.addressLine2,
        city=updated_billing.city,
        state=updated_billing.state,
        zipCode=updated_billing.zipCode,
        country=updated_billing.country,
        createdAt=updated_billing.createdAt,
        updatedAt=updated_billing.updatedAt
    )

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(current_user: UserResponse = Depends(get_current_user)):
    """Get billing history/invoices"""
    db = get_db()
    
    # Get company first
    company = await db.company.find_unique(
        where={"userId": current_user.id}
    )
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    invoices = await db.invoice.find_many(
        where={"companyId": company.id},
        # order_by={"createdAt": "desc"}
    )
    
    return [
        InvoiceResponse(
            id=invoice.id,
            companyId=invoice.companyId,
            invoiceNumber=invoice.invoiceNumber,
            amount=invoice.amount,
            currency=invoice.currency,
            status=invoice.status,
            dueDate=invoice.dueDate,
            paidAt=invoice.paidAt,
            stripeInvoiceId=invoice.stripeInvoiceId,
            downloadUrl=invoice.downloadUrl,
            createdAt=invoice.createdAt,
            updatedAt=invoice.updatedAt
        )
        for invoice in invoices
    ]
