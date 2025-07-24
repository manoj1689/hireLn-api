from fastapi import APIRouter, Depends
from typing import List
from database import get_db
from models.schemas import (
    DashboardMetrics, RecruitmentTrend, PipelineStage, 
    ActivityItem, UserResponse
)
from auth.dependencies import get_current_user
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(current_user: UserResponse = Depends(get_current_user)):
    """Get dashboard metrics"""
    db = get_db()
    
    # Get total jobs
    total_jobs = await db.job.count()
    
    # Get active candidates (candidates with applications in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_candidates = await db.application.count(
        where={"appliedAt": {"gte": thirty_days_ago}}
    )
    
    # Calculate hiring success rate (hired / total applications * 100)
    total_applications = await db.application.count()
    hired_applications = await db.application.count(where={"status": "HIRED"})
    hiring_success_rate = (hired_applications / total_applications * 100) if total_applications > 0 else 0
    
    # Average time to hire (mock data for now)
    avg_time_to_hire = 1
    
    # AI interviews completed (mock data for now)
    ai_interviews_completed = await db.interview.count(where={"status":"COMPLETED"})
    
    return DashboardMetrics(
        totalJobs=total_jobs,
        activeCandidates=active_candidates,
        hiringSuccessRate=round(hiring_success_rate, 1),
        avgTimeToHire=avg_time_to_hire,
        aiInterviewsCompleted=ai_interviews_completed
    )

@router.get("/recruitment-trends", response_model=List[RecruitmentTrend])
async def get_recruitment_trends(current_user: UserResponse = Depends(get_current_user)):
    """Get recruitment trends data"""
    # Mock data for now - in a real app, you'd query the database for monthly application counts
    trends = [
        RecruitmentTrend(month="Jan", applications=150),
        RecruitmentTrend(month="Feb", applications=230),
        RecruitmentTrend(month="Mar", applications=224),
        RecruitmentTrend(month="Apr", applications=218),
        RecruitmentTrend(month="May", applications=135),
        RecruitmentTrend(month="Jun", applications=147),
    ]
    return trends

@router.get("/pipeline", response_model=List[PipelineStage])
async def get_pipeline_stages(current_user: UserResponse = Depends(get_current_user)):
    """Get hiring pipeline data"""
    db = get_db()
    
    # Get counts for each stage
    applied_count = await db.application.count(where={"status": "APPLIED"})
    screening_count = await db.application.count(where={"status": "SCREENING"})
    interview_count = await db.application.count(where={"status": "INTERVIEW"})
    offer_count = await db.application.count(where={"status": "OFFER"})
    hired_count = await db.application.count(where={"status": "HIRED"})
    
    total = applied_count + screening_count + interview_count + offer_count + hired_count
    
    if total == 0:
        # Return mock data if no applications exist
        return [
            PipelineStage(stage="Applied", count=0, percentage=0),
            PipelineStage(stage="Screening", count=0, percentage=0),
            PipelineStage(stage="Interview", count=0, percentage=0),
            PipelineStage(stage="Offer", count=0, percentage=0),
            PipelineStage(stage="Hired", count=0, percentage=0),
        ]
    
    return [
        PipelineStage(
            stage="Applied", 
            count=applied_count, 
            percentage=round(applied_count / total * 100) if total > 0 else 0
        ),
        PipelineStage(
            stage="Screening", 
            count=screening_count, 
            percentage=round(screening_count / total * 100) if total > 0 else 0
        ),
        PipelineStage(
            stage="Interview", 
            count=interview_count, 
            percentage=round(interview_count / total * 100) if total > 0 else 0
        ),
        PipelineStage(
            stage="Offer", 
            count=offer_count, 
            percentage=round(offer_count / total * 100) if total > 0 else 0
        ),
        PipelineStage(
            stage="Hired", 
            count=hired_count, 
            percentage=round(hired_count / total * 100) if total > 0 else 0
        ),
    ]

@router.get("/activities", response_model=List[ActivityItem])
async def get_recent_activities(current_user: UserResponse = Depends(get_current_user)):
    """Get recent activities"""
    db = get_db()
    
    activities = await db.activity.find_many(
        take=10,
        order_by={"createdAt": "desc"}
    )
    
    # If no activities, return mock data
    if not activities:
        return [
            ActivityItem(
                id="1",
                type="APPLICATION_RECEIVED",
                title="New application received",
                description="Sarah Wilson applied for Senior Product Designer position",
                time="10 minutes ago"
            ),
            ActivityItem(
                id="2",
                type="INTERVIEW_SCHEDULED",
                title="Interview scheduled",
                description="Technical interview with Michael Chen for Frontend Developer role",
                time="1 hour ago"
            ),
            ActivityItem(
                id="3",
                type="CANDIDATE_HIRED",
                title="Offer accepted",
                description="Jessica Parker accepted the Marketing Manager position",
                time="2 hours ago"
            ),
            ActivityItem(
                id="4",
                type="JOB_CREATED",
                title="New job posted",
                description="Senior Backend Engineer position is now live",
                time="3 hours ago"
            ),
        ]
    
    return [
        ActivityItem(
            id=activity.id,
            type=activity.type,
            title=activity.title,
            description=activity.description,
            time=f"{(datetime.utcnow() - activity.createdAt).days} days ago"
        )
        for activity in activities
    ]
