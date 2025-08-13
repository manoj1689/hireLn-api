from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional, Union

from fastapi.responses import JSONResponse
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import (
    InterviewResultWithDetailsResponse, InterviewScheduleRequest, InterviewResponse, InterviewRescheduleRequest,
    InterviewFeedbackRequest, InterviewStatus, InterviewType, UserResponse
)
from auth.dependencies import get_current_user, get_user_or_interview_auth
from datetime import datetime, timedelta
import pytz
import json
from service.email_service import EmailService, email_service
from utils.openai_client import create_openai_chat
from utils.token_utils import generate_interview_token, generate_token_expiry
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/schedule", response_model=InterviewResponse)
async def schedule_interview(
    interview_data: InterviewScheduleRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Schedule a new interview"""
    db = get_db()
    
    # Check if candidate exists
    candidate = await db.candidate.find_unique(where={"id": interview_data.candidateId})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check if application exists
    application = await db.application.find_unique(
        where={"id": interview_data.applicationId},
        include={"job": True}
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = application.job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # ✅ Parse local date & time, convert to UTC, keep as datetime (not str)
    try:
        scheduled_datetime = datetime.strptime(
            f"{interview_data.scheduledDate} {interview_data.scheduledTime}",
            "%Y-%m-%d %H:%M"
        )
        print("🕒 Naive datetime (no timezone):", scheduled_datetime)
        
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date, time, or timezone format"
        )
    
    join_token = generate_interview_token()
    token_expiry = generate_token_expiry(hours=48)
    
    def safe_json(value, label=""):
        if not value:
            return None

        if isinstance(value, (dict, list)):
            return value

        try:
            parsed = json.loads(value)
            return parsed
        except json.JSONDecodeError as e:
            return None


    # Example usage:
    candidate_education = safe_json(candidate.education, "candidate.education")
    candidate_experience = safe_json(candidate.experience, "candidate.experience")


    interview_data_dict = {
        "candidateId": interview_data.candidateId,
        "applicationId": interview_data.applicationId,
        "scheduledById": current_user.id,
        "userId": current_user.id,
        "jobId": job.id,
        "type": interview_data.type,
        "scheduledAt": scheduled_datetime,
        "duration": interview_data.duration,
        "timezone": interview_data.timezone,
        "meetingLink": interview_data.meetingLink,
        "location": interview_data.location,
        "notes": interview_data.notes,
        "joinToken": join_token,
        "tokenExpiry": token_expiry,
        "status": "SCHEDULED",
        "interviewers": json.dumps([i.dict() for i in interview_data.interviewers]) if interview_data.interviewers else None,
        "candidateEducation": json.dumps(candidate_education) if candidate_education else None,
        "candidateExperience": json.dumps(candidate_experience) if candidate_experience else None,
        "candidateSkills": candidate.technicalSkills,
        "candidateResume": candidate.resume,
        "candidatePortfolio": candidate.portfolio,
        "candidateLinkedIn": candidate.linkedin,
        "candidateGitHub": candidate.github,
        "candidateLocation": candidate.location,

        # Application Field
        "coverLetter": application.coverLetter,

        # Job Additional Fields
        "jobDepartment": job.department,
        "jobDescription": job.description,
        "jobType": job.employmentType,
        "jobResponsibility": job.responsibilities,
        "jobSkills": job.skills,
        "jobEducation": job.education,
        "jobCertificates": job.certifications,
        "jobPublished": job.publishedAt,
    }
    
    interview = await db.interview.create(data=interview_data_dict)

    interviewers_str_list = [f"{i.name} ({i.email})" for i in interview_data.interviewers] if interview_data.interviewers else []

    if interview_data.sendEmailNotification:
        try:
            email_sent = email_service.send_interview_invitation(
                candidate_email=candidate.email,
                candidate_name=candidate.name,
                job_title=job.title,
                interview_type=interview_data.type,
                scheduled_at=scheduled_datetime,  # ✅ proper datetime object
                duration=interview_data.duration,
                meeting_link=interview_data.meetingLink,
                location=interview_data.location,
                interviewers=interviewers_str_list,
                interview_id=interview.id,
                join_token=join_token,
                frontend_url="http://localhost:3000"
            )

            if email_sent:
                await db.interview.update(
                    where={"id": interview.id},
                    data={"invitationSent": True}
                )
        except Exception as e:
            logger.error(f"Error sending interview invitation: {str(e)}")

    if application.status == "APPLIED":
        await db.application.update(
            where={"id": application.id},
            data={"status": "INTERVIEW"}
        )
    # Log activity
    await ActivityHelpers.log_interview_scheduled(
       user_id=current_user.id,
       interview_id=interview.id,
       candidate_name=candidate.name,
       job_title=job.title,
       scheduled_date=scheduled_datetime
   )
    response = {
        "id": interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "applicationId": application.id,
        "jobId": job.id,
        "jobTitle": job.title,
        "interviewType": interview.type,
        "status": interview.status,
        "scheduledAt": interview.scheduledAt,
        "duration": interview.duration,
        "timezone": interview.timezone,
        "interviewers": interview_data.interviewers,
        "meetingLink": interview.meetingLink,
        "location": interview.location,
        "notes": interview.notes,
        "feedback": None,
        "invitationSent": interview.invitationSent,
        "joinToken": interview.joinToken,
        "tokenExpiry": interview.tokenExpiry,
        "createdAt": interview.createdAt,
        "updatedAt": interview.updatedAt
    }

    return InterviewResponse(**response)




@router.get("/", response_model=List[InterviewResponse])
async def get_interviews(
    candidate_id: Optional[str] = None,
    application_id: Optional[str] = None,
    job_id: Optional[str] = None,  # ✅ Added job_id filter
    status: Optional[InterviewStatus] = None,
    type: Optional[InterviewType] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get interviews with optional filtering"""
    db = get_db()
    
    where_clause = {}
    
    if candidate_id:
        where_clause["candidateId"] = candidate_id
    
    if application_id:
        where_clause["applicationId"] = application_id
    
    if job_id:  # ✅ Added job_id filtering
        where_clause["jobId"] = job_id
    
    if status:
        where_clause["status"] = status
    
    if type:
        where_clause["type"] = type
    
    # Date range filtering
    if from_date:
        try:
            from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
            where_clause["scheduledAt"] = {"gte": from_datetime}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid from_date format. Use YYYY-MM-DD."
            )
    
    if to_date:
        try:
            to_datetime = datetime.strptime(to_date, "%Y-%m-%d")
            to_datetime = to_datetime + timedelta(days=1)  # Include the entire day
            
            if "scheduledAt" in where_clause:
                where_clause["scheduledAt"]["lte"] = to_datetime
            else:
                where_clause["scheduledAt"] = {"lte": to_datetime}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid to_date format. Use YYYY-MM-DD."
            )
    
    interviews = await db.interview.find_many(
        where=where_clause,
        skip=skip,
        take=limit,
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True
                }
            },
            "job": True  # ✅ Added direct job include
        }
    )
    
    results = []
    for interview in interviews:
        candidate = interview.candidate
        application = interview.application
        job = interview.job or (application.job if application else None)
        job_title = job.title if job else "Unknown Position"
        
        # Parse interviewers JSON if it exists
        interviewers = []
        if interview.interviewers:
            try:
                if isinstance(interview.interviewers, str):
                    interviewers = json.loads(interview.interviewers)
                elif isinstance(interview.interviewers, list):
                    interviewers = interview.interviewers
            except (json.JSONDecodeError, TypeError):
                interviewers = []
        
        results.append({
             "id": interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "candidateEducation":candidate.education, 
        "candidateExperience":candidate.experience,
        "candidateSkills":candidate.technicalSkills,
        "candidateResume":candidate.resume,
        "candidatePortfolio":candidate.portfolio,
        "candidateLinkedIn":candidate.linkedin,
        "candidateGitHub":candidate.github,
        "candidateLocation":candidate.location,

        "applicationId": application.id if application else None,
        "coverLetter":application.coverLetter,

        "jobId": interview.jobId,  # ✅ Added jobId to response
        "jobTitle": job_title,
        "jobDepartment":job.department,
        "jobDescription":job.description,
        "jobType":job.employmentType,
        "jobResponsibility":job.responsibilities,
        "jobSkills":job.skills,
        "jobEducation":job.education,
        "jobCertificates":job.certifications,
        "jobPublished":job.publishedAt,
        "interviewType": interview.type,
        "status": interview.status,
        "scheduledAt": interview.scheduledAt,
        "duration": interview.duration,
        "timezone": interview.timezone,
        "interviewers": interviewers,
        "meetingLink": interview.meetingLink,
        "location": interview.location,
        "notes": interview.notes,
        "feedback": interview.feedback,
        "invitationSent": interview.invitationSent,
        "joinToken": interview.joinToken,
        "tokenExpiry": interview.tokenExpiry,
        "createdAt": interview.createdAt,
        "updatedAt": interview.updatedAt
        })
    
    return [InterviewResponse(**result) for result in results]

@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """Get a specific interview by ID"""
    db = get_db()
    
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True
                }
            },
            "job": True  # ✅ Added direct job include
        }
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    candidate = interview.candidate
    application = interview.application
    job = interview.job or (application.job if application else None)
    job_title = job.title if job else "Unknown Position"
    
    # Parse interviewers JSON if it exists
    interviewers = []
    if interview.interviewers:
        try:
            if isinstance(interview.interviewers, str):
                interviewers = json.loads(interview.interviewers)
            elif isinstance(interview.interviewers, list):
                interviewers = interview.interviewers
        except (json.JSONDecodeError, TypeError):
            interviewers = []
    
    response = {
        "id": interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "candidateEducation":candidate.education, 
        "candidateExperience":candidate.experience,
        "candidateSkills":candidate.technicalSkills,
        "candidateResume":candidate.resume,
        "candidatePortfolio":candidate.portfolio,
        "candidateLinkedIn":candidate.linkedin,
        "candidateGitHub":candidate.github,
        "candidateLocation":candidate.location,

        "applicationId": application.id if application else None,
        "coverLetter":application.coverLetter,

        "jobId": interview.jobId,  # ✅ Added jobId to response
        "jobTitle": job_title,
        "jobDepartment":job.department,
        "jobDescription":job.description,
        "jobType":job.employmentType,
        "jobResponsibility":job.responsibilities,
        "jobSkills":job.skills,
        "jobEducation":job.education,
        "jobCertificates":job.certifications,
        "jobPublished":job.publishedAt,
        "interviewType": interview.type,
        "status": interview.status,
        "scheduledAt": interview.scheduledAt,
        "duration": interview.duration,
        "timezone": interview.timezone,
        "interviewers": interviewers,
        "meetingLink": interview.meetingLink,
        "location": interview.location,
        "notes": interview.notes,
        "feedback": interview.feedback,
        "invitationSent": interview.invitationSent,
        "joinToken": interview.joinToken,
        "tokenExpiry": interview.tokenExpiry,
        "createdAt": interview.createdAt,
        "updatedAt": interview.updatedAt
    }
    
    return InterviewResponse(**response)

@router.put("/{interview_id}/reschedule", response_model=InterviewResponse)
async def reschedule_interview(
    interview_id: str,
    reschedule_data: InterviewRescheduleRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Reschedule an interview"""
    db = get_db()
    
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True
                }
            },
            "job": True
        }
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Parse new date and time
    try:
        new_scheduled_datetime = datetime.strptime(
            f"{reschedule_data.newDate} {reschedule_data.newTime}", 
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time."
        )
    
    # Update interview
    updated_interview = await db.interview.update(
        where={"id": interview_id},
        data={
            "scheduledAt": new_scheduled_datetime,
            "status": InterviewStatus.RESCHEDULED,
            "notes": f"{interview.notes or ''}\n\nRescheduled: {reschedule_data.reason}"
        }
    )
    
    candidate = interview.candidate
    application = interview.application
    job = interview.job or (application.job if application else None)
    job_title = job.title if job else "Unknown Position"
    
    # Parse interviewers JSON if it exists
    interviewers = []
    if updated_interview.interviewers:
        try:
            if isinstance(updated_interview.interviewers, str):
                interviewers = json.loads(updated_interview.interviewers)
            elif isinstance(updated_interview.interviewers, list):
                interviewers = updated_interview.interviewers
        except (json.JSONDecodeError, TypeError):
            interviewers = []
    # Log activity
    if candidate and job:
       await ActivityHelpers.log_interview_rescheduled(
           user_id=current_user.id,
           interview_id=updated_interview.id,
           candidate_name=candidate.name,
           job_title=job.title,
           new_date=new_scheduled_datetime
       )
    
    response = {
        "id": updated_interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "applicationId": application.id if application else None,
        "jobId": updated_interview.jobId,  # ✅ Added jobId to response
        "jobTitle": job_title,
        "interviewType": updated_interview.type,
        "status": updated_interview.status,
        "scheduledAt": updated_interview.scheduledAt,
        "duration": updated_interview.duration,
        "timezone": updated_interview.timezone,
        "interviewers": interviewers,
        "meetingLink": updated_interview.meetingLink,
        "location": updated_interview.location,
        "notes": updated_interview.notes,
        "feedback": updated_interview.feedback,
        "invitationSent": updated_interview.invitationSent,
        "joinToken": updated_interview.joinToken,
        "tokenExpiry": updated_interview.tokenExpiry,
        "createdAt": updated_interview.createdAt,
        "updatedAt": updated_interview.updatedAt
    }
    
    return InterviewResponse(**response)

@router.put("/{interview_id}/status", response_model=InterviewResponse)
async def update_interview_status(
    interview_id: str,
    new_status: InterviewStatus,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update interview status"""
    db = get_db()
    
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True
                }
            },
            "job": True
        }
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Update interview status
    update_data = {"status": new_status}
    
    # If status is COMPLETED, set completedAt
    if new_status == InterviewStatus.COMPLETED:
        update_data["completedAt"] = datetime.utcnow()
    
    updated_interview = await db.interview.update(
        where={"id": interview_id},
        data=update_data
    )
    
    candidate = interview.candidate
    application = interview.application
    job = interview.job or (application.job if application else None)
    job_title = job.title if job else "Unknown Position"
    
    # Parse interviewers JSON if it exists
    interviewers = []
    if updated_interview.interviewers:
        try:
            if isinstance(updated_interview.interviewers, str):
                interviewers = json.loads(updated_interview.interviewers)
            elif isinstance(updated_interview.interviewers, list):
                interviewers = updated_interview.interviewers
        except (json.JSONDecodeError, TypeError):
            interviewers = []
    # Log activity based on new status
    if candidate and job:
       if new_status == InterviewStatus.SCHEDULED:
           await ActivityHelpers.log_interview_scheduled(
               user_id=current_user.id,
               interview_id=updated_interview.id,
               candidate_name=candidate.name,
               job_title=job.title
           )
       if new_status == InterviewStatus.COMPLETED:
           await ActivityHelpers.log_interview_completed(
               user_id=current_user.id,
               interview_id=updated_interview.id,
               candidate_name=candidate.name,
               job_title=job.title
           )
       elif new_status == InterviewStatus.CANCELLED:
           await ActivityHelpers.log_interview_cancelled(
               user_id=current_user.id,
               interview_id=updated_interview.id,
               candidate_name=candidate.name,
               job_title=job.title
           )
       

    response = {
        "id": updated_interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "applicationId": application.id if application else None,
        "jobId": updated_interview.jobId,  # ✅ Added jobId to response
        "jobTitle": job_title,
        "interviewType": updated_interview.type,
        "status": updated_interview.status,
        "scheduledAt": updated_interview.scheduledAt,
        "duration": updated_interview.duration,
        "timezone": updated_interview.timezone,
        "interviewers": interviewers,
        "meetingLink": updated_interview.meetingLink,
        "location": updated_interview.location,
        "notes": updated_interview.notes,
        "feedback": updated_interview.feedback,
        "invitationSent": updated_interview.invitationSent,
        "joinToken": updated_interview.joinToken,
        "tokenExpiry": updated_interview.tokenExpiry,
        "createdAt": updated_interview.createdAt,
        "updatedAt": updated_interview.updatedAt
    }
    
    return InterviewResponse(**response)

@router.post("/{interview_id}/feedback", response_model=InterviewResponse)
async def submit_interview_feedback(
    interview_id: str,
    feedback_data: InterviewFeedbackRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Submit feedback for an interview"""
    db = get_db()
    
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True
                }
            },
            "job": True
        }
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Check if interview is completed
    if interview.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback can only be submitted for completed interviews"
        )
    
    # Prepare feedback data
    feedback = {
        "rating": feedback_data.rating,
        "technicalSkills": feedback_data.technicalSkills,
        "communicationSkills": feedback_data.communicationSkills,
        "culturalFit": feedback_data.culturalFit,
        "overallRecommendation": feedback_data.overallRecommendation,
        "strengths": feedback_data.strengths,
        "weaknesses": feedback_data.weaknesses,
        "detailedFeedback": feedback_data.detailedFeedback,
        "nextSteps": feedback_data.nextSteps,
        "submittedBy": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role
        },
        "submittedAt": datetime.utcnow().isoformat()
    }
    
    # Update interview with feedback
    updated_interview = await db.interview.update(
        where={"id": interview_id},
        data={
            "feedback": feedback,
            "rating": feedback_data.rating,
            "recommendation": feedback_data.overallRecommendation
        }
    )
    
    candidate = interview.candidate
    application = interview.application
    job = interview.job or (application.job if application else None)
    job_title = job.title if job else "Unknown Position"
    
    # Parse interviewers JSON if it exists
    interviewers = []
    if updated_interview.interviewers:
        try:
            if isinstance(updated_interview.interviewers, str):
                interviewers = json.loads(updated_interview.interviewers)
            elif isinstance(updated_interview.interviewers, list):
                interviewers = updated_interview.interviewers
        except (json.JSONDecodeError, TypeError):
            interviewers = []
    
    response = {
        "id": updated_interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "applicationId": application.id if application else None,
        "jobId": updated_interview.jobId,  # ✅ Added jobId to response
        "jobTitle": job_title,
        "interviewType": updated_interview.type,
        "status": updated_interview.status,
        "scheduledAt": updated_interview.scheduledAt,
        "duration": updated_interview.duration,
        "timezone": updated_interview.timezone,
        "interviewers": interviewers,
        "meetingLink": updated_interview.meetingLink,
        "location": updated_interview.location,
        "notes": updated_interview.notes,
        "feedback": updated_interview.feedback,
        "invitationSent": updated_interview.invitationSent,
        "joinToken": updated_interview.joinToken,
        "tokenExpiry": updated_interview.tokenExpiry,
        "createdAt": updated_interview.createdAt,
        "updatedAt": updated_interview.updatedAt
    }
    
    return InterviewResponse(**response)

@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete an interview"""
    db = get_db()
    
    interview = await db.interview.find_unique(where={"id": interview_id})
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    await db.interview.delete(where={"id": interview_id})
    
    return {"message": "Interview deleted successfully"}


@router.post("/interview/{interview_id}/auto-evaluate", response_model=dict)
async def auto_evaluate_interview(
    interview_id: str,
    knowledge_level: str = Query("intermediate", description="Knowledge level: beginner, intermediate, advanced"),
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    db = get_db()

    try:
        # Step 1: Validate interview and auth
        interview = await db.interview.find_unique(
            where={"id": interview_id},
            include={"user": True}
        )
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        if isinstance(auth_data, dict) and "interview" in auth_data:
            if auth_data["interview"].id != interview.id:
                raise HTTPException(status_code=403, detail="Not authorized")
        elif isinstance(auth_data, UserResponse):
            if interview.userId != auth_data.id:
                raise HTTPException(status_code=403, detail="Not authorized")

        # Step 2: Fetch existing evaluations
        questionsEvaluation = await db.evaluation.find_many(where={"interviewId": interview_id})
        if not questionsEvaluation:
            raise HTTPException(status_code=400, detail="No questions found")

        evaluations = []
        total_scores = {
            "factualAccuracy": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
            "coherence": 0.0,
            "score": 0.0,
        }
        count = 0
        final_evaluations = []

        def rating_to_score(rating: str) -> float:
            mapping = {"Poor": 1.0, "Fair": 2.0, "Good": 3.0, "Excellent": 4.0}
            return mapping.get(rating.strip().title(), 2.0)

        for q in questionsEvaluation:
            count += 1
            if q.factualAccuracy and q.evaluatedAt:
                evaluations.append({
                    "questionId": q.id,
                    "questionText": q.questionText,
                    "answerText": q.answerText,
                    "evaluation": {
                        "factualAccuracy": q.factualAccuracy,
                        "factualAccuracyExplanation": q.factualAccuracyExplanation,
                        "completeness": q.completeness,
                        "completenessExplanation": q.completenessExplanation,
                        "relevance": q.relevance,
                        "relevanceExplanation": q.relevanceExplanation,
                        "coherence": q.coherence,
                        "coherenceExplanation": q.coherenceExplanation,
                        "score": q.score,
                        "finalEvaluation": q.finalEvaluation
                    }
                })
                total_scores["factualAccuracy"] += rating_to_score(q.factualAccuracy)
                total_scores["completeness"] += rating_to_score(q.completeness)
                total_scores["relevance"] += rating_to_score(q.relevance)
                total_scores["coherence"] += rating_to_score(q.coherence)
                total_scores["score"] += q.score or 0
                final_evaluations.append(q.finalEvaluation or "")
            else:
                evaluations.append({
                    "questionId": q.id,
                    "questionText": q.questionText,
                    "note": "Evaluation not available yet",
                    "score": 0.0
                })

        def average(val: float) -> float:
            return round(val / count, 2) if count > 0 else 0.0

        avg_fa = average(total_scores["factualAccuracy"])
        avg_comp = average(total_scores["completeness"])
        avg_rel = average(total_scores["relevance"])
        avg_coh = average(total_scores["coherence"])
        avg_score = average(total_scores["score"])

        if avg_score >= 4.0:
            pass_status = "pass"
            summary_result = "Candidate passed with Excellent performance"
        elif avg_score >= 3.0:
            pass_status = "pass"
            summary_result = "Candidate passed with Good performance"
        elif avg_score >= 2.0:
            pass_status = "borderline"
            summary_result = "Candidate is borderline – Fair performance"
        elif avg_score >= 1.0:
            pass_status = "fail"
            summary_result = "Candidate failed – Poor performance"
        else:
            pass_status = "fail"
            summary_result = "Candidate failed – Incomplete or missing answers"

        # Step 3: Manual safe upsert
        result_data = {
            "evaluatedCount": len([q for q in questionsEvaluation if q.factualAccuracy]),
            "totalQuestions": len(questionsEvaluation),
            "averageFactualAccuracy": avg_fa,
            "averageCompleteness": avg_comp,
            "averageRelevance": avg_rel,
            "averageCoherence": avg_coh,
            "averageScore": avg_score,
            "passStatus": pass_status,
            "summaryResult": summary_result,
            "knowledgeLevel": knowledge_level,
            "recommendations": None
        }

        try:
            existing_result = await db.interviewresult.find_unique(where={"interviewId": interview_id})
            if existing_result:
                await db.interviewresult.update(
                    where={"interviewId": interview_id},
                    data=result_data
                )
            else:
                await db.interviewresult.create(
                    data={
                        **result_data,
                        "interviewId": interview_id,
                        "candidateId": interview.candidateId,
                        "applicationId":interview.applicationId,
                        "jobId": interview.jobId or "Unknown",
                    }
                )
        except Exception as e:
            # fallback if a unique constraint error occurs due to race condition
            if "Unique constraint failed" in str(e):
                await db.interviewresult.update(
                    where={"interviewId": interview_id},
                    data=result_data
                )
            else:
                raise e

        # Log activity
        if interview.candidate and interview.job:
           await ActivityHelpers.log_ai_evaluation_completed(
               user_id= interview.userId,
               interview_id=interview.id,
               candidate_name=interview.candidate.name,
               job_title=interview.job.title,
               score=avg_score
           )
        # Step 4: Return evaluation summary
        return {
            "success": True,
            "interviewId": interview_id,
            "evaluatedCount": len(evaluations),
            "averageFactualAccuracy": avg_fa,
            "averageCompleteness": avg_comp,
            "averageRelevance": avg_rel,
            "averageCoherence": avg_coh,
            "averageScore": avg_score,
            "passStatus": pass_status,
            "summaryResult": summary_result,
            "evaluations": evaluations
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.get("/interview/{interview_id}/result", response_model=InterviewResultWithDetailsResponse)
async def get_interview_result(
    interview_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get interview result by interview ID"""
    db = get_db()
    
    try:
        # Step 1: Validate interview exists and auth
        interview = await db.interview.find_unique(
            where={"id": interview_id},
            include={"user": True}
        )
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        # Check authorization - ensure user owns this interview
        if interview.userId != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this interview result")

        # Step 2: Get interview result
        interview_result = await db.interviewresult.find_unique(
            where={"interviewId": interview_id}
        )
        
        if not interview_result:
            raise HTTPException(status_code=404, detail="Interview result not found")

        # Step 3: Get evaluations for detailed response
        evaluations = await db.evaluation.find_many(
            where={"interviewId": interview_id},
            # order_by={"createdAt": "asc"}
        )

        # Step 4: Build detailed evaluations response
        detailed_evaluations = []
        for evaluation in evaluations:
            detailed_evaluations.append({
                "id": evaluation.id,
                "questionText": evaluation.questionText,
                "answerText": evaluation.answerText,
                "interviewId": evaluation.interviewId,
                "expectedAnswerFormat": None,  # Not stored in evaluation table
                "factualAccuracy": evaluation.factualAccuracy,
                "factualAccuracyExplanation": evaluation.factualAccuracyExplanation,
                "completeness": evaluation.completeness,
                "completenessExplanation": evaluation.completenessExplanation,
                "relevance": evaluation.relevance,
                "relevanceExplanation": evaluation.relevanceExplanation,
                "coherence": evaluation.coherence,
                "coherenceExplanation": evaluation.coherenceExplanation,
                "score": evaluation.score,
                "inputTokens": evaluation.inputTokens,
                "outputTokens": evaluation.outputTokens,
                "finalEvaluation": evaluation.finalEvaluation,
                "createdAt": evaluation.createdAt,
                "updatedAt": evaluation.updatedAt,
                "answeredAt": None,  # Not available in evaluation table
                "evaluatedAt": evaluation.evaluatedAt
            })

        

        # Step 5: Build final response
        response = {
            "id": interview_result.id,
            "interviewId": interview_result.interviewId,
            "candidateId": interview_result.candidateId,
            "applicationId":interview_result.applicationId,
            "jobId": interview_result.jobId,
            "evaluatedCount": interview_result.evaluatedCount,
            "totalQuestions": interview_result.totalQuestions,
            "averageFactualAccuracy": interview_result.averageFactualAccuracy,
            "averageCompleteness": interview_result.averageCompleteness,
            "averageRelevance": interview_result.averageRelevance,
            "averageCoherence": interview_result.averageCoherence,
            "averageScore": interview_result.averageScore,
            "passStatus": interview_result.passStatus,
            "summaryResult": interview_result.summaryResult,
            "knowledgeLevel": interview_result.knowledgeLevel,
            "recommendations": interview_result.recommendations,
            "createdAt": interview_result.createdAt,
            "updatedAt": interview_result.updatedAt,
            "evaluations": detailed_evaluations
        }

        return InterviewResultWithDetailsResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching interview result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch interview result: {str(e)}")



@router.post("/interview/{interview_id}/send-result")
async def send_interview_result_email(
    interview_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Send interview result to candidate by email using candidateId"""
    db = get_db()

    try:
        # Step 1: Fetch interview
        interview = await db.interview.find_unique(where={"id": interview_id})
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        if interview.userId != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Step 2: Fetch interview result
        result = await db.interviewresult.find_unique(
            where={"interviewId": interview_id}
        )
        if not result:
            raise HTTPException(status_code=404, detail="Interview result not found")

        # Step 3: Fetch candidate info from candidate table
        candidate = await db.candidate.find_unique(where={"id": result.candidateId})
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Step 4: Fetch job info
        job = await db.job.find_unique(where={"id": result.jobId}) if result.jobId else None

        # Step 5: Send email
        email_service = EmailService()
        success = email_service.send_individual_result(
            email=candidate.email,
            name=candidate.name,
            organization_name="HireIn",  # or dynamically from user's org if applicable
            invitation_token=None,
            application_status=result.passStatus,
            score=result.averageScore,
            job_title=job.title if job else None,
            department=job.department if job else None,
            interview_date=str(interview.createdAt),
            message=result.summaryResult
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        # Log activity
        if job:
           await ActivityHelpers.log_interview_result_sent(
               user_id=current_user.id,
               interview_id=interview.id,
               candidate_name=candidate.name,
               job_title=job.title
           )

        return JSONResponse(content={"message": "Interview result email sent successfully"}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending interview result: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
