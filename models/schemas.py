from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Optional, List, Union
from datetime import datetime
from enum import Enum
from decimal import Decimal

# Enums
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"
    INDIVIDUAL="INDIVIDUAL"

class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    TEMPORARY = "TEMPORARY"
    INTERNSHIP = "INTERNSHIP"

class JobStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"

class SalaryPeriod(str, Enum):
    yearly = "yearly"
    monthly = "monthly"
    weekly = "weekly"
    hourly = "hourly"

class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    HIRED = "HIRED"
    REJECTED = "REJECTED"

class InterviewType(str, Enum):
    PHONE = "PHONE"
    VIDEO = "VIDEO"
    IN_PERSON = "IN_PERSON"
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    PANEL = "PANEL"

class InterviewStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"
    INVITED = "INVITED"  # When invite is sent but not confirmed
    JOINED = "JOINED"    # When candidate clicks join link

# Registration Step 1 - Basic Information
class UserBasicInfo(BaseModel):
    firstName: str
    lastName: str
    workEmail: EmailStr
    password: str
    confirmPassword: str

# Registration Step 2 - Company Details
class CompanyDetails(BaseModel):
    companyName: str
    companySize: str
    industry: str
    hiringVolume: str
    primaryHiringNeeds: List[str] = []

# Registration Step 3 - Payment Information
class PaymentInfo(BaseModel):
    cardNumber: str
    expirationDate: str
    cvv: str
    billingAddress: str
    city: str
    zipCode: str
    termsAgreement: bool

# Complete Registration
class UserRegistration(BaseModel):
    basicInfo: UserBasicInfo
    companyDetails: CompanyDetails
    paymentInfo: PaymentInfo

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    avatar: Optional[str] = None
    role: UserRole = UserRole.RECRUITER
    companyName: Optional[str] = None
    companySize: Optional[str] = None
    industry: Optional[str] = None
    hiringVolume: Optional[str] = None
    primaryHiringNeeds: List[str] = []

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    name: str  # Computed from firstName + lastName
    createdAt: datetime
    updatedAt: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Step-by-step registration responses
class RegistrationStep1Response(BaseModel):
    message: str
    step: int
    sessionId: str

class RegistrationStep2Response(BaseModel):
    message: str
    step: int
    sessionId: str

class RegistrationCompleteResponse(BaseModel):
    message: str
    data: Token
    trialEndsAt: datetime

# Core Job Schemas
class JobBase(BaseModel):
    title: str
    description: str
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: SalaryPeriod = SalaryPeriod.yearly
    requirements: List[str] = []
    responsibilities: List[str] = []
    skills: List[str] = []
    experience: Optional[str] = None
    education: Optional[str] = None
    isRemote: bool = False
    isHybrid: bool = False
    certifications: List[str] = []
    languages: List[Dict[str, Union[str, None]]] = []
    softSkills: List[str] = []

class JobCreate(JobBase):
    internalJobBoard: bool = False
    externalJobBoards: bool = True
    socialMedia: bool = False
    applicationFormFields: Dict[str, Union[str, int, bool]] = {}

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employmentType: Optional[EmploymentType] = None
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: Optional[SalaryPeriod] = None
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    status: Optional[JobStatus] = None
    isRemote: Optional[bool] = None
    isHybrid: Optional[bool] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[Dict[str, Union[str, None]]]] = None
    softSkills: Optional[List[str]] = None
    internalJobBoard: Optional[bool] = None
    externalJobBoards: Optional[bool] = None
    socialMedia: Optional[bool] = None
    applicationFormFields: Optional[Dict[str, Union[str, int, bool]]] = None

class JobResponse(JobBase):
    id: str
    status: JobStatus
    createdAt: datetime
    updatedAt: datetime
    publishedAt: Optional[datetime] = None
    closedAt: Optional[datetime] = None

# Step-by-step job creation schemas
class JobBasicInfo(BaseModel):
    jobTitle: str
    department: str
    location: str
    employmentType: EmploymentType
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    salaryPeriod: SalaryPeriod = SalaryPeriod.yearly

class JobDetails(BaseModel):
    jobDescription: str
    keyResponsibilities: List[str] = []
    workMode: str  # remote | hybrid | onsite
    requiredExperience: Optional[str] = None
    teamSize: str
    reportingStructure: str

class JobRequirements(BaseModel):
    requiredSkills: List[str] = []
    educationLevel: Optional[str] = None
    certifications: List[str] = []
    languages: List[Dict[str, str]] = []  # e.g. [{"language": "English", "level": "fluent"}]
    softSkills: List[str] = []

class JobPublishOptions(BaseModel):
    internalJobBoard: bool = False
    externalJobBoards: bool = True
    socialMedia: bool = False
    applicationFormFields: Dict[str, Union[str, int, bool]] = {}

class JobStepperCreate(BaseModel):
    basicInfo: JobBasicInfo
    jobDetails: JobDetails
    requirements: JobRequirements
    publishOptions: JobPublishOptions

# Step Responses
class SalaryRangeSuggestion(BaseModel):
    min: int
    max: int
    note: Optional[str] = None

class JobStep1Response(BaseModel):
    message: str
    step: int
    sessionId: str
    aiSuggestions: Dict[str, Union[str, List[str], SalaryRangeSuggestion]] = {}

class JobStep2Response(BaseModel):
    message: str
    step: int
    sessionId: str
    similarJobs: List[Dict[str, Union[str, int]]] = []

class JobStep3Response(BaseModel):
    message: str
    step: int
    sessionId: str
    jobData: Dict[str, Optional[dict]]

class JobCreationCompleteResponse(BaseModel):
    message: str
    job: JobResponse
    publishedTo: List[str] = []

# Interview Scheduling Schemas
class InterviewerInfo(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    avatar: Optional[str] = None

class InterviewScheduleRequest(BaseModel):
    candidateId: str
    applicationId: str
    type: InterviewType
    scheduledDate: str  # YYYY-MM-DD
    scheduledTime: str  # HH:MM
    duration: int = 60  # minutes
    # timezone: str = "UTC"
    timezone: str = "Asia/Kolkata" 
    interviewers: List[InterviewerInfo] = []
    meetingLink: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    sendCalendarInvite: bool = True
    sendEmailNotification: bool = True

class InterviewRescheduleRequest(BaseModel):
    newDate: str  # YYYY-MM-DD
    newTime: str  # HH:MM
    reason: str
    notifyCandidate: bool = True

class InterviewFeedbackRequest(BaseModel):
    rating: int  # 1-5 scale
    technicalSkills: int  # 1-5 scale
    communicationSkills: int  # 1-5 scale
    culturalFit: int  # 1-5 scale
    overallRecommendation: str  # HIRE, NO_HIRE, MAYBE
    strengths: List[str] = []
    weaknesses: List[str] = []
    detailedFeedback: str
    nextSteps: Optional[str] = None

class InterviewResponse(BaseModel):
    # Core Interview Fields
    id: str
    candidateId: str
    candidateName: str
    candidateEmail: str
    applicationId: Optional[str]
    jobId: str
    jobTitle: str
    interviewType: InterviewType
    status: InterviewStatus
    scheduledAt: datetime
    duration: int
    timezone: str
    interviewers: List[InterviewerInfo] = []
    meetingLink: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[dict] = None
    calendarEventId: Optional[str] = None
    invitationSent: bool = False
    joinToken: Optional[str] = None
    tokenExpiry: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime

    # Candidate Additional Fields
    candidateEducation: Optional[str] = None
    candidateExperience: Optional[str] = None
    candidateSkills: List[str] = []
    candidateResume: Optional[str] = None
    candidatePortfolio: Optional[str] = None
    candidateLinkedIn: Optional[str] = None
    candidateGitHub: Optional[str] = None
    candidateLocation: Optional[str] = None

    # Application
    coverLetter: Optional[str] = None

    # Job Additional Fields
    jobDepartment: Optional[str] = None
    jobDescription: Optional[str] = None
    jobType: Optional[str] = None
    jobResponsibility: Optional[List[str]] = []
    jobSkills: Optional[List[str]] = []
    jobEducation: Optional[str] = None
    jobCertificates: Optional[List[str]] = []
    jobPublished: Optional[datetime] = None

class InterviewCalendarEvent(BaseModel):
    title: str
    description: str
    startTime: datetime
    endTime: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    meetingLink: Optional[str] = None

# New schemas for calendar integration and join tokens
class CalendarInviteResponse(BaseModel):
    success: bool
    eventId: Optional[str] = None
    message: str

class InterviewConfirmationRequest(BaseModel):
    interviewId: str
    confirmed: bool
    response: Optional[str] = None  # Optional response message from candidate

class InterviewJoinResponse(BaseModel):
    success: bool
    message: str
    interview: Optional[InterviewResponse] = None
    redirectUrl: Optional[str] = None

# Candidate schemas
class CandidateBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    resume: Optional[str] = None
    portfolio: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    skills: List[str] = []
    experience: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    salaryExpectation: Optional[int] = None
    
class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    id: str
    applicationStatus: Optional[ApplicationStatus] = None
    interviewStatus: Optional[InterviewStatus] = None
    createdAt: datetime
    updatedAt: datetime

class CandidateWithInterviews(CandidateResponse):
    upcomingInterviews: List[InterviewResponse] = []
    pastInterviews: List[InterviewResponse] = []
    applicationStatus: ApplicationStatus

# Application schemas
class ApplicationBase(BaseModel):
    jobId: str
    candidateId: str
    coverLetter: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    userId: str  # Add userId to ApplicationCreate
    appliedAt: datetime = datetime.utcnow()  # Automatically set the appliedAt timestamp

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    matchScore: Optional[int] = None

class ApplicationResponse(ApplicationBase):
    id: str
    status: ApplicationStatus
    matchScore: Optional[int] = None
    notes: Optional[str] = None
    appliedAt: datetime
    updatedAt: datetime

# Dashboard schemas
class DashboardMetrics(BaseModel):
    totalJobs: int
    activeCandidates: int
    hiringSuccessRate: float
    avgTimeToHire: int
    aiInterviewsCompleted: int

class RecruitmentTrend(BaseModel):
    month: str
    applications: int

class PipelineStage(BaseModel):
    stage: str
    count: int
    percentage: int

class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    time: str

# Settings schemas
class UserSettingsBase(BaseModel):
    language: str = "en-US"
    timezone: str = "UTC"
    dateFormat: str = "MM/DD/YYYY"
    autoSave: bool = True
    emailDailyDigest: bool = True
    emailNewCandidateAlerts: bool = True
    emailMarketingEmails: bool = False
    emailNewApplications: bool = True
    pushNewApplications: bool = True
    emailInterviewReminders: bool = True
    pushInterviewReminders: bool = True
    emailTaskDeadlines: bool = True
    pushTaskDeadlines: bool = False
    emailProductUpdates: bool = True
    pushProductUpdates: bool = False
    emailSecurityAlerts: bool = True
    pushSecurityAlerts: bool = True

class UserSettingsCreate(UserSettingsBase):
    userId: str

class UserSettingsUpdate(BaseModel):
    language: Optional[str] = None
    timezone: Optional[str] = None
    dateFormat: Optional[str] = None
    autoSave: Optional[bool] = None
    emailDailyDigest: Optional[bool] = None
    emailNewCandidateAlerts: Optional[bool] = None
    emailMarketingEmails: Optional[bool] = None
    emailNewApplications: Optional[bool] = None
    pushNewApplications: Optional[bool] = None
    emailInterviewReminders: Optional[bool] = None
    pushInterviewReminders: Optional[bool] = None
    emailTaskDeadlines: Optional[bool] = None
    pushTaskDeadlines: Optional[bool] = None
    emailProductUpdates: Optional[bool] = None
    pushProductUpdates: Optional[bool] = None
    emailSecurityAlerts: Optional[bool] = None
    pushSecurityAlerts: Optional[bool] = None

class UserSettingsResponse(UserSettingsBase):
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime

class GeneralSettingsUpdate(BaseModel):
    language: Optional[str] = None
    timezone: Optional[str] = None
    dateFormat: Optional[str] = None
    autoSave: Optional[bool] = None

class EmailSettingsUpdate(BaseModel):
    emailDailyDigest: Optional[bool] = None
    emailNewCandidateAlerts: Optional[bool] = None
    emailMarketingEmails: Optional[bool] = None

class NotificationSettingsUpdate(BaseModel):
    emailNewApplications: Optional[bool] = None
    pushNewApplications: Optional[bool] = None
    emailInterviewReminders: Optional[bool] = None
    pushInterviewReminders: Optional[bool] = None
    emailTaskDeadlines: Optional[bool] = None
    pushTaskDeadlines: Optional[bool] = None
    emailProductUpdates: Optional[bool] = None
    pushProductUpdates: Optional[bool] = None
    emailSecurityAlerts: Optional[bool] = None
    pushSecurityAlerts: Optional[bool] = None

# Company schemas
class SocialMediaLinks(BaseModel):
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None


class FeaturedImage(BaseModel):
    url: str
    caption: Optional[str] = None

class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[int] = None
    companySize: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    taxId: Optional[str] = None
    logo: Optional[str] = None
    coverImage: Optional[str] = None
    primaryColor: str = "#10b981"
    secondaryColor: str = "#3b82f6"
    careerHeadline: Optional[str] = None
    careerDescription: Optional[str] = None
    featuredImages: Optional[List[FeaturedImage]] = None
    socialMedia: Optional[SocialMediaLinks] = None
    remoteWorkPolicy: Optional[str] = None
    remoteHiringRegions: List[str] = []

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    founded: Optional[int] = None
    companySize: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    taxId: Optional[str] = None
    logo: Optional[str] = None
    coverImage: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    careerHeadline: Optional[str] = None
    careerDescription: Optional[str] = None
    featuredImages: Optional[List[FeaturedImage]] = None
    socialMedia: Optional[SocialMediaLinks] = None
    remoteWorkPolicy: Optional[str] = None
    remoteHiringRegions: Optional[List[str]] = None

class CompanyResponse(CompanyBase):
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime

# Company Location schemas
class CompanyLocationBase(BaseModel):
    name: str
    type: str = "office"
    address: str
    city: str
    state: Optional[str] = None
    country: str
    zipCode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isHeadquarters: bool = False

class CompanyLocationCreate(CompanyLocationBase):
    pass

class CompanyLocationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipCode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isHeadquarters: Optional[bool] = None

class CompanyLocationResponse(CompanyLocationBase):
    id: str
    companyId: str
    createdAt: datetime
    updatedAt: datetime

# Team Member schemas
class TeamMemberBase(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: str = "active"
    accessLevel: str = "member"

class TeamMemberCreate(TeamMemberBase):
    pass

class TeamMemberInvite(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    accessLevel: str = "member"

class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None
    accessLevel: Optional[str] = None

class TeamMemberResponse(TeamMemberBase):
    id: str
    companyId: str
    invitedAt: Optional[datetime] = None
    joinedAt: Optional[datetime] = None
    invitedBy: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Subscription schemas
class SubscriptionBase(BaseModel):
    planName: str
    planPrice: Decimal
    billingCycle: str = "monthly"
    status: str = "active"
    currentPeriodStart: datetime
    currentPeriodEnd: datetime
    cancelAtPeriodEnd: bool = False
    teamMemberLimit: int = 25
    aiCreditsLimit: int = 1000
    storageLimit: int = 10

class SubscriptionCreate(SubscriptionBase):
    stripeSubscriptionId: Optional[str] = None
    stripeCustomerId: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    planName: Optional[str] = None
    planPrice: Optional[Decimal] = None
    billingCycle: Optional[str] = None
    status: Optional[str] = None
    currentPeriodEnd: Optional[datetime] = None
    cancelAtPeriodEnd: Optional[bool] = None
    teamMemberLimit: Optional[int] = None
    aiCreditsLimit: Optional[int] = None
    storageLimit: Optional[int] = None

class SubscriptionResponse(SubscriptionBase):
    id: str
    companyId: str
    stripeSubscriptionId: Optional[str] = None
    stripeCustomerId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Payment Method schemas
class PaymentMethodBase(BaseModel):
    type: str = "card"
    last4: str
    brand: str
    expiryMonth: int
    expiryYear: int
    isDefault: bool = False

class PaymentMethodCreate(PaymentMethodBase):
    stripePaymentMethodId: Optional[str] = None

class PaymentMethodUpdate(BaseModel):
    isDefault: Optional[bool] = None

class PaymentMethodResponse(PaymentMethodBase):
    id: str
    companyId: str
    stripePaymentMethodId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Billing Address schemas
class BillingAddressBase(BaseModel):
    contactName: str
    contactEmail: EmailStr
    contactPhone: Optional[str] = None
    companyName: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    zipCode: str
    country: str

class BillingAddressCreate(BillingAddressBase):
    pass

class BillingAddressUpdate(BaseModel):
    contactName: Optional[str] = None
    contactEmail: Optional[EmailStr] = None
    contactPhone: Optional[str] = None
    companyName: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None

class BillingAddressResponse(BillingAddressBase):
    id: str
    companyId: str
    createdAt: datetime
    updatedAt: datetime

# Invoice schemas
class InvoiceBase(BaseModel):
    invoiceNumber: str
    amount: Decimal
    currency: str = "USD"
    status: str = "pending"
    dueDate: datetime
    paidAt: Optional[datetime] = None

class InvoiceCreate(InvoiceBase):
    stripeInvoiceId: Optional[str] = None
    downloadUrl: Optional[str] = None

class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    paidAt: Optional[datetime] = None
    downloadUrl: Optional[str] = None

class InvoiceResponse(InvoiceBase):
    id: str
    companyId: str
    stripeInvoiceId: Optional[str] = None
    downloadUrl: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

# Subscription Addon schemas
class SubscriptionAddonBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    billingCycle: str = "monthly"
    isActive: bool = True

class SubscriptionAddonCreate(SubscriptionAddonBase):
    pass

class SubscriptionAddonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    billingCycle: Optional[str] = None
    isActive: Optional[bool] = None

class SubscriptionAddonResponse(SubscriptionAddonBase):
    id: str
    subscriptionId: str
    createdAt: datetime
    updatedAt: datetime

# Usage and Plan Information
class PlanUsage(BaseModel):
    teamMembers: Dict[str, Union[int, str]]  # {"current": 18, "limit": 25}
    aiCredits: Dict[str, Union[int, str]]    # {"current": 873, "limit": 1000}
    storage: Dict[str, Union[int, str]]      # {"current": 4.2, "limit": 10, "unit": "GB"}

class PlanFeature(BaseModel):
    name: str
    included: bool
    description: Optional[str] = None

class PlanDetails(BaseModel):
    name: str
    price: Decimal
    billingCycle: str
    features: List[PlanFeature]
    limits: Dict[str, int]

# AI Tools schemas
class ErrorResponse(BaseModel):
    detail: str

class Question(BaseModel):
    question_text: str
    expected_answer_format: str

class InterviewQuestionRequest(BaseModel):
    job_position: str
    interview_type: str  # e.g., "Technical Skills", "Behavioral", etc.
    key_skills: List[str]
    experience_level: str  # e.g., "Senior Level (5+ years)"
    additional_context: Optional[str] = None
    number_of_questions: int = Field(default=1, gt=0, lt=6, description="Number of questions to generate, must be between 1 and 5.")
    job_description: Optional[str] = None  # Added for job description based questions

class InterviewQuestionsResponse(BaseModel):
    questions: List[Question]
    number_of_questions: Optional[int] = None
    input_tokens: int
    output_tokens: int

class InterviewQuestionsFromResumeRequest(BaseModel):
    resume: str
    number_of_questions: int = Field(default=1, gt=0, lt=6, description="Number of questions to generate, must be between 1 and 5.")

class InterviewQuestionsFromResumeResponse(BaseModel):
    questions: List[Question]
    input_tokens: int
    output_tokens: int

# New schema for generating questions based on job_id and candidate_id
class InterviewQuestionsFromJobCandidateRequest(BaseModel):
    job_id: str
    candidate_id: str
    interview_type: str = "TECHNICAL"  # Default to technical interview
    number_of_questions: int = Field(default=4, gt=0, le=10, description="Number of questions to generate, must be between 1 and 10.")

class InterviewQuestionsFromJobCandidateResponse(BaseModel):
    questions: List[Question]
    job_title: str
    candidate_name: str
    interview_type: str
    input_tokens: int
    output_tokens: int

# ✅ NEW: Updated Question Schemas for separated models
class QuestionBase(BaseModel):
    questionText: str
    expectedAnswerFormat: Optional[str] = None

class QuestionCreate(QuestionBase):
    interviewId: str

class QuestionResponse(QuestionBase):
    id: str
    interviewId: str
    createdAt: datetime
    updatedAt: datetime

# ✅ NEW: Answer Schemas
class AnswerBase(BaseModel):
    answerText: str

class AnswerCreate(AnswerBase):
    questionId: str
    interviewId: str

class AnswerUpdate(BaseModel):
    answerText: Optional[str] = None

class AnswerResponse(AnswerBase):
    id: str
    questionId: str
    interviewId: str
    answeredAt: datetime
    createdAt: datetime
    updatedAt: datetime

# ✅ NEW: Evaluation Schemas
# ✅ UPDATED: Evaluation Schemas with questionText and answerText
class EvaluationBase(BaseModel):
    questionText: str  # ✅ NEW: Added questionText
    answerText: str    # ✅ NEW: Added answerText
    interviewId: str   # ✅ NEW: Added interviewId
    factualAccuracy: Optional[str] = None
    factualAccuracyExplanation: Optional[str] = None
    completeness: Optional[str] = None
    completenessExplanation: Optional[str] = None
    relevance: Optional[str] = None
    relevanceExplanation: Optional[str] = None
    coherence: Optional[str] = None
    coherenceExplanation: Optional[str] = None
    score: Optional[float] = None
    inputTokens: Optional[int] = None
    outputTokens: Optional[int] = None
    finalEvaluation: Optional[str] = None

class EvaluationCreate(EvaluationBase):
    answerId: str

class EvaluationUpdate(EvaluationBase):
    pass

class EvaluationResponse(EvaluationBase):
    id: str
    answerId: str
    evaluatedAt: datetime
    createdAt: datetime
    updatedAt: datetime

# ✅ NEW: Combined response for evaluation with question and answer details
# ✅ UPDATED: Combined response for evaluation with question and answer details
class EvaluationWithDetailsResponse(BaseModel):
    id: str
    questionText: str
    answerText: str
    interviewId: str  # ✅ NEW: Added interviewId
    expectedAnswerFormat: Optional[str] = None
    factualAccuracy: Optional[str] = None
    factualAccuracyExplanation: Optional[str] = None
    completeness: Optional[str] = None
    completenessExplanation: Optional[str] = None
    relevance: Optional[str] = None
    relevanceExplanation: Optional[str] = None
    coherence: Optional[str] = None
    coherenceExplanation: Optional[str] = None
    score: Optional[float] = None
    inputTokens: Optional[int] = None
    outputTokens: Optional[int] = None
    finalEvaluation: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    answeredAt: Optional[datetime] = None
    evaluatedAt: Optional[datetime] = None

# ✅ NEW: Interview Result Schemas
class InterviewResultBase(BaseModel):
    candidateId: str
    applicationId:str
    jobId: str
    evaluatedCount: int
    totalQuestions: int
    averageFactualAccuracy: float
    averageCompleteness: float
    averageRelevance: float
    averageCoherence: float
    averageScore: float
    passStatus: str  # "pass", "fail", "borderline"
    summaryResult: str
    knowledgeLevel: str
    recommendations: Optional[str] = None

class InterviewResultCreate(InterviewResultBase):
    interviewId: str

class InterviewResultResponse(InterviewResultBase):
    id: str
    interviewId: str
    createdAt: datetime
    updatedAt: datetime

class InterviewResultWithDetailsResponse(InterviewResultResponse):
    
    evaluations: List[EvaluationWithDetailsResponse] = []


# Legacy schemas for backward compatibility
class QuestionEvaluationData(BaseModel):
    factualAccuracy: str
    factualAccuracyExplanation: str
    completeness: str
    completenessExplanation: str
    relevance: str
    relevanceExplanation: str
    coherence: str
    coherenceExplanation: str
    score: float
    inputTokens: int
    outputTokens: int
    finalEvaluation: str

class QuestionEvaluationUpdate(QuestionEvaluationData):
    pass

class QuestionWithEvaluationResponse(QuestionResponse):
    evaluation: Optional[QuestionEvaluationData] = None

# AI Tools Schemas
class QuestionEvaluationRequest(BaseModel):
    questionText: str
    answerText: str
    knowledgeLevel: str

# Pydantic models for request and response validation

class CandidateEvaluationRequest(BaseModel):
    job_description: str
    candidate_resume: str

class CandidateEvaluationResponse(BaseModel):
    candidate_name: str
    email_id: str
    decision: str
    input_tokens: int
    output_tokens: int

class CreateJobDescriptionRequest(BaseModel):
    content_type: str  # e.g., "Job Description", "Email Template", etc.
    job_position: str
    key_requirements: str
    company_values: str
    additional_details: Optional[str] = None
    tone: str = "Professional"

class CreateJobDescriptionResponse(BaseModel):
    generated_content: str
    input_tokens: int
    output_tokens: int
