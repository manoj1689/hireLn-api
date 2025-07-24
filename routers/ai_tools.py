import uuid
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, UploadFile, File, Header, logger
from fastapi.middleware.cors import CORSMiddleware
import openai
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional, Union
from utils.openai_client import create_openai_chat
from dotenv import load_dotenv
import json
import logging
import re
import html
from requests import Session
from unstructured.partition.pdf import partition_pdf
from database import get_db
import pdfplumber
from io import BytesIO  # Importing BytesIO for handling file content
from models.schemas import (
    CandidateResponse,
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
    UserResponse
)
from auth.dependencies import get_current_user, get_user_or_interview_auth

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file
load_dotenv()



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
            "skills": candidate.skills or [],
            "experience": candidate.experience or "Not specified",
            "education": candidate.education or "Not specified",
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
            "skills": {
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
    # if job_experience:
    #     # you can customize this keyword extraction based on your data
    #     experience_keyword = "experience" if "experience" in job_experience.lower() else job_experience
    #     filters.append({
    #         "experience": {
    #             "contains": experience_keyword,
    #             "mode": "insensitive"
    #         }
    #     })

    if job_education:
        # partial match on "Bachelor", "Master", etc.
        edu_keyword = "Bachelor" if "bachelor" in job_education.lower() else job_education
        filters.append({
            "education": {
                "contains": edu_keyword,
                "mode": "insensitive"
            }
        })

    # Salary expectation filter with fallback to None
    salary_filter = {
        "OR": [
            {"salaryExpectation": None},
            {
                "AND": [
                    {"salaryExpectation": {"gte": job_salary_min}},
                    {"salaryExpectation": {"lte": job_salary_max}},
                ]
            }
        ]
    }

    filters.append(salary_filter)

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

@router.post("/pdf_to_text/")
async def pdf_to_text(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Converts a PDF file to plain text using a combination of unstructured and pdfplumber.
    """
    logger = logging.getLogger("pdf_to_text")
    logger.info("Received a PDF conversion request.")

    if file.content_type != "application/pdf":
        logger.error(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are allowed.")

    try:
        pdf_content = await file.read()
        pdf_stream = BytesIO(pdf_content)

        # Extract text using unstructured
        try:
            elements = partition_pdf(file=pdf_stream)
            unstructured_text = "\n".join(element.text for element in elements if element.text)
            logger.info("Extracted text using unstructured.")
        except Exception as e:
            logger.warning(f"Error using unstructured: {str(e)}")
            unstructured_text = ""

        # Reset the stream for further processing
        pdf_stream.seek(0)

        # Extract text using pdfplumber
        try:
            with pdfplumber.open(pdf_stream) as pdf:
                pdfplumber_text_pages = [page.extract_text() for page in pdf.pages]
                pdfplumber_text = "\n\n".join(pdfplumber_text_pages) if pdfplumber_text_pages else ""
                logger.info(f"Extracted {len(pdf.pages)} pages using pdfplumber.")
        except Exception as e:
            logger.warning(f"Error using pdfplumber: {str(e)}")
            pdfplumber_text = ""

        # Combine and clean the extracted text
        combined_text = f"[unstructured Output]\n{unstructured_text}\n\n[pdfplumber Output]\n{pdfplumber_text}".strip()
        combined_text = clean_extracted_text(combined_text)

        logger.info("Successfully combined text extraction results.")
        return {"text": combined_text}

    except Exception as e:
        logger.error("Error while reading PDF", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error while reading PDF: {str(e)}")


