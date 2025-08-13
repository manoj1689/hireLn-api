import uuid
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
import openai
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional, Union
from service.candidate_service import create_candidate_from_parsed_data
from utils.openai_client import create_openai_chat
from dotenv import load_dotenv
import json
import logging
import re
import html
from requests import Session

# New imports for resume parsing
from ollama import Client
import base64
import fitz # PyMuPDF
import os
import tempfile
import requests
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from fastapi import Depends
from database import get_db  # async session getter (assumed)
from prisma import Prisma 
import pdfplumber
from io import BytesIO
from models.schemas import (
    CandidateResponse,
    CandidateCreate,
    CreateJobDescriptionRequest,
    CreateJobDescriptionResponse,
    ErrorResponse,
    InterviewQuestionRequest,
    QuestionEvaluationData,
    Question,
    QuestionEvaluationRequest,
    InterviewQuestionRequest,
    InterviewQuestionsResponse,
    InterviewQuestionsFromResumeRequest,
    InterviewQuestionsFromResumeResponse,
    InterviewQuestionsFromJobCandidateRequest,
    InterviewQuestionsFromJobCandidateResponse,
    CandidateEvaluationRequest,
    CandidateEvaluationResponse,
    UserResponse,
    # New imports for resume parsing
    ParseResumesFromDriveResponse,
    ResumeParseResult
)
from auth.dependencies import get_current_user, get_user_or_interview_auth

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file
load_dotenv()

# Constants for resume parsing
# SERVER = "http://103.99.186.164:11434"
# MODEL = "qwen2.5vl:7b"
SERVICE_ACCOUNT_FILE = "hirelnresumes-185cd081b37f.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

# Initialize Google Drive service (global for efficiency)
try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build("drive", "v3", credentials=credentials)
except Exception as e:
    logger.error(f"Failed to initialize Google Drive service: {e}")
    drive_service = None # Set to None if initialization fails, so endpoints can check

def clean_extracted_text(text: str) -> str:
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def extract_text_with_pymupdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


# Utility: extract structured data from a PDF using Open AI
def extract_resume_data(text: str) -> CandidateCreate:
    prompt = (
        "You are a strict JSON generator for extracting structured candidate data from resumes.\n"
        "Extract ONLY the following fields from the given resume text.\n"
        "Your output MUST be a valid, strictly formatted JSON object with ALL specified fields.\n\n"
        "⚠️ RULES:\n"
        "- Always include **ALL** fields listed below.\n"
        "- If data is missing:\n"
        "  - Use an empty string (`\"\"`) for string fields\n"
        "  - Use an empty array (`[]`) for list fields\n"
        "  - Use an empty object (`{}`) for object fields\n"
        "- Do NOT include extra fields or explanations.\n"
        "- Ensure all nested structures follow the expected format strictly.\n\n"
        "### Required JSON Fields:\n"
        "{\n"
        '  "name": string,\n'
        '  "email": string,\n'
        '  "phone": string,\n'
        '  "address": array of strings,\n'
        '  "location": string,\n'
        '  "personalInfo": {\n'
        '    "dob": string,\n'
        '    "gender": string,\n'
        '    "maritalStatus": string,\n'
        '    "nationality": string\n'
        '  },\n'
        '  "summary": string,\n'
        '  "education": [\n'
        '    {\n'
        '      "degree": string,\n'
        '      "institution": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "grade": string\n'
        '    }\n'
        '  ],\n'
        '  "experience": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "company": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "description": string\n'
        '    }\n'
        '  ],\n'
        '  "previousJobs": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "company": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "description": array of strings\n'
        '    }\n'
        '  ],\n'
        '  "internships": array of strings,\n'
        '  "technicalSkills": array of strings,\n'
        '  "softSkills": array of strings,\n'
        '  "languages": array of strings,\n'
        '  "certifications": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "issuer": string,\n'
        '      "date": string\n'
        '    }\n'
        '  ],\n'
        '  "projects": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "description": string,\n'
        '      "url": string\n'
        '    }\n'
        '  ],\n'
        '  "hobbies": array of strings,\n'
        '  "salaryExpectation": integer,\n'
        '  "department": string\n'
        '  "resume": string (optional)\n'
        '  "portfolio": string (optional)\n'
        '  "linkedin": string (optional)\n'
        '  "github": string (optional)\n'
        '}\n\n'
        "### Resume text:\n"
        f"{text}\n\n"
        "### Response:\n"
        "Return a valid JSON object only. No markdown. No explanations. No extra keys."
    )
    messages = [
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000
        )
        content = response.choices[0].message.content.strip()

        # Strip ```json ... ``` wrappers if present
        content = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

        parsed_data = json.loads(content)
        return CandidateCreate(**parsed_data)  # Validate via Pydantic
    except Exception as e:
        logger.error("OpenAI API call failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OpenAI API failed: {str(e)}")
    

async def process_resume_file(temp_path: Path, file_name: str, current_user: UserResponse, db: Prisma):
    try:
        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()

        raw_text = extract_text_with_pymupdf(pdf_bytes)
        cleaned_text = clean_extracted_text(raw_text)

        parsed_data = extract_resume_data(cleaned_text)  # not str(temp_path)
        
        
        success, message = await create_candidate_from_parsed_data(parsed_data, current_user, db)
        print("file",file_name, "success", success, "message", message)
        return {"file": file_name, "success": success, "message": message}

    except Exception as e:
        logger.warning(f"Failed to process {file_name}: {e}")
        return {"file": file_name, "success": False, "message": str(e)}


@router.post("/generate_interview_questions", response_model=InterviewQuestionsResponse)
async def generate_interview_questions(
    request: InterviewQuestionRequest,
    # current_user: UserResponse = Depends(get_current_user)
):
    # Sanitize inputs
    job_position = html.escape(request.job_position)
    interview_type = html.escape(request.interview_type)
    experience_level = html.escape(request.experience_level)
    key_skills = ", ".join(map(html.escape, request.key_skills))
    additional_context = html.escape(request.additional_context or "None")

    # Construct prompt
    prompt = (
        f"You are an expert HR assistant. Generate tailored interview questions for the following job role.\n\n"
        f"Job Position: {job_position}\n"
        f"Interview Type: {interview_type}\n"
        f"Key Skills: {key_skills}\n"
        f"Experience Level: {experience_level}\n"
        f"Additional Context: {additional_context}\n\n"
        f"Provide {request.number_of_questions} high-quality interview questions relevant to the role and experience. "
        f"Return them as a JSON array like this:\n"
        f"[{{\"question_text\": \"string\", \"expected_answer_format\": \"string\"}}]"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Provide the questions in JSON format only."}
    ]

    try:
        completion = create_openai_chat(messages)
        content = completion.choices[0].message.content.strip()
        # logging.info(f"Raw OpenAI Response Content:\n{content}")

        # Remove markdown \`\`\`json fences if present
        content = re.sub(r"^\`\`\`json\s*|\`\`\`$", "", content, flags=re.MULTILINE).strip()

        # Extract JSON array from the response
        json_match = re.search(r"(\[[\s\S]*\])", content)
        if not json_match:
            raise HTTPException(status_code=500, detail="Could not extract JSON array from OpenAI response.")

        json_str = json_match.group(1)
        logging.info(f"Extracted JSON string:\n{json_str}")

        # Parse JSON string to Python objects
        json_content = json.loads(json_str)

        # Validate each question with Pydantic
        questions = [Question(**q) for q in json_content]

        return InterviewQuestionsResponse(
            questions=questions[:request.number_of_questions],
            number_of_questions=request.number_of_questions,
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )

    except (json.JSONDecodeError, ValidationError) as e:
        logging.error("Failed to decode or validate OpenAI response", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        logging.error("Error during interview question generation", exc_info=True)
        raise HTTPException(status_code=500, detail="Error during API processing: " + str(e))  
    
@router.post("/generate_interview_questions_from_jd", response_model=InterviewQuestionsResponse)
async def generate_interview_questions_from_jd(
    request: InterviewQuestionRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    sanitized_job_description = html.escape(request.job_description)

    prompt = (
        "You are a knowledgeable assistant tasked with generating interview questions. "
        f"Generate {request.number_of_questions} questions based on the following job description: '{sanitized_job_description}'.\n"
        "Return the questions in a JSON array where each question follows this format:\n"
        "{\n"
        "  \"question_text\": \"string\",\n"
        "  \"expected_answer_format\": \"string\"\n"
        "}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Provide the questions in JSON format."}
    ]

    completion = create_openai_chat(messages)
    try:
        content = completion.choices[0].message.content.strip()
        
        # Log the response for debugging
        logging.info(f"OpenAI Response Content: {content}")
        
        # Remove triple backticks if present
        content = content.strip("\`\`\`json").strip("\`\`\`").strip()
        
        json_content = json.loads(content)
        
        questions = [Question(**q) for q in json_content]
        return InterviewQuestionsResponse(
            questions=questions,
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )
    except (json.JSONDecodeError, ValidationError) as e:
        logging.error("Failed to decode JSON or validate data", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        logging.error("An error occurred during API call", exc_info=True)
        raise HTTPException(status_code=500, detail="Error during API processing: " + str(e))

@router.post("/generate_interview_questions_from_resume", response_model=InterviewQuestionsFromResumeResponse)
async def generate_interview_questions_from_resume(
    request: InterviewQuestionsFromResumeRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    sanitized_resume = html.escape(request.resume)

    prompt = (
        "You are a knowledgeable assistant tasked with generating interview questions from a resume. "
        f"Create {request.number_of_questions} subjective questions to assess a candidate based on the provided resume: '{sanitized_resume}'.\n"
        "Return the questions in a JSON array where each question follows this format:\n"
        "{\n"
        "  \"question_text\": \"string\",\n"
        "  \"expected_answer_format\": \"string\"\n"
        "}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Provide the questions in JSON format."}
    ]

    completion = create_openai_chat(messages)
    try:
        content = completion.choices[0].message.content.strip()
        
        # Log the raw response content for debugging
        logging.info(f"OpenAI Response Content: {content}")
        
        # Remove triple backticks if present
        content = content.strip("\`\`\`json").strip("\`\`\`").strip()
        
        # Parse JSON content directly
        json_content = json.loads(content)
        
        questions = [Question(**q) for q in json_content]
        return InterviewQuestionsFromResumeResponse(
            questions=questions,
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )
    except (json.JSONDecodeError, ValidationError) as e:
        logging.error("Failed to decode JSON or validate data", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        logging.error("An error occurred during API call", exc_info=True)
 
        raise HTTPException(status_code=500, detail="Error during API processing: " + str(e))




@router.post("/generate_interview_questions_from_jobCandidate", response_model=InterviewQuestionsFromJobCandidateResponse)
async def generate_interview_questions_from_job_candidate(
    request: InterviewQuestionsFromJobCandidateRequest,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """
    Generate interview questions based on a specific job and candidate combination.
    
    Authentication options:
    1. Authorization: Bearer <jwt_token>
    2. X-Interview-Token: <interview_token>
    """
    db = get_db()

    try:
        # Fetch job details
        job = await db.job.find_unique(
            where={"id": request.job_id}
        )

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Fetch candidate details
        candidate = await db.candidate.find_unique(
            where={"id": request.candidate_id}
        )

        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Authorization check
        if isinstance(auth_data, UserResponse):
            # User token auth - check if user owns the job
            if job.userId != auth_data.id:
                raise HTTPException(status_code=403, detail="Access denied to this job")
        else:
            # Interview token auth - check if the interview matches
            interview_data = auth_data
            if (interview_data["job"].id != request.job_id or 
                interview_data["candidate"].id != request.candidate_id):
                raise HTTPException(status_code=403, detail="Interview token doesn't match job/candidate")

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


        # Prepare job information
        job_info = {
            "title": job.title,
            "description": job.description,
            "skills": job.skills or [],
            "requirements": job.requirements or [],
            "responsibilities": job.responsibilities or [],
            "experience": job.experience or "Not specified",
            "education": job.education or "Not specified"
        }

        # Prepare candidate information
        candidate_info = {
            "name": candidate.name,
            "skills": candidate.technicalSkills or [],
            "experience": json.dumps(candidate_experience) if candidate_experience else "Not specified",
            "education": json.dumps(candidate_education) if candidate_education else "Not specified",
            "resume": candidate.resume or "No resume provided"
                }

        # Create a comprehensive prompt
        prompt = (
            f"Session ID: {uuid.uuid4()}\n"
            f"You are an expert HR assistant tasked with generating tailored interview questions. "
            f"Create {request.number_of_questions} {request.interview_type.lower()} interview questions "
            f"that assess how well this specific candidate fits the job requirements.\n\n"
            f"JOB DETAILS:\n"
            f"Title: {job_info['title']}\n"
            f"Description: {job_info['description']}\n"
            f"Required Skills: {', '.join(job_info['skills'])}\n"
            f"Requirements: {'; '.join(job_info['requirements'])}\n"
            f"Key Responsibilities: {'; '.join(job_info['responsibilities'])}\n"
            f"Experience Level: {job_info['experience']}\n"
            f"Education: {job_info['education']}\n\n"
            f"CANDIDATE PROFILE:\n"
            f"Name: {candidate_info['name']}\n"
            f"Skills: {', '.join(candidate_info['skills'])}\n"
            f"Experience: {candidate_info['experience']}\n"
            f"Education: {candidate_info['education']}\n"
            f"Resume Summary: {candidate_info['resume'][:500]}...\n\n"
            f"Generate questions that:\n"
            f"1. Assess the candidate's proficiency in job-required skills\n"
            f"2. Evaluate their experience relevance to the role\n"
            f"3. Test their understanding of key responsibilities\n"
            f"4. Identify potential gaps or strengths\n"
            f"5. Are specific to this job-candidate combination\n\n"
            f"6. You have to generate each time different questions set\n\n"
            f"Return the questions in a JSON array format:\n"
            f"[{{\"question_text\": \"string\", \"expected_answer_format\": \"string\"}}]"
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Generate the tailored interview questions in JSON format."}
        ]

        completion = create_openai_chat(messages)
        content = completion.choices[0].message.content.strip()

        # Log the response for debugging
        logger.info(f"OpenAI Response Content: {content}")

        # Remove triple backticks if present
        content = content.strip("```json").strip("```").strip()

        # Extract JSON array from the response
        json_match = re.search(r"(\[[\s\S]*\])", content)
        if not json_match:
            raise HTTPException(status_code=500, detail="Could not extract JSON array from OpenAI response.")

        json_str = json_match.group(1)
        json_content = json.loads(json_str)

        # Validate each question with Pydantic
        questions = [Question(**q) for q in json_content]

        return InterviewQuestionsFromJobCandidateResponse(
            questions=questions[:request.number_of_questions],
            job_title=job.title,
            candidate_name=candidate.name,
            interview_type=request.interview_type,
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("Failed to decode JSON or validate data", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        logger.error("An error occurred during API call", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during API processing: {str(e)}")
    
    
@router.post("/evaluate_student_answer", response_model=QuestionEvaluationData)
async def evaluate_student_answer(request: QuestionEvaluationRequest):
    """
    Evaluate a student's answer using AI
    """
    try:
        # Create the evaluation prompt
        prompt = f"""
        You are an expert interviewer evaluating a candidate's answer. Please evaluate the following:

        Question: {request.questionText}
        Answer: {request.answerText}
        Knowledge Level: {request.knowledgeLevel}

        Please provide a comprehensive evaluation with the following criteria:

        1. Factual Accuracy: Rate as "Poor", "Fair", "Good", or "Excellent"
        2. Completeness: Rate as "Poor", "Fair", "Good", or "Excellent"  
        3. Relevance: Rate as "Poor", "Fair", "Good", or "Excellent"
        4. Coherence: Rate as "Poor", "Fair", "Good", or "Excellent"
        5. Overall Score: Provide a numerical score from 1.0 to 5.0
        6. Final Evaluation: Provide a summary evaluation

        Please respond in the following JSON format:
        {{
            "factualAccuracy": "rating",
            "factualAccuracyExplanation": "detailed explanation",
            "completeness": "rating",
            "completenessExplanation": "detailed explanation",
            "relevance": "rating", 
            "relevanceExplanation": "detailed explanation",
            "coherence": "rating",
            "coherenceExplanation": "detailed explanation",
            "score": numerical_score,
            "finalEvaluation": "overall summary"
        }}
        """

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert interviewer and evaluator. Provide detailed, constructive feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Parse the response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Find JSON in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_str = content[start_idx:end_idx]
            evaluation_data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            # Fallback parsing if JSON extraction fails
            raise HTTPException(
                status_code=500,
                detail="Failed to parse AI evaluation response"
            )

        # Get token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Create response
        return QuestionEvaluationData(
            factualAccuracy=evaluation_data.get("factualAccuracy", "Fair"),
            factualAccuracyExplanation=evaluation_data.get("factualAccuracyExplanation", "No explanation provided"),
            completeness=evaluation_data.get("completeness", "Fair"),
            completenessExplanation=evaluation_data.get("completenessExplanation", "No explanation provided"),
            relevance=evaluation_data.get("relevance", "Fair"),
            relevanceExplanation=evaluation_data.get("relevanceExplanation", "No explanation provided"),
            coherence=evaluation_data.get("coherence", "Fair"),
            coherenceExplanation=evaluation_data.get("coherenceExplanation", "No explanation provided"),
            score=float(evaluation_data.get("score", 3.0)),
            inputTokens=input_tokens,
            outputTokens=output_tokens,
            finalEvaluation=evaluation_data.get("finalEvaluation", "No final evaluation provided")
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )

@router.post("/evaluate_candidate_resume", response_model=CandidateEvaluationResponse)
async def evaluate_candidate_resume(
    request: CandidateEvaluationRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    sanitized_job_description = html.escape(request.job_description)
    sanitized_resume = html.escape(request.candidate_resume)

    prompt = (
        "You are a knowledgeable assistant tasked with evaluating a candidate's resume against a job description. "
        "Analyze the alignment between the job requirements and the candidate's qualifications using the following criteria:\n"
        "- Skill Match: Assess if the candidate possesses the necessary skills listed in the job description.\n"
        "- Experience Level: Assess if the candidate's experience meets the job's experience requirements.\n"
        "- Relevance: Assess how relevant the candidate's past experience and skills are to the job role.\n"
        "- Potential for Growth: Assess the candidate's potential for growth and suitability for long-term success in the role.\n\n"
        "Provide the evaluation in the following JSON format:\n"
        "{\n"
        "  \"candidate_name\": \"string\",\n"
        "  \"email_id\": \"string\",\n"
        "  \"decision\": \"string\",\n"
        "  \"input_tokens\": integer,\n"
        "  \"output_tokens\": integer\n"
        "}\n\n"
        f"Job Description: {sanitized_job_description}\n"
        f"Candidate Resume: {sanitized_resume}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Evaluate the resume against the job description and provide feedback in the specified JSON format."}
    ]

    completion = create_openai_chat(messages)
    try:
        content = completion.choices[0].message.content.strip()
        # Remove triple backticks if present
        content = content.strip("\`\`\`json").strip("\`\`\`").strip()
        json_match = re.search(r'{.*}', content, re.DOTALL)
        if not json_match:
            raise HTTPException(status_code=500, detail="Failed to find JSON data in OpenAI response")

        results = json.loads(json_match.group(0))
        return CandidateEvaluationResponse(
            candidate_name=results["candidate_name"],
            email_id=results["email_id"],
            decision=results["decision"],
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )
    except (json.JSONDecodeError, ValidationError, KeyError) as e:
        logging.error("Error processing JSON from response", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing JSON from response: {str(e)}")
    except Exception as e:
        logging.error("An error occurred during API call", exc_info=True)
        raise HTTPException(status_code=500, detail="Error during API processing: " + str(e))


@router.post("/create_job_description_from_form", response_model=CreateJobDescriptionResponse)
async def create_job_description_from_form(
    request: CreateJobDescriptionRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    sanitized_content_type = html.escape(request.content_type)
    sanitized_job_position = html.escape(request.job_position)
    sanitized_key_requirements = html.escape(request.key_requirements)
    sanitized_company_values = html.escape(request.company_values)
    sanitized_additional_details = html.escape(request.additional_details or "")
    sanitized_tone = html.escape(request.tone)

    # Compose prompt dynamically based on content type
    prompt = (
        f"You are an expert assistant tasked with crafting a {sanitized_content_type.lower()} based on these details:\n"
        f"Job Position: {sanitized_job_position}\n"
        f"Key Requirements: {sanitized_key_requirements}\n"
        f"Company Values: {sanitized_company_values}\n"
        f"Additional Details: {sanitized_additional_details}\n"
        f"Tone: {sanitized_tone}\n"
        "Provide the generated content in the following JSON format:\n"
        "{\n"
        "  \"generated_content\": \"string\"\n"
        "}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Generate the requested content."}
    ]

    try:
        completion = create_openai_chat(messages)
        content = completion.choices[0].message.content.strip()
        # logging.info(f"OpenAI Response Content: {content}")

        # Remove triple backticks if present
        content = content.strip("\`\`\`json").strip("\`\`\`").strip()
        json_content = json.loads(content)

        if "generated_content" not in json_content:
            raise HTTPException(status_code=500, detail="Missing 'generated_content' in OpenAI response")

        return CreateJobDescriptionResponse(
            generated_content=json_content["generated_content"],
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens
        )
    except (json.JSONDecodeError, KeyError) as e:
        logging.error("Failed to decode JSON or validate response", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        logging.error("Error during content generation", exc_info=True)
        raise HTTPException(status_code=500, detail=f"API processing error: {str(e)}")


@router.get("/match/{job_id}", response_model=List[CandidateResponse])
async def get_matched_candidates(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get candidates matched to a specific job"""
    db = get_db()

    job = await db.job.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_skills = job.skills or []
    job_location = job.location or ""
    job_experience = job.experience or ""
    job_education = job.education or ""
    job_salary_min = job.salaryMin or 0
    job_salary_max = job.salaryMax 
    job_employment_type = job.employmentType if hasattr(job, "employmentType") else None

    # Extract city or main location keyword (loosely)
    location_keyword = job_location.split(",")[0].strip() if job_location else ""

    # Prepare filters with partial matching and fallbacks
    filters = [
        {
            "technicalSkills": {
                "hasSome": job_skills  # candidate must have at least one skill in job_skills
            }
        }
    ]

    # if location_keyword:
    #     filters.append({
    #         "location": {
    #             "contains": location_keyword,
    #             "mode": "insensitive"
    #         }
    #     })
    # print("job exp",job_experience)
   # Match candidate experience based on range
    # if job_experience:
    #     job_exp_min, job_exp_max = parse_experience_range(job_experience)

    #     filters.append({
    #         "OR": [
    #             {"experience": None},  
    #             {
    #                 "AND": [
    #                     {
    #                         "experience": {
    #                             "in": [
    #                                 exp_range
    #                                 for exp_range in [
    #                                     "0-1", "1-3", "3-5", "5-10", "10+"
    #                                 ]
    #                                 if ranges_overlap(
    #                                     job_exp_min, job_exp_max,
    #                                     *parse_experience_range(exp_range)
    #                                 )
    #                             ]
    #                         }
    #                     }
    #                 ]
    #             }
    #         ]
    #     })

    # if job_education:
    #     # partial match on "Bachelor", "Master", etc.
    #     edu_keyword = "Bachelor" if "bachelor" in job_education.lower() else job_education
    #     filters.append({
    #         "education": {
    #             "contains": edu_keyword,
    #             "mode": "insensitive"
    #         }
    #     })

    # Salary expectation filter with fallback to None
    # salary_filter = {
    #     "OR": [
    #         {"salaryExpectation": None},
    #         {
    #             "AND": [
    #                 {"salaryExpectation": {"gte": job_salary_min}},
    #                 {"salaryExpectation": {"lte": job_salary_max}},
    #             ]
    #         }
    #     ]
    # }

    # filters.append(salary_filter)

    candidates = await db.candidate.find_many(
        where={"AND": filters},
        skip=skip,
        take=limit
    )

    return [CandidateResponse(**candidate.dict()) for candidate in candidates]


def clean_extracted_text(text: str) -> str:
    """
    Cleans the extracted text to remove duplicates and unnecessary information.
    """
    # Remove repeated lines, page numbers, and other unnecessary patterns
    clean_text = re.sub(r"111093/2022/COORDINATION SECTION.*\n", "", text)
    clean_text = re.sub(r"\bClass-X\b", "", clean_text)
    clean_text = re.sub(r"\bEnglish-L&L $$184$$\b", "", clean_text)
    clean_text = re.sub(r"\b\d{2,}\b", "", clean_text)
    
    # Remove extra newlines
    clean_text = re.sub(r'\n{2,}', '\n\n', clean_text).strip()
    
    return clean_text

def parse_experience_range(exp: str):
    if exp == "10+":
        return 10, float("inf")
    if "-" in exp:
        parts = exp.split("-")
        return int(parts[0]), int(parts[1])
    return 0, 0

def ranges_overlap(min1, max1, min2, max2):
    return max(min1, min2) <= min(max1, max2)


@router.post("/parse_resumes_from_drive")
async def parse_resumes_from_drive(
    folder_id: str = Query(..., description="Google Drive folder ID containing the resumes."),
    limit: int = Query(4, gt=0, le=100),
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    if not drive_service:
        raise HTTPException(status_code=500, detail="Google Drive service not initialized.")

    results = []

    try:
        query = f"'{folder_id}' in parents and trashed = false and mimeType='application/pdf'"
        response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])[:limit]

        for file in files:
            file_id = file["id"]
            file_name = file["name"]
            temp_path = Path(tempfile.gettempdir()) / file_name

            try:
                # Download file
                download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                headers = {"Authorization": f"Bearer {credentials.token}"}
                res = requests.get(download_url, headers=headers)

                if res.status_code != 200:
                    raise Exception(f"Failed to download {file_name} from Google Drive.")

                with open(temp_path, "wb") as f:
                    f.write(res.content)

                result = await process_resume_file(temp_path, file_name, current_user, db)
                results.append(result)

            except Exception as e:
                results.append({
                    "file": file_name,
                    "success": False,
                    "message": str(e)
                })
            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        return {"summary": results}

    except Exception as e:
        logger.exception("Error in parse_resumes_from_drive")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
   

@router.post("/parse-resumes-upload")
async def parse_resumes_upload(
    files: List[UploadFile] = File(..., description="List of PDF resume files to upload and parse."),
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    creation_summary = []

    for file in files:
        file_name = file.filename
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(await file.read())
                temp_path = Path(temp_file.name)

            result = await process_resume_file(temp_path, file_name, current_user, db)
            creation_summary.append(result)

        except Exception as e:
            creation_summary.append({
                "file": file_name,
                "success": False,
                "message": str(e)
            })
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    return {"summary": creation_summary}
