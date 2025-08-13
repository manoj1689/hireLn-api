import calendar
from fastapi import APIRouter, Depends
from typing import List
from database import get_db
from models.schemas import (
    DashboardMetrics, MetricWithChange, RecruitmentTrend, PipelineStage, 
    ActivityItem, UserResponse
)
from auth.dependencies import get_current_user
from datetime import datetime, timedelta,timezone


router = APIRouter()

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(current_user: UserResponse = Depends(get_current_user)):
    """Get dashboard metrics with % change from last month"""
    db = get_db()

    # Time ranges
    now = datetime.utcnow()
    start_current_month = now.replace(day=1)
    start_last_month = (start_current_month - timedelta(days=1)).replace(day=1)
    end_last_month = start_current_month

    # 1. Total Jobs
    total_jobs_current = await db.job.count(where={"createdAt": {"gte": start_current_month}})
    total_jobs_last = await db.job.count(
        where={"createdAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    job_change = calculate_change(total_jobs_current, total_jobs_last)

    # 2. Active Candidates (applied in last 30 days vs previous 30 days)
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    active_current = await db.application.count(where={"appliedAt": {"gte": thirty_days_ago}})
    active_last = await db.application.count(
        where={"appliedAt": {"gte": sixty_days_ago, "lt": thirty_days_ago}}
    )
    active_change = calculate_change(active_current, active_last)

    # 3. Hiring Success Rate (HIRED / total applications)
    total_applications = await db.application.count()
    hired_applications = await db.application.count(where={"status": "HIRED"})
    hiring_success_rate = (hired_applications / total_applications * 100) if total_applications else 0

    # Last month success rate
    total_apps_last = await db.application.count(
        where={"appliedAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    hired_apps_last = await db.application.count(
        where={"appliedAt": {"gte": start_last_month, "lt": end_last_month}, "status": "HIRED"}
    )
    success_rate_last = (hired_apps_last / total_apps_last * 100) if total_apps_last else 0
    success_change = calculate_change(hiring_success_rate, success_rate_last)

    # 4. AI Interviews Completed
    ai_interviews_current = await db.interview.count(
        where={"status": "COMPLETED", "createdAt": {"gte": start_current_month}}
    )
    ai_interviews_last = await db.interview.count(
        where={"status": "COMPLETED", "createdAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    ai_change = calculate_change(ai_interviews_current, ai_interviews_last)

    # 5. Average time to hire — Placeholder logic (replace with actual calc)
    avg_time_to_hire = 1
    avg_time_last = 2  # mock last month
    avg_time_change = calculate_change(avg_time_to_hire, avg_time_last)

    return DashboardMetrics(
        totalJobs=MetricWithChange(value=total_jobs_current, change=job_change),
        activeCandidates=MetricWithChange(value=active_current, change=active_change),
        hiringSuccessRate=MetricWithChange(value=round(hiring_success_rate, 1), change=round(success_change, 1)),
        avgTimeToHire=MetricWithChange(value=avg_time_to_hire, change=avg_time_change),
        aiInterviewsCompleted=MetricWithChange(value=ai_interviews_current, change=ai_change),
    )

# Helper function
def calculate_change(current: int | float, previous: int | float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


@router.get("/recruitment-trends", response_model=List[RecruitmentTrend])
async def get_recruitment_trends(current_user: UserResponse = Depends(get_current_user)):
    """Get recruitment trends data"""
    db = get_db()
    
    # Get the last 6 months of data
    current_date = datetime.utcnow()
    
    trends = []
    for i in range(5, -1, -1):  # Last 6 months
        # Calculate the start and end of the month
        target_date = current_date - timedelta(days=30 * i)
        year = target_date.year
        month = target_date.month
        
        # Get first day of the month
        start_of_month = datetime(year, month, 1)
        
        # Get last day of the month
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Query applications for this month
        applications_count = await db.application.count(
            where={
                "appliedAt": {
                    "gte": start_of_month,
                    "lte": end_of_month
                }
            }
        )
        
        # Get month name
        month_name = calendar.month_abbr[month]
        
        trends.append(RecruitmentTrend(
            month=month_name,
            applications=applications_count
        ))
    
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
        # order_by={"createdAt": "desc"}
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
            time=format_time_ago(activity.createdAt)
        )
        for activity in activities
    ]


@router.get("/department-stats", response_model=List[dict])
async def get_department_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get department-wise job statistics"""
    db = get_db()
    
    # Get department-wise job counts using raw query
    # This will group jobs by department and count them
    departments = await db.query_raw("""
        SELECT department, COUNT(*) as job_count
        FROM Jobs
        GROUP BY department
        ORDER BY job_count DESC
    """)
    
    # Convert the result to a list of dictionaries
    department_stats = []
    for dept in departments:
        department_stats.append({
            "department": dept["department"],
            "jobCount": dept["job_count"]
        })
    
    return department_stats

def format_time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    minutes = int(seconds // 60)
    hours = int(minutes // 60)
    days = int(hours // 24)

    if seconds < 60:
        return "just now"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{days} day{'s' if days != 1 else ''} ago"