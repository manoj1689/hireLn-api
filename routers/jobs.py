from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta

from pydantic import Json
from database import get_db
from models.schemas import (
    JobCreate, JobUpdate, JobResponse, UserResponse, JobStatus,
    JobBasicInfo, JobDetails, JobRequirements, JobPublishOptions,
    JobStep1Response, JobStep2Response, JobStep3Response, 
    JobCreationCompleteResponse, JobStepperCreate
)
from auth.dependencies import get_current_user
import uuid
import json

router = APIRouter()

# In-memory session storage (in production, use Redis or database)
job_sessions = {}

@router.post("/create/step1", response_model=JobStep1Response)
async def create_job_step1(
    basic_info: JobBasicInfo,
    current_user: UserResponse = Depends(get_current_user)
):
    """Step 1: Basic Information - Job title, department, location, salary"""
    session_id = str(uuid.uuid4())
    
    # Store step 1 data in session
    job_sessions[session_id] = {
        "user_id": current_user.id,
        "step": 1,
        "basic_info": basic_info.dict(),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24)
    }
    
    # AI suggestions based on job title and department
    ai_suggestions = {
        "titleSuggestion": f"Senior {basic_info.jobTitle}",
        "salaryRange": {
            "min": 120000 if "senior" in basic_info.jobTitle.lower() else 80000,
            "max": 180000 if "senior" in basic_info.jobTitle.lower() else 120000,
            "note": "Market Average"
        }
    }
    
    return JobStep1Response(
        message="Basic information saved successfully",
        step=1,
        sessionId=session_id,
        aiSuggestions=ai_suggestions
    )

@router.post("/create/step2", response_model=JobStep2Response)
async def create_job_step2(
    job_details: JobDetails,
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Step 2: Job Details - Description, responsibilities, work mode"""
    if session_id not in job_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session ID or session expired"
        )
    
    session = job_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to different user"
        )
    
    # Update session with step 2 data
    session["step"] = 2
    session["job_details"] = job_details.dict()
    
    # Similar active positions (mock data)
    similar_jobs = [
        {
            "title": "Senior Frontend Developer",
            "company": "Google",
            "location": "San Francisco",
            "salary": "$150-180K"
        },
        {
            "title": "Frontend Team Lead", 
            "company": "Meta",
            "location": "Remote",
            "salary": "$160-200K"
        }
    ]
    
    return JobStep2Response(
        message="Job details saved successfully",
        step=2,
        sessionId=session_id,
        similarJobs=similar_jobs
    )

@router.post("/create/step3", response_model=JobStep3Response)
async def create_job_step3(
    requirements: JobRequirements,
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Step 3: Requirements - Skills, education, certifications"""
    if session_id not in job_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session ID or session expired"
        )
    
    session = job_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to different user"
        )
    
    # Update session with step 3 data
    session["step"] = 3
    session["requirements"] = requirements.model_dump()
    
    # Return all entered data
    job_data = {
        "basic_info": session.get("basic_info", {}),
        "job_details": session.get("job_details", {}),
        "requirements": session.get("requirements", {}),
    }
    
    return JobStep3Response(
        message="Requirements saved successfully",
        step=3,
        sessionId=session_id,
        jobData=job_data
    )

@router.post("/create/step4", response_model=JobCreationCompleteResponse)
async def create_job_step4(
    publish_options: JobPublishOptions,
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Step 4: Review & Publish - Final review and publishing options"""
    # Check if the session exists
    if session_id not in job_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session ID or session expired"
        )
    
    session = job_sessions[session_id]
    
    # Ensure session belongs to the current user
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to a different user"
        )
    
    # Get all session data
    basic_info = JobBasicInfo(**session["basic_info"])
    job_details = JobDetails(**session["job_details"])
    requirements = JobRequirements(**session["requirements"])
    
    # Process languages data properly
    languages_data = []
    if requirements.languages:
        for lang in requirements.languages:
            if isinstance(lang, dict):
                # Handle both possible key formats
                language_name = lang.get('language') or lang.get('name', '')
                proficiency = lang.get('proficiency') or lang.get('level', '')
                if language_name and proficiency:
                    languages_data.append({
                        "language": language_name,
                        "proficiency": proficiency
                    })
    
    # Prepare job data for creation
    data = {
        "title": basic_info.jobTitle,
        "description": job_details.jobDescription,
        "department": basic_info.department,
        "location": basic_info.location,
        "employmentType": basic_info.employmentType,
        "salaryMin": basic_info.salaryMin or 0,
        "salaryMax": basic_info.salaryMax or 0,
        "salaryPeriod": basic_info.salaryPeriod,
        "responsibilities": job_details.keyResponsibilities or [],
        "requirements": [],  # Add empty requirements array if needed
        "experience": job_details.requiredExperience,
        "teamSize": job_details.teamSize,
        "reportingStructure": job_details.reportingStructure,
        
        # Requirements fields - ensure they're properly mapped
        "skills": requirements.requiredSkills or [],
        "education": requirements.educationLevel,  # This should save to education field
        "certifications": requirements.certifications or [],
        "softSkills": requirements.softSkills or [],
        "languages": json.dumps(languages_data) if languages_data else json.dumps([]),
        
        # Work mode settings
        "isRemote": job_details.workMode.lower() == "remote",
        "isHybrid": job_details.workMode.lower() == "hybrid",
        
        # Publishing options
        "internalJobBoard": publish_options.internalJobBoard,
        "externalJobBoards": publish_options.externalJobBoards,
        "socialMedia": publish_options.socialMedia,
        "applicationFormFields": json.dumps(publish_options.applicationFormFields) if isinstance(publish_options.applicationFormFields, dict) else publish_options.applicationFormFields,
        
        # Status and timestamps
        "status": "ACTIVE" if publish_options.externalJobBoards else "DRAFT",
        "publishedAt": datetime.utcnow() if publish_options.externalJobBoards else None,
        
        # User association
        "userId": current_user.id
    }

    # Get the database session
    db = get_db()
    try:
        # Create the job in the database
        job = await db.job.create(data=data)
        # print(f"Job created successfully with data: {data}")  # Debug logging
    except Exception as e:
        # print(f"Error creating job: {str(e)}")  # Debug logging
        # print(f"Data being sent: {data}")  # Debug logging
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

    # Determine where job was published
    published_to = []
    if publish_options.internalJobBoard:
        published_to.append("Internal Job Board")
    if publish_options.externalJobBoards:
        published_to.extend(["Indeed", "LinkedIn", "Glassdoor"])
    if publish_options.socialMedia:
        published_to.extend(["Twitter", "Facebook"])
    
    # Clean up session
    del job_sessions[session_id]
    
    return JobCreationCompleteResponse(
        message="Job created and published successfully",
        job=JobResponse(**job.model_dump()),
        publishedTo=published_to
    )

@router.get("/create/session/{session_id}")
async def get_job_session(
    session_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current session data for review"""
    if session_id not in job_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session = job_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to different user"
        )
    
    return {
        "sessionId": session_id,
        "step": session["step"],
        "basicInfo": session.get("basic_info"),
        "jobDetails": session.get("job_details"),
        "requirements": session.get("requirements")
    }

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[JobStatus] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all jobs with optional filtering"""
    db = get_db()
    
    where_clause = {}
    
    if status:
        where_clause["status"] = status
    
    if department:
        where_clause["department"] = department
    
    if search:
        where_clause["OR"] = [
            {"title": {"contains": search, "mode": "insensitive"}},
            {"description": {"contains": search, "mode": "insensitive"}}
        ]
    
    jobs = await db.job.find_many(
        where=where_clause,
        skip=skip,
        take=limit
    )
    
    # Sort jobs by createdAt descending manually in Python
    jobs_sorted = sorted(jobs, key=lambda job: job.createdAt, reverse=True)
    
    return [JobResponse(**job.dict()) for job in jobs_sorted]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a specific job by ID"""
    db = get_db()
    
    job = await db.job.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(**job.dict())

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update a job posting"""
    db = get_db()

    # Find existing job
    existing_job = await db.job.find_unique(where={"id": job_id})
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Prepare update data
    update_data = job_data.dict(exclude_unset=True)

    # Serialize JSON fields if they exist
    if "languages" in update_data and isinstance(update_data["languages"], (dict, list)):
        update_data["languages"] = json.dumps(update_data["languages"])

    if "applicationFormFields" in update_data and isinstance(update_data["applicationFormFields"], (dict, list)):
        update_data["applicationFormFields"] = json.dumps(update_data["applicationFormFields"])

    # Perform update
    job = await db.job.update(
        where={"id": job_id},
        data=update_data
    )

    return JobResponse(**job.dict())

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete a job posting"""
    db = get_db()
    
    # Check if the job exists
    existing_job = await db.job.find_unique(where={"id": job_id})
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if the current user is the owner of the job
    if existing_job.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this job"
        )
    
    # Delete the job from the database
    await db.job.delete(where={"id": job_id})

    return {"message": "Job deleted successfully", "jobId": job_id}

@router.post("/{job_id}/publish")
async def publish_job(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Publish a job posting"""
    db = get_db()
    
    job = await db.job.update(
        where={"id": job_id},
        data={
            "status": "ACTIVE",
            "publishedAt": datetime.utcnow()
        }
    )
    
    return JobResponse(**job.dict())
