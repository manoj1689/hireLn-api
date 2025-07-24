from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from database import get_db
from models.schemas import InterviewJoinResponse, InterviewResponse, InterviewStatus
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/join", response_model=InterviewJoinResponse)
async def join_interview(
    interview_id: str = Query(..., description="Interview ID"),
    token: Optional[str] = Query(None, description="Join token")
):
    """Join an interview using interview ID and optional token"""
    db = get_db()
    
    try:
        # Find the interview
        interview = await db.interview.find_unique(
            where={"id": interview_id},
            include={
                "candidate": True,
                "application": {
                    "include": {
                        "job": True
                    }
                }
            }
        )
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Check if token is required and valid
        if interview.joinToken and token != interview.joinToken:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing join token"
            )
        
        # Check if token has expired - ensure both datetimes are timezone-aware
        if interview.tokenExpiry:
            current_time = datetime.now(timezone.utc)
            token_expiry = interview.tokenExpiry
            
            # If tokenExpiry is naive, make it UTC
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            
            if current_time > token_expiry:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Join token has expired"
                )
        
        # Check interview status
        if interview.status in [InterviewStatus.CANCELLED, InterviewStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview is {interview.status.lower()}"
            )
        
        # Update interview status to JOINED if it's SCHEDULED
        if interview.status == InterviewStatus.SCHEDULED:
            await db.interview.update(
                where={"id": interview_id},
                data={"status": InterviewStatus.JOINED}
            )
        
        # Prepare interview response
        candidate = interview.candidate
        application = interview.application
        job_title = application.job.title if application and application.job else "Unknown Position"
        
        # Parse interviewers if they exist
        interviewers = []
        if interview.interviewers:
            try:
                import json
                interviewers = json.loads(interview.interviewers)
            except:
                interviewers = []
        
        interview_response = InterviewResponse(
            id=interview.id,
            candidateId=candidate.id,
            candidateName=candidate.name,
            candidateEmail=candidate.email,
            applicationId=application.id,
            jobId=application.jobId,
            jobTitle=job_title,
            interviewType=interview.type,
            status=InterviewStatus.JOINED,
            scheduledAt=interview.scheduledAt,
            duration=interview.duration,
            timezone=interview.timezone,
            interviewers=interviewers,
            meetingLink=interview.meetingLink,
            location=interview.location,
            notes=interview.notes,
            feedback=interview.feedback,
            calendarEventId=getattr(interview, "calendarEventId", None),
            invitationSent=interview.invitationSent,
            joinToken=interview.joinToken,
            tokenExpiry=interview.tokenExpiry,
            createdAt=interview.createdAt,
            updatedAt=interview.updatedAt
        )

        
        # Generate redirect URL for the frontend
        redirect_url = f"/ai-interview-round?interview_id={interview_id}&token={token}"
        
        return InterviewJoinResponse(
            success=True,
            message="Successfully joined the interview",
            interview=interview_response,
            redirectUrl=redirect_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/confirm/{interview_id}")
async def confirm_interview(
    interview_id: str,
    confirmed: bool = True,
    response_message: Optional[str] = None
):
    """Confirm interview attendance"""
    db = get_db()
    
    try:
        interview = await db.interview.find_unique(where={"id": interview_id})
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Update interview status based on confirmation
        new_status = InterviewStatus.CONFIRMED if confirmed else InterviewStatus.CANCELLED
        
        update_data = {"status": new_status}
        if response_message:
            update_data["notes"] = f"{interview.notes or ''}\n\nCandidate response: {response_message}"
        
        await db.interview.update(
            where={"id": interview_id},
            data=update_data
        )
        
        return {
            "success": True,
            "message": f"Interview {'confirmed' if confirmed else 'cancelled'} successfully",
            "status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{interview_id}/start")
async def start_interview(interview_id: str):
    """Start an interview (update status to IN_PROGRESS)"""
    db = get_db()
    
    try:
        interview = await db.interview.find_unique(where={"id": interview_id})
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Update interview status to IN_PROGRESS with timezone-aware datetime
        await db.interview.update(
            where={"id": interview_id},
            data={
                "status": InterviewStatus.IN_PROGRESS,
                "startedAt": datetime.now(timezone.utc)
            }
        )
        
        return {
            "success": True,
            "message": "Interview started successfully",
            "status": InterviewStatus.IN_PROGRESS
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{interview_id}/complete")
async def complete_interview(interview_id: str):
    """Complete an interview (update status to COMPLETED)"""
    db = get_db()
    
    try:
        interview = await db.interview.find_unique(where={"id": interview_id})
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Update interview status to COMPLETED with timezone-aware datetime
        await db.interview.update(
            where={"id": interview_id},
            data={
                "status": InterviewStatus.COMPLETED,
                "completedAt": datetime.now(timezone.utc)
            }
        )
        
        return {
            "success": True,
            "message": "Interview completed successfully",
            "status": InterviewStatus.COMPLETED
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
