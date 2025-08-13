from fastapi import APIRouter, HTTPException, status, Depends
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import (
    UserSettingsResponse, UserSettingsUpdate, UserSettingsCreate,
    GeneralSettingsUpdate, EmailSettingsUpdate, NotificationSettingsUpdate,
    UserResponse
)
from auth.dependencies import get_current_user

router = APIRouter()

@router.get("/", response_model=UserSettingsResponse)
async def get_user_settings(current_user: UserResponse = Depends(get_current_user)):
    """Get current user's settings"""
    db = get_db()
    
    # Try to find existing settings
    settings = await db.usersettings.find_unique(
        where={"userId": current_user.id}
    )
    
    # If no settings exist, create default settings
    if not settings:
        settings = await db.usersettings.create(
            data={
                "userId": current_user.id,
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
    
    return UserSettingsResponse(
        id=settings.id,
        userId=settings.userId,
        language=settings.language,
        timezone=settings.timezone,
        dateFormat=settings.dateFormat,
        autoSave=settings.autoSave,
        emailDailyDigest=settings.emailDailyDigest,
        emailNewCandidateAlerts=settings.emailNewCandidateAlerts,
        emailMarketingEmails=settings.emailMarketingEmails,
        emailNewApplications=settings.emailNewApplications,
        pushNewApplications=settings.pushNewApplications,
        emailInterviewReminders=settings.emailInterviewReminders,
        pushInterviewReminders=settings.pushInterviewReminders,
        emailTaskDeadlines=settings.emailTaskDeadlines,
        pushTaskDeadlines=settings.pushTaskDeadlines,
        emailProductUpdates=settings.emailProductUpdates,
        pushProductUpdates=settings.pushProductUpdates,
        emailSecurityAlerts=settings.emailSecurityAlerts,
        pushSecurityAlerts=settings.pushSecurityAlerts,
        createdAt=settings.createdAt,
        updatedAt=settings.updatedAt
    )

@router.put("/", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update user settings"""
    db = get_db()
    
    # Check if settings exist
    existing_settings = await db.usersettings.find_unique(
        where={"userId": current_user.id}
    )
    
    if not existing_settings:
        # Create new settings if they don't exist
        settings_data = {
            "userId": current_user.id,
            "language": settings_update.language or "en-US",
            "timezone": settings_update.timezone or "UTC",
            "dateFormat": settings_update.dateFormat or "MM/DD/YYYY",
            "autoSave": settings_update.autoSave if settings_update.autoSave is not None else True,
            "emailDailyDigest": settings_update.emailDailyDigest if settings_update.emailDailyDigest is not None else True,
            "emailNewCandidateAlerts": settings_update.emailNewCandidateAlerts if settings_update.emailNewCandidateAlerts is not None else True,
            "emailMarketingEmails": settings_update.emailMarketingEmails if settings_update.emailMarketingEmails is not None else False,
            "emailNewApplications": settings_update.emailNewApplications if settings_update.emailNewApplications is not None else True,
            "pushNewApplications": settings_update.pushNewApplications if settings_update.pushNewApplications is not None else True,
            "emailInterviewReminders": settings_update.emailInterviewReminders if settings_update.emailInterviewReminders is not None else True,
            "pushInterviewReminders": settings_update.pushInterviewReminders if settings_update.pushInterviewReminders is not None else True,
            "emailTaskDeadlines": settings_update.emailTaskDeadlines if settings_update.emailTaskDeadlines is not None else True,
            "pushTaskDeadlines": settings_update.pushTaskDeadlines if settings_update.pushTaskDeadlines is not None else False,
            "emailProductUpdates": settings_update.emailProductUpdates if settings_update.emailProductUpdates is not None else True,
            "pushProductUpdates": settings_update.pushProductUpdates if settings_update.pushProductUpdates is not None else False,
            "emailSecurityAlerts": settings_update.emailSecurityAlerts if settings_update.emailSecurityAlerts is not None else True,
            "pushSecurityAlerts": settings_update.pushSecurityAlerts if settings_update.pushSecurityAlerts is not None else True
        }
        
        settings = await db.usersettings.create(data=settings_data)
    else:
        # Update existing settings
        update_data = {}
        
        if settings_update.language is not None:
            update_data["language"] = settings_update.language
        if settings_update.timezone is not None:
            update_data["timezone"] = settings_update.timezone
        if settings_update.dateFormat is not None:
            update_data["dateFormat"] = settings_update.dateFormat
        if settings_update.autoSave is not None:
            update_data["autoSave"] = settings_update.autoSave
        if settings_update.emailDailyDigest is not None:
            update_data["emailDailyDigest"] = settings_update.emailDailyDigest
        if settings_update.emailNewCandidateAlerts is not None:
            update_data["emailNewCandidateAlerts"] = settings_update.emailNewCandidateAlerts
        if settings_update.emailMarketingEmails is not None:
            update_data["emailMarketingEmails"] = settings_update.emailMarketingEmails
        if settings_update.emailNewApplications is not None:
            update_data["emailNewApplications"] = settings_update.emailNewApplications
        if settings_update.pushNewApplications is not None:
            update_data["pushNewApplications"] = settings_update.pushNewApplications
        if settings_update.emailInterviewReminders is not None:
            update_data["emailInterviewReminders"] = settings_update.emailInterviewReminders
        if settings_update.pushInterviewReminders is not None:
            update_data["pushInterviewReminders"] = settings_update.pushInterviewReminders
        if settings_update.emailTaskDeadlines is not None:
            update_data["emailTaskDeadlines"] = settings_update.emailTaskDeadlines
        if settings_update.pushTaskDeadlines is not None:
            update_data["pushTaskDeadlines"] = settings_update.pushTaskDeadlines
        if settings_update.emailProductUpdates is not None:
            update_data["emailProductUpdates"] = settings_update.emailProductUpdates
        if settings_update.pushProductUpdates is not None:
            update_data["pushProductUpdates"] = settings_update.pushProductUpdates
        if settings_update.emailSecurityAlerts is not None:
            update_data["emailSecurityAlerts"] = settings_update.emailSecurityAlerts
        if settings_update.pushSecurityAlerts is not None:
            update_data["pushSecurityAlerts"] = settings_update.pushSecurityAlerts
        
        settings = await db.usersettings.update(
            where={"userId": current_user.id},
            data=update_data
        )
    # Log activity
    await ActivityHelpers.log_settings_updated(
       user_id=current_user.id,
       setting_type="general" # Can be more specific if needed
   )
    return UserSettingsResponse(
        id=settings.id,
        userId=settings.userId,
        language=settings.language,
        timezone=settings.timezone,
        dateFormat=settings.dateFormat,
        autoSave=settings.autoSave,
        emailDailyDigest=settings.emailDailyDigest,
        emailNewCandidateAlerts=settings.emailNewCandidateAlerts,
        emailMarketingEmails=settings.emailMarketingEmails,
        emailNewApplications=settings.emailNewApplications,
        pushNewApplications=settings.pushNewApplications,
        emailInterviewReminders=settings.emailInterviewReminders,
        pushInterviewReminders=settings.pushInterviewReminders,
        emailTaskDeadlines=settings.emailTaskDeadlines,
        pushTaskDeadlines=settings.pushTaskDeadlines,
        emailProductUpdates=settings.emailProductUpdates,
        pushProductUpdates=settings.pushProductUpdates,
        emailSecurityAlerts=settings.emailSecurityAlerts,
        pushSecurityAlerts=settings.pushSecurityAlerts,
        createdAt=settings.createdAt,
        updatedAt=settings.updatedAt
    )

@router.put("/general", response_model=UserSettingsResponse)
async def update_general_settings(
    general_settings: GeneralSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update general settings (language, timezone, date format, auto-save)"""
    db = get_db()
    
    # Ensure settings exist
    await get_user_settings(current_user)
    
    update_data = {}
    if general_settings.language is not None:
        update_data["language"] = general_settings.language
    if general_settings.timezone is not None:
        update_data["timezone"] = general_settings.timezone
    if general_settings.dateFormat is not None:
        update_data["dateFormat"] = general_settings.dateFormat
    if general_settings.autoSave is not None:
        update_data["autoSave"] = general_settings.autoSave
    
    settings = await db.usersettings.update(
        where={"userId": current_user.id},
        data=update_data
    )
    # Log activity
    await ActivityHelpers.log_settings_updated(
       user_id=current_user.id,
       setting_type="general"
   )
    
    return UserSettingsResponse(
        id=settings.id,
        userId=settings.userId,
        language=settings.language,
        timezone=settings.timezone,
        dateFormat=settings.dateFormat,
        autoSave=settings.autoSave,
        emailDailyDigest=settings.emailDailyDigest,
        emailNewCandidateAlerts=settings.emailNewCandidateAlerts,
        emailMarketingEmails=settings.emailMarketingEmails,
        emailNewApplications=settings.emailNewApplications,
        pushNewApplications=settings.pushNewApplications,
        emailInterviewReminders=settings.emailInterviewReminders,
        pushInterviewReminders=settings.pushInterviewReminders,
        emailTaskDeadlines=settings.emailTaskDeadlines,
        pushTaskDeadlines=settings.pushTaskDeadlines,
        emailProductUpdates=settings.emailProductUpdates,
        pushProductUpdates=settings.pushProductUpdates,
        emailSecurityAlerts=settings.emailSecurityAlerts,
        pushSecurityAlerts=settings.pushSecurityAlerts,
        createdAt=settings.createdAt,
        updatedAt=settings.updatedAt
    )

@router.put("/email", response_model=UserSettingsResponse)
async def update_email_settings(
    email_settings: EmailSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update email settings"""
    db = get_db()
    
    # Ensure settings exist
    await get_user_settings(current_user)
    
    update_data = {}
    if email_settings.emailDailyDigest is not None:
        update_data["emailDailyDigest"] = email_settings.emailDailyDigest
    if email_settings.emailNewCandidateAlerts is not None:
        update_data["emailNewCandidateAlerts"] = email_settings.emailNewCandidateAlerts
    if email_settings.emailMarketingEmails is not None:
        update_data["emailMarketingEmails"] = email_settings.emailMarketingEmails
    
    settings = await db.usersettings.update(
        where={"userId": current_user.id},
        data=update_data
    )
    # Log activity
    await ActivityHelpers.log_settings_updated(
       user_id=current_user.id,
       setting_type="email"
   )
    return UserSettingsResponse(
        id=settings.id,
        userId=settings.userId,
        language=settings.language,
        timezone=settings.timezone,
        dateFormat=settings.dateFormat,
        autoSave=settings.autoSave,
        emailDailyDigest=settings.emailDailyDigest,
        emailNewCandidateAlerts=settings.emailNewCandidateAlerts,
        emailMarketingEmails=settings.emailMarketingEmails,
        emailNewApplications=settings.emailNewApplications,
        pushNewApplications=settings.pushNewApplications,
        emailInterviewReminders=settings.emailInterviewReminders,
        pushInterviewReminders=settings.pushInterviewReminders,
        emailTaskDeadlines=settings.emailTaskDeadlines,
        pushTaskDeadlines=settings.pushTaskDeadlines,
        emailProductUpdates=settings.emailProductUpdates,
        pushProductUpdates=settings.pushProductUpdates,
        emailSecurityAlerts=settings.emailSecurityAlerts,
        pushSecurityAlerts=settings.pushSecurityAlerts,
        createdAt=settings.createdAt,
        updatedAt=settings.updatedAt
    )

@router.put("/notifications", response_model=UserSettingsResponse)
async def update_notification_settings(
    notification_settings: NotificationSettingsUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update notification settings"""
    db = get_db()
    
    # Ensure settings exist
    await get_user_settings(current_user)
    
    update_data = {}
    if notification_settings.emailNewApplications is not None:
        update_data["emailNewApplications"] = notification_settings.emailNewApplications
    if notification_settings.pushNewApplications is not None:
        update_data["pushNewApplications"] = notification_settings.pushNewApplications
    if notification_settings.emailInterviewReminders is not None:
        update_data["emailInterviewReminders"] = notification_settings.emailInterviewReminders
    if notification_settings.pushInterviewReminders is not None:
        update_data["pushInterviewReminders"] = notification_settings.pushInterviewReminders
    if notification_settings.emailTaskDeadlines is not None:
        update_data["emailTaskDeadlines"] = notification_settings.emailTaskDeadlines
    if notification_settings.pushTaskDeadlines is not None:
        update_data["pushTaskDeadlines"] = notification_settings.pushTaskDeadlines
    if notification_settings.emailProductUpdates is not None:
        update_data["emailProductUpdates"] = notification_settings.emailProductUpdates
    if notification_settings.pushProductUpdates is not None:
        update_data["pushProductUpdates"] = notification_settings.pushProductUpdates
    if notification_settings.emailSecurityAlerts is not None:
        update_data["emailSecurityAlerts"] = notification_settings.emailSecurityAlerts
    if notification_settings.pushSecurityAlerts is not None:
        update_data["pushSecurityAlerts"] = notification_settings.pushSecurityAlerts
    
    settings = await db.usersettings.update(
        where={"userId": current_user.id},
        data=update_data
    )
    # Log activity
    await ActivityHelpers.log_settings_updated(
       user_id=current_user.id,
       setting_type="notifications"
   )
    return UserSettingsResponse(
        id=settings.id,
        userId=settings.userId,
        language=settings.language,
        timezone=settings.timezone,
        dateFormat=settings.dateFormat,
        autoSave=settings.autoSave,
        emailDailyDigest=settings.emailDailyDigest,
        emailNewCandidateAlerts=settings.emailNewCandidateAlerts,
        emailMarketingEmails=settings.emailMarketingEmails,
        emailNewApplications=settings.emailNewApplications,
        pushNewApplications=settings.pushNewApplications,
        emailInterviewReminders=settings.emailInterviewReminders,
        pushInterviewReminders=settings.pushInterviewReminders,
        emailTaskDeadlines=settings.emailTaskDeadlines,
        pushTaskDeadlines=settings.pushTaskDeadlines,
        emailProductUpdates=settings.emailProductUpdates,
        pushProductUpdates=settings.pushProductUpdates,
        emailSecurityAlerts=settings.emailSecurityAlerts,
        pushSecurityAlerts=settings.pushSecurityAlerts,
        createdAt=settings.createdAt,
        updatedAt=settings.updatedAt
    )

@router.delete("/")
async def reset_user_settings(current_user: UserResponse = Depends(get_current_user)):
    """Reset user settings to default values"""
    db = get_db()
    
    # Delete existing settings
    await db.usersettings.delete_many(where={"userId": current_user.id})
    
    # Create new default settings
    settings = await db.usersettings.create(
        data={
            "userId": current_user.id,
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
    
    return {"message": "Settings reset to default values successfully"}
