import json
from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from typing import List, Optional
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import (
    CandidateCreate, CandidateResponse, ApplicationCreate, 
    ApplicationUpdate, ApplicationResponse, UserResponse, ApplicationStatus
)
from auth.dependencies import get_current_user
from models.schemas import InterviewStatus
from fastapi.encoders import jsonable_encoder

router = APIRouter()

@router.post("/add", response_model=CandidateResponse)
async def create_candidate(
    candidate_data: CandidateCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new candidate"""
    db = get_db()

    # Check if candidate already exists
    existing_candidate = await db.candidate.find_unique(where={"email": candidate_data.email})
    if existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Candidate with this email already exists"
        )

    # Convert Pydantic model to dict
    candidate_dict = candidate_data.dict()

    # Fields to be serialized as JSON strings before storing
    json_fields = [
        "education", 
        "experience", 
        "certifications", 
        "projects", 
        "previousJobs", 
        "personalInfo"
    ]

    for field in json_fields:
        if candidate_dict.get(field) is not None:
            candidate_dict[field] = json.dumps(candidate_dict[field])

    # Create candidate in DB
    candidate = await db.candidate.create(data=candidate_dict)
    print("Candidate JSON (after serialization):", json.dumps(candidate_dict, indent=2))

    # Prepare response with default fields
    response_data = candidate.dict()
    response_data["applicationStatus"] = None
    response_data["interviewStatus"] = None

    # Log activity
    await ActivityHelpers.log_candidate_added(
        user_id=current_user.id,
        candidate_id=candidate.id,
        candidate_name=candidate.name
    )

    return CandidateResponse(**response_data)

@router.get("/", response_model=List[CandidateResponse])
async def get_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    technicalSkills: Optional[List[str]] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all candidates with optional filtering by search and technical skills only"""
    db = get_db()
    
    where_clause = {}

    # Search by name/email/skills
    if search:
        where_clause["OR"] = [
            {"name": {"contains": search, "mode": "insensitive"}},
            {"email": {"contains": search, "mode": "insensitive"}},
            {"technicalSkills": {"has": search}}
        ]

    # Filter by technicalSkills
    if technicalSkills:
        where_clause["AND"] = where_clause.get("AND", []) + [
            {"technicalSkills": {"hasSome": technicalSkills}}
        ]

    candidates = await db.candidate.find_many(
        where=where_clause,
        skip=skip,
        take=limit,
        include={
            "applications": {
                "where": {"userId": current_user.id},
                "include": {
                    "interviews": {
                        "order_by": {"scheduledAt": "desc"}
                    }
                },
                "order_by": {"appliedAt": "desc"}
            }
        }
    )
    
    result = []
    for candidate in candidates:
        latest_application_status = None
        latest_interview_status = None
        
        if candidate.applications:
            latest_app = candidate.applications[0]
            latest_application_status = latest_app.status

            all_interviews = []
            for app in candidate.applications:
                if app.interviews:
                    all_interviews.extend(app.interviews)
            
            if all_interviews:
                sorted_interviews = sorted(all_interviews, key=lambda x: x.scheduledAt, reverse=True)
                latest_interview_status = sorted_interviews[0].status
        
        candidate_data = candidate.dict()
        candidate_data["applicationStatus"] = latest_application_status
        candidate_data["interviewStatus"] = latest_interview_status
        
        result.append(CandidateResponse(**candidate_data))
    
    return result

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a specific candidate by ID with application and interview status"""
    db = get_db()
    
    candidate = await db.candidate.find_unique(
        where={"id": candidate_id},
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "interviews": {
                        "order_by": {"scheduledAt": "desc"}
                    }
                },
                "order_by": {"appliedAt": "desc"}
            }
        }
    )
    
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Get the most recent application status
    latest_application_status = None
    latest_interview_status = None
    
    if candidate.applications:
        # Get the most recent application
        latest_app = candidate.applications[0]  # Already ordered by appliedAt desc
        latest_application_status = latest_app.status
        
        # Get the most recent interview status from all applications
        all_interviews = []
        for app in candidate.applications:
            if app.interviews:
                all_interviews.extend(app.interviews)
        
        if all_interviews:
            # Sort all interviews by scheduledAt desc and get the latest
            sorted_interviews = sorted(all_interviews, key=lambda x: x.scheduledAt, reverse=True)
            latest_interview_status = sorted_interviews[0].status
    
    # Build candidate response with original structure plus status fields
    candidate_data = candidate.dict()
    candidate_data["applicationStatus"] = latest_application_status
    candidate_data["interviewStatus"] = latest_interview_status
    
    return CandidateResponse(**candidate_data)

# 🔁 UPDATE candidate
@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    update_data: CandidateCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()

    existing_candidate = await db.candidate.find_unique(where={"id": candidate_id})
    if not existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    candidate = await db.candidate.update(
        where={"id": candidate_id},
        data=update_data.dict(exclude_unset=True)
    )

    candidate_data = candidate.dict()
    candidate_data["applicationStatus"] = None
    candidate_data["interviewStatus"] = None

    # Log activity
    await ActivityHelpers.log_candidate_updated(
       user_id=current_user.id,
       candidate_id=candidate.id,
       candidate_name=candidate.name
   )

    return CandidateResponse(**candidate_data)


# ❌ DELETE candidate
@router.delete("/{candidate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()

    existing_candidate = await db.candidate.find_unique(where={"id": candidate_id})
    if not existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    await db.candidate.delete(where={"id": candidate_id})
    
    await ActivityHelpers.log_candidate_deleted(
       user_id=current_user.id,
       candidate_id=candidate_id,
       candidate_name=existing_candidate.name
   )


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new job application"""
    db = get_db()
    
    # Check if application already exists
    existing_application = await db.application.find_unique(
        where={
            "jobId_candidateId": {
                "jobId": application_data.jobId,
                "candidateId": application_data.candidateId
            }
        }
    )
    if existing_application:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Application already exists for this job and candidate"
        )
    
    # Create application data with current user's ID
    app_data = application_data.dict()
    app_data["userId"] = current_user.id  # Use the current authenticated user's ID
    
    application = await db.application.create(data=app_data)
    
     # Fetch job and candidate details for logging
    job = await db.job.find_unique(where={"id": application.jobId})
    candidate = await db.candidate.find_unique(where={"id": application.candidateId})

    if job and candidate:
       await ActivityHelpers.log_application_received(
           user_id=current_user.id,
           application_id=application.id,
           candidate_name=candidate.name,
           job_title=job.title
       )
    return ApplicationResponse(**application.dict())

@router.get("/applications/list", response_model=List[ApplicationResponse])
async def get_applications(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    candidate_id: Optional[str] = Query(None, description="Filter by candidate ID"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get applications with optional filtering"""
    db = get_db()

    # Debug: Print current_user ID
    # print(f"Current user ID: {current_user.id}")

    # Validate candidate exists if candidate_id is provided
    if candidate_id:
        # print(f"Checking candidate with ID: {candidate_id}")
        candidate = await db.candidate.find_unique(where={"id": candidate_id})

        # Debug: Check if candidate was found
        # if candidate:
        #     print(f"Candidate found: {candidate}")
        # else:
        #     print(f"Candidate not found with ID: {candidate_id}")  

        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
    
    # Validate job exists if job_id is provided
    if job_id:
        # print(f"Checking job with ID: {job_id}")
        job = await db.job.find_unique(where={"id": job_id})
        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

    # Build where clause for application filtering, including the authenticated user's userId
    where_clause = {"userId": current_user.id}  # Filter applications by the authenticated user
    if job_id:
        where_clause["jobId"] = job_id
    if candidate_id:
        where_clause["candidateId"] = candidate_id
    if status:
        where_clause["status"] = status

    # Debug: Print where_clause to see the final filter
    # print(f"Where clause for fetching applications: {where_clause}")

    try:
        # Fetch applications based on where_clause
        applications = await db.application.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            include={
                "job": True,
                "candidate": True
            }
        )

        # Debug: Print fetched applications
        # print(f"Fetched applications: {applications}")

        # Convert to response format
        result = []
        for app in applications:
            app_dict = {
                "id": app.id,
                "jobId": app.jobId,
                "candidateId": app.candidateId,
                "coverLetter": app.coverLetter,
                "status": app.status,
                "matchScore": app.matchScore,
                "notes": app.notes,
                "appliedAt": app.appliedAt,
                "updatedAt": app.updatedAt
            }
            result.append(ApplicationResponse(**app_dict))

        return result

    except Exception as e:
        print(f"Error while fetching applications: {str(e)}")  # Debugging the error
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching applications: {str(e)}"
        )

@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update an application status"""
    db = get_db()
    
    # Check if application exists
    existing_application = await db.application.find_unique(where={"id": application_id})
    if not existing_application:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    update_data = application_data.dict(exclude_unset=True)
    application = await db.application.update(
        where={"id": application_id},
        data=update_data
    )
   

    # Log activity if status changed
    if application_data.status and application_data.status != existing_application.status:
        if existing_application.job and existing_application.candidate:
            await ActivityHelpers.log_application_status_changed(
                user_id=current_user.id,
                application_id=application.id,
                candidate_name=existing_application.candidate.name,
                job_title=existing_application.job.title,
                new_status=application_data.status.value
            )
   
    return ApplicationResponse(**application.dict())

# Add a debug endpoint to check what data exists
@router.get("/debug/applications")
async def debug_applications(
    current_user: UserResponse = Depends(get_current_user)
):
    """Debug endpoint to see all applications data"""
    db = get_db()
    
    try:
        # Get all applications
        applications = await db.application.find_many(
            include={
                "job": True,
                "candidate": True
            }
        )
        
        # Get all jobs
        jobs = await db.job.find_many()
        
        # Get all candidates
        candidates = await db.candidate.find_many()
        
        return {
            "total_applications": len(applications),
            "total_jobs": len(jobs),
            "total_candidates": len(candidates),
            "applications": [
                {
                    "id": app.id,
                    "jobId": app.jobId,
                    "candidateId": app.candidateId,
                    "status": app.status,
                    "job_title": app.job.title if app.job else "No job",
                    "candidate_name": app.candidate.name if app.candidate else "No candidate"
                }
                for app in applications
            ],
            "jobs": [{"id": job.id, "title": job.title} for job in jobs],
            "candidates": [{"id": candidate.id, "name": candidate.name} for candidate in candidates]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/{candidate_id}/status-summary")
async def get_candidate_status_summary(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a summary of candidate's application and interview status"""
    db = get_db()
    
    candidate = await db.candidate.find_unique(
        where={"id": candidate_id},
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "job": True,
                    "interviews": True
                }
            }
        }
    )
    
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Calculate statistics
    stats = {
        "candidateId": candidate_id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "totalApplications": len(candidate.applications),
        "applicationsByStatus": {
            "APPLIED": 0,
            "SCREENING": 0,
            "INTERVIEW": 0,
            "OFFER": 0,
            "HIRED": 0,
            "REJECTED": 0
        },
        "interviewsByStatus": {
            "SCHEDULED": 0,
            "CONFIRMED": 0,
            "IN_PROGRESS": 0,
            "COMPLETED": 0,
            "CANCELLED": 0,
            "NO_SHOW": 0,
            "RESCHEDULED": 0
        },
        "interviewsByType": {
            "PHONE": 0,
            "VIDEO": 0,
            "IN_PERSON": 0,
            "TECHNICAL": 0,
            "BEHAVIORAL": 0,
            "PANEL": 0
        },
        "averageMatchScore": 0,
        "recentActivity": []
    }
    
    total_match_score = 0
    match_score_count = 0
    
    for app in candidate.applications:
        # Count applications by status
        stats["applicationsByStatus"][app.status] += 1
        
        # Calculate average match score
        if app.matchScore:
            total_match_score += app.matchScore
            match_score_count += 1
        
        # Add to recent activity
        stats["recentActivity"].append({
            "type": "APPLICATION",
            "action": f"Applied for {app.job.title if app.job else 'Unknown Position'}",
            "date": app.appliedAt,
            "status": app.status
        })
        
        # Count interviews
        for interview in app.interviews:
            stats["interviewsByStatus"][interview.status] += 1
            stats["interviewsByType"][interview.type] += 1
            
            # Add to recent activity
            stats["recentActivity"].append({
                "type": "INTERVIEW",
                "action": f"{interview.type} interview for {app.job.title if app.job else 'Unknown Position'}",
                "date": interview.scheduledAt,
                "status": interview.status
            })
    
    # Calculate average match score
    if match_score_count > 0:
        stats["averageMatchScore"] = round(total_match_score / match_score_count, 1)
    
    # Sort recent activity by date (most recent first)
    stats["recentActivity"].sort(key=lambda x: x["date"], reverse=True)
    stats["recentActivity"] = stats["recentActivity"][:10]  # Limit to 10 most recent
    
    return stats

@router.get("/statistics/overview")
async def get_candidates_overview(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get overview statistics for all candidates"""
    db = get_db()
    
    # Get all candidates with their applications and interviews
    candidates = await db.candidate.find_many(
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "interviews": True
                }
            }
        }
    )
    
    stats = {
        "totalCandidates": len(candidates),
        "candidatesWithApplications": 0,
        "candidatesWithInterviews": 0,
        "applicationsByStatus": {
            "APPLIED": 0,
            "SCREENING": 0,
            "INTERVIEW": 0,
            "OFFER": 0,
            "HIRED": 0,
            "REJECTED": 0
        },
        "interviewsByStatus": {
            "SCHEDULED": 0,
            "CONFIRMED": 0,
            "IN_PROGRESS": 0,
            "COMPLETED": 0,
            "CANCELLED": 0,
            "NO_SHOW": 0,
            "RESCHEDULED": 0
        },
        "topSkills": {},
        "averageApplicationsPerCandidate": 0
    }
    
    total_applications = 0
    
    for candidate in candidates:
        # Count candidates with applications
        if candidate.applications:
            stats["candidatesWithApplications"] += 1
            total_applications += len(candidate.applications)
        
        # Check if candidate has interviews
        has_interviews = any(app.interviews for app in candidate.applications)
        if has_interviews:
            stats["candidatesWithInterviews"] += 1
        
        # Count skills
        for skill in candidate.skills:
            stats["topSkills"][skill] = stats["topSkills"].get(skill, 0) + 1
        
        # Count applications and interviews by status
        for app in candidate.applications:
            stats["applicationsByStatus"][app.status] += 1
            
            for interview in app.interviews:
                stats["interviewsByStatus"][interview.status] += 1
    
    # Calculate average applications per candidate
    if stats["candidatesWithApplications"] > 0:
        stats["averageApplicationsPerCandidate"] = round(
            total_applications / stats["candidatesWithApplications"], 1
        )
    
    # Get top 10 skills
    stats["topSkills"] = dict(
        sorted(stats["topSkills"].items(), key=lambda x: x[1], reverse=True)[:10]
    )
    
    return stats
