from typing import Optional, Dict, Any
from datetime import datetime
from database import get_db
from models.schemas import UserResponse
from prisma import Json # Import Json type from prisma

class ActivityService:
   """Service for managing user activities and logging system events"""
   
   @staticmethod
   async def log_activity(
       user_id: str,
       activity_type: str,
       title: str,
       description: str,
       entity_id: Optional[str] = None,
       entity_type: Optional[str] = None,
       metadata: Optional[Dict[str, Any]] = None
   ):
       """Log a new activity"""
       db = get_db()
       
       try:
           activity = await db.activity.create(
               data={
                   "type": activity_type,
                   "title": title,
                   "description": description,
                   "user": { # Changed from "userId" to "user" with connect
                       "connect": {"id": user_id}
                   },
                   "entityId": entity_id,
                   "entityType": entity_type,
                   "metadata": Json(metadata) if metadata is not None else Json({}) # Ensure metadata is Json type, handle None
               }
           )
           return activity
       except Exception as e:
           print(f"Error logging activity: {e}")
           return None

# Activity Types Constants
class ActivityTypes:
   # Job related
   JOB_CREATED = "JOB_CREATED"
   JOB_PUBLISHED = "JOB_PUBLISHED"
   JOB_UPDATED = "JOB_UPDATED"
   JOB_CLOSED = "JOB_CLOSED"
   JOB_PAUSED = "JOB_PAUSED"
   JOB_REACTIVATED = "JOB_REACTIVATED"
   JOB_DELETED = "JOB_DELETED" # NEW

   # Application related
   APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
   APPLICATION_REVIEWED = "APPLICATION_REVIEWED"
   APPLICATION_SHORTLISTED = "APPLICATION_SHORTLISTED"
   APPLICATION_REJECTED = "APPLICATION_REJECTED"
   APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED" # NEW
   
   # Interview related
   INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
   INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
   INTERVIEW_CANCELLED = "INTERVIEW_CANCELLED"
   INTERVIEW_RESCHEDULED = "INTERVIEW_RESCHEDULED"
   INTERVIEW_STARTED = "INTERVIEW_STARTED"
   INTERVIEW_FEEDBACK_SUBMITTED = "INTERVIEW_FEEDBACK_SUBMITTED" # NEW
   INTERVIEW_DELETED = "INTERVIEW_DELETED" # NEW
   INTERVIEW_RESULT_SENT = "INTERVIEW_RESULT_SENT" # NEW
   
   # Candidate related
   CANDIDATE_ADDED = "CANDIDATE_ADDED"
   CANDIDATE_UPDATED = "CANDIDATE_UPDATED" # NEW
   CANDIDATE_DELETED = "CANDIDATE_DELETED" # NEW
   CANDIDATE_HIRED = "CANDIDATE_HIRED"
   CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
   CANDIDATE_MOVED_TO_NEXT_STAGE = "CANDIDATE_MOVED_TO_NEXT_STAGE"
   
   # System related
   USER_LOGIN = "USER_LOGIN"
   USER_LOGOUT = "USER_LOGOUT"
   USER_REGISTERED = "USER_REGISTERED" # NEW
   SETTINGS_UPDATED = "SETTINGS_UPDATED"
   PROFILE_UPDATED = "PROFILE_UPDATED"

   # Company related
   COMPANY_CREATED = "COMPANY_CREATED" # NEW
   COMPANY_UPDATED = "COMPANY_UPDATED" # NEW
   COMPANY_DELETED = "COMPANY_DELETED" # NEW
   COMPANY_LOCATION_ADDED = "COMPANY_LOCATION_ADDED" # NEW
   COMPANY_LOCATION_UPDATED = "COMPANY_LOCATION_UPDATED" # NEW
   COMPANY_LOCATION_DELETED = "COMPANY_LOCATION_DELETED" # NEW
   TEAM_MEMBER_INVITED = "TEAM_MEMBER_INVITED" # NEW
   TEAM_MEMBER_UPDATED = "TEAM_MEMBER_UPDATED" # NEW
   TEAM_MEMBER_DELETED = "TEAM_MEMBER_DELETED" # NEW
   
   # AI related
   AI_QUESTIONS_GENERATED = "AI_QUESTIONS_GENERATED"
   AI_EVALUATION_COMPLETED = "AI_EVALUATION_COMPLETED"
   AI_RESUME_ANALYZED = "AI_RESUME_ANALYZED"

# Helper functions for common activities
class ActivityHelpers:
   
   @staticmethod
   async def log_job_created(user_id: str, job_id: str, job_title: str):
       """Log when a new job is created"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.JOB_CREATED,
           title="New job posted",
           description=f"Created job posting for {job_title}",
           entity_id=job_id,
           entity_type="job"
       )
   
   @staticmethod
   async def log_job_updated(user_id: str, job_id: str, job_title: str):
       """Log when a job is updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.JOB_UPDATED,
           title="Job updated",
           description=f"Updated job posting for {job_title}",
           entity_id=job_id,
           entity_type="job"
       )

   @staticmethod
   async def log_job_deleted(user_id: str, job_id: str, job_title: str):
       """Log when a job is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.JOB_DELETED,
           title="Job deleted",
           description=f"Deleted job posting for {job_title}",
           entity_id=job_id,
           entity_type="job"
       )

   @staticmethod
   async def log_job_published(user_id: str, job_id: str, job_title: str):
       """Log when a job is published"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.JOB_PUBLISHED,
           title="Job published",
           description=f"Published job posting for {job_title}",
           entity_id=job_id,
           entity_type="job"
       )

   @staticmethod
   async def log_application_received(user_id: str, application_id: str, candidate_name: str, job_title: str):
       """Log when a new application is received"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.APPLICATION_RECEIVED,
           title="New application received",
           description=f"{candidate_name} applied for {job_title} position",
           entity_id=application_id,
           entity_type="application"
       )
   
   @staticmethod
   async def log_application_status_changed(user_id: str, application_id: str, candidate_name: str, job_title: str, new_status: str):
       """Log when application status changes"""
       status_messages = {
           "APPLIED": "applied for",
           "SCREENING": "moved to screening stage for",
           "INTERVIEW": "moved to interview stage for", 
           "OFFER": "received job offer for",
           "HIRED": "was hired for",
           "REJECTED": "was rejected for"
       }
       
       message = status_messages.get(new_status, f"status changed to {new_status} for")
       
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.APPLICATION_STATUS_CHANGED,
           title="Application status updated",
           description=f"{candidate_name} {message} {job_title}",
           entity_id=application_id,
           entity_type="application",
           metadata={"new_status": new_status}
       )

   @staticmethod
   async def log_interview_scheduled(user_id: str, interview_id: str, candidate_name: str, job_title: str, scheduled_date: datetime):
       """Log when an interview is scheduled"""
       date_str = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_SCHEDULED,
           title="Interview scheduled",
           description=f"Interview scheduled with {candidate_name} for {job_title} on {date_str}",
           entity_id=interview_id,
           entity_type="interview"
       )
   
   @staticmethod
   async def log_interview_completed(user_id: str, interview_id: str, candidate_name: str, job_title: str):
       """Log when an interview is completed"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_COMPLETED,
           title="Interview completed",
           description=f"Completed interview with {candidate_name} for {job_title}",
           entity_id=interview_id,
           entity_type="interview"
       )

   @staticmethod
   async def log_interview_rescheduled(user_id: str, interview_id: str, candidate_name: str, job_title: str, new_date: datetime):
       """Log when an interview is rescheduled"""
       date_str = new_date.strftime("%B %d, %Y at %I:%M %p")
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_RESCHEDULED,
           title="Interview rescheduled",
           description=f"Interview with {candidate_name} for {job_title} rescheduled to {date_str}",
           entity_id=interview_id,
           entity_type="interview"
       )

   @staticmethod
   async def log_interview_cancelled(user_id: str, interview_id: str, candidate_name: str, job_title: str):
       """Log when an interview is cancelled"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_CANCELLED,
           title="Interview cancelled",
           description=f"Interview with {candidate_name} for {job_title} was cancelled",
           entity_id=interview_id,
           entity_type="interview"
       )

   @staticmethod
   async def log_interview_deleted(user_id: str, interview_id: str, candidate_name: str, job_title: str):
       """Log when an interview is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_DELETED,
           title="Interview deleted",
           description=f"Interview with {candidate_name} for {job_title} was deleted",
           entity_id=interview_id,
           entity_type="interview"
       )

   @staticmethod
   async def log_interview_feedback_submitted(user_id: str, interview_id: str, candidate_name: str, job_title: str):
       """Log when interview feedback is submitted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_FEEDBACK_SUBMITTED,
           title="Interview feedback submitted",
           description=f"Feedback submitted for {candidate_name}'s interview for {job_title}",
           entity_id=interview_id,
           entity_type="interview"
       )

   @staticmethod
   async def log_interview_result_sent(user_id: str, interview_id: str, candidate_name: str, job_title: str):
       """Log when interview result is sent to candidate"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.INTERVIEW_RESULT_SENT,
           title="Interview result sent",
           description=f"Interview result sent to {candidate_name} for {job_title}",
           entity_id=interview_id,
           entity_type="interview"
       )
   
   @staticmethod
   async def log_candidate_added(user_id: str, candidate_id: str, candidate_name: str):
       """Log when a new candidate is added"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.CANDIDATE_ADDED,
           title="New candidate added",
           description=f"Added new candidate: {candidate_name}",
           entity_id=candidate_id,
           entity_type="candidate"
       )

   @staticmethod
   async def log_candidate_updated(user_id: str, candidate_id: str, candidate_name: str):
       """Log when a candidate is updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.CANDIDATE_UPDATED,
           title="Candidate updated",
           description=f"Updated candidate details for {candidate_name}",
           entity_id=candidate_id,
           entity_type="candidate"
       )

   @staticmethod
   async def log_candidate_deleted(user_id: str, candidate_id: str, candidate_name: str):
       """Log when a candidate is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.CANDIDATE_DELETED,
           title="Candidate deleted",
           description=f"Deleted candidate: {candidate_name}",
           entity_id=candidate_id,
           entity_type="candidate"
       )
   
   @staticmethod
   async def log_candidate_hired(user_id: str, candidate_id: str, candidate_name: str, job_title: str):
       """Log when a candidate is hired"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.CANDIDATE_HIRED,
           title="Candidate hired",
           description=f"{candidate_name} has been hired for {job_title} position",
           entity_id=candidate_id,
           entity_type="candidate"
       )
   
   @staticmethod
   async def log_ai_questions_generated(user_id: str, interview_id: str, job_title: str, question_count: int):
       """Log when AI questions are generated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.AI_QUESTIONS_GENERATED,
           title="AI questions generated",
           description=f"Generated {question_count} AI interview questions for {job_title}",
           entity_id=interview_id,
           entity_type="interview",
           metadata={"question_count": question_count}
       )

   @staticmethod
   async def log_ai_evaluation_completed(user_id: str, interview_id: str, candidate_name: str, job_title: str, score: float):
       """Log when AI evaluation is completed"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.AI_EVALUATION_COMPLETED,
           title="AI evaluation completed",
           description=f"AI evaluation completed for {candidate_name}'s interview for {job_title} with score {score}",
           entity_id=interview_id,
           entity_type="interview",
           metadata={"score": score}
       )

   @staticmethod
   async def log_user_login(user_id: str, user_email: str):
       """Log when a user logs in"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.USER_LOGIN,
           title="User logged in",
           description=f"User {user_email} logged in",
           entity_id=user_id,
           entity_type="user"
       )

   @staticmethod
   async def log_user_registered(user_id: str, user_email: str):
       """Log when a new user registers"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.USER_REGISTERED,
           title="New user registered",
           description=f"New user {user_email} registered",
           entity_id=user_id,
           entity_type="user"
       )

   @staticmethod
   async def log_settings_updated(user_id: str, setting_type: str):
       """Log when user settings are updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.SETTINGS_UPDATED,
           title="Settings updated",
           description=f"User settings for {setting_type} updated",
           entity_id=user_id,
           entity_type="user_settings",
           metadata={"setting_type": setting_type}
       )

   @staticmethod
   async def log_company_created(user_id: str, company_id: str, company_name: str):
       """Log when a company profile is created"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_CREATED,
           title="Company profile created",
           description=f"Created company profile for {company_name}",
           entity_id=company_id,
           entity_type="company"
       )

   @staticmethod
   async def log_company_updated(user_id: str, company_id: str, company_name: str):
       """Log when a company profile is updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_UPDATED,
           title="Company profile updated",
           description=f"Updated company profile for {company_name}",
           entity_id=company_id,
           entity_type="company"
       )

   @staticmethod
   async def log_company_deleted(user_id: str, company_id: str, company_name: str):
       """Log when a company profile is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_DELETED,
           title="Company profile deleted",
           description=f"Deleted company profile for {company_name}",
           entity_id=company_id,
           entity_type="company"
       )

   @staticmethod
   async def log_company_location_added(user_id: str, location_id: str, location_name: str, company_name: str):
       """Log when a company location is added"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_LOCATION_ADDED,
           title="Company location added",
           description=f"Added new location '{location_name}' for {company_name}",
           entity_id=location_id,
           entity_type="company_location"
       )

   @staticmethod
   async def log_company_location_updated(user_id: str, location_id: str, location_name: str, company_name: str):
       """Log when a company location is updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_LOCATION_UPDATED,
           title="Company location updated",
           description=f"Updated location '{location_name}' for {company_name}",
           entity_id=location_id,
           entity_type="company_location"
       )

   @staticmethod
   async def log_company_location_deleted(user_id: str, location_id: str, location_name: str, company_name: str):
       """Log when a company location is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.COMPANY_LOCATION_DELETED,
           title="Company location deleted",
           description=f"Deleted location '{location_name}' for {company_name}",
           entity_id=location_id,
           entity_type="company_location"
       )

   @staticmethod
   async def log_team_member_invited(user_id: str, invited_member_email: str, invited_by_name: str):
       """Log when a team member is invited"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.TEAM_MEMBER_INVITED,
           title="Team member invited",
           description=f"{invited_by_name} invited {invited_member_email} to the team",
           entity_type="team_member",
           metadata={"invited_email": invited_member_email}
       )

   @staticmethod
   async def log_team_member_updated(user_id: str, member_id: str, member_name: str):
       """Log when a team member's details are updated"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.TEAM_MEMBER_UPDATED,
           title="Team member updated",
           description=f"Updated details for team member: {member_name}",
           entity_id=member_id,
           entity_type="team_member"
       )

   @staticmethod
   async def log_team_member_deleted(user_id: str, member_id: str, member_name: str):
       """Log when a team member is deleted"""
       await ActivityService.log_activity(
           user_id=user_id,
           activity_type=ActivityTypes.TEAM_MEMBER_DELETED,
           title="Team member deleted",
           description=f"Removed team member: {member_name}",
           entity_id=member_id,
           entity_type="team_member"
       )
