from fastapi import APIRouter, HTTPException, status, Depends, Query, Header
from typing import List, Optional, Union
from datetime import datetime
from database import get_db
from models.schemas import (
    QuestionCreate, QuestionResponse, AnswerCreate, AnswerUpdate, AnswerResponse,
    EvaluationCreate, EvaluationUpdate, EvaluationResponse, EvaluationWithDetailsResponse,
    UserResponse
)
from auth.dependencies import get_current_user, get_user_or_interview_auth
from pydantic import BaseModel
from utils.openai_client import create_openai_chat  # Import your function
import json
import logging

router = APIRouter()

# ✅ Pydantic model for bulk upload
class QuestionBulkUploadRequest(BaseModel):
    questions: List[dict]  # List of {"question_text": "...", "expected_answer_format": "..."}

@router.post("/interview/{interview_id}/bulk-upload", response_model=List[QuestionResponse])
async def bulk_upload_questions_for_interview(
    interview_id: str,
    request: QuestionBulkUploadRequest,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """
    Bulk upload questions for a specific interview
    
    Body format:
    {
      "questions": [
        {
          "question_text": "Your question here?",
          "expected_answer_format": "Expected format description"
        }
      ]
    }
    """
    db = get_db()
    
    if not request.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No questions provided"
        )
    
    # Verify interview exists
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={"user": True}
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Authorization check
    if isinstance(auth_data, UserResponse):
        if interview.userId != auth_data.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add questions to this interview"
            )
    else:
        interview_data = auth_data
        if interview_data["interview"].id != interview_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Interview token doesn't match this interview"
            )
    
    # Create questions in bulk
    created_questions = []
    for question_item in request.questions:
        question_text = question_item.get("question_text", "").strip()
        expected_answer_format = question_item.get("expected_answer_format", "").strip()
        
        if not question_text:
            continue
            
        question_data = {
            "interviewId": interview_id,
            "questionText": question_text,
            "expectedAnswerFormat": expected_answer_format if expected_answer_format else None,
        }
            
        try:
            created_question = await db.question.create(data=question_data)
            created_questions.append(QuestionResponse(**created_question.dict()))
        except Exception as e:
            logging.error(f"Error creating question: {e}")
            continue
    
    if not created_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid questions could be created"
        )
    
    return created_questions

@router.get("/interview-questions/{interview_id}", response_model=List[QuestionResponse])
async def get_interview_questions(
    interview_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """Get all questions for an interview"""
    db = get_db()
    
    # Authorization checks
    if isinstance(auth_data, dict) and "interview" in auth_data:
        interview_data = auth_data["interview"]
        if interview_data.id != interview_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not valid for this interview"
            )
    elif isinstance(auth_data, UserResponse):
        interview = await db.interview.find_unique(
            where={"id": interview_id},
            include={"user": True}
        )
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        if interview.userId != auth_data.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view questions for this interview"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )
    
    # Get questions
    questions = await db.question.find_many(
        where={"interviewId": interview_id},
        order={"createdAt": "asc"}
    )
    
    return [QuestionResponse(**q.dict()) for q in questions]

# ✅ NEW: Create answer for a question
@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
async def create_answer(
    question_id: str,
    answer_data: AnswerCreate,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """Create an answer for a question"""
    db = get_db()
    
    question = await db.question.find_unique(
        where={"id": question_id},
        include={"interview": {"include": {"user": True}}}
    )
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Authorization checks
    if isinstance(auth_data, dict) and "interview" in auth_data:
        if auth_data["interview"].id != question.interviewId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to answer this question"
            )
    elif isinstance(auth_data, UserResponse):
        if question.interview.userId != auth_data.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to answer this question"
            )
    
    # Create answer
    answer = await db.answer.create(
        data={
            "answerText": answer_data.answerText,
            "questionId": question_id,
            "interviewId": question.interviewId
        }
    )
    
    return AnswerResponse(**answer.dict())

# ✅ NEW: Update answer
@router.put("/answers/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: str,
    answer_update: AnswerUpdate,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """Update an answer"""
    db = get_db()
    
    answer = await db.answer.find_unique(
        where={"id": answer_id},
        include={"question": {"include": {"interview": {"include": {"user": True}}}}}
    )
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )
    
    # Authorization checks
    if isinstance(auth_data, dict) and "interview" in auth_data:
        if auth_data["interview"].id != answer.interviewId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this answer"
            )
    elif isinstance(auth_data, UserResponse):
        if answer.question.interview.userId != auth_data.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this answer"
            )
    
    # Update answer
    updated_answer = await db.answer.update(
        where={"id": answer_id},
        data={"answerText": answer_update.answerText} if answer_update.answerText else {}
    )
    
    return AnswerResponse(**updated_answer.dict())

# ✅ NEW: Auto-Evaluation API using answer_id
@router.post("/answers/{answer_id}/auto-evaluate", response_model=EvaluationWithDetailsResponse)
async def auto_evaluate_answer(
    answer_id: str,
    knowledge_level: str = Query("intermediate", description="Knowledge level: beginner, intermediate, advanced"),
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """
    Auto-evaluate an answer by answer_id - gets question and answer from database,
    evaluates using AI, and creates/updates evaluation
    """
    db = get_db()
    
    try:
        # Get answer with question and interview data
        answer = await db.answer.find_unique(
            where={"id": answer_id},
            include={
                "question": {
                    "include": {
                        "interview": {"include": {"user": True}}
                    }
                }
            }
        )
        
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer not found"
            )
        
        # Authorization check
        if isinstance(auth_data, dict) and "interview" in auth_data:
            if auth_data["interview"].id != answer.interviewId:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to evaluate this answer"
                )
        elif isinstance(auth_data, UserResponse):
            if answer.question.interview.userId != auth_data.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to evaluate this answer"
                )
        
        # Perform AI evaluation
        prompt = f"""
        You are an expert interviewer evaluating a candidate's answer. Please evaluate the following:

        Question: {answer.question.questionText}
        Answer: {answer.answerText}
        Knowledge Level: {knowledge_level}

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

        messages = [
            {"role": "system", "content": "You are an expert interviewer and evaluator. Provide detailed, constructive feedback."},
            {"role": "user", "content": prompt}
        ]
        
        response = create_openai_chat(messages)
        content = response.choices[0].message.content.strip()

        # Extract JSON from the response
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_str = content[start_idx:end_idx]
            evaluation_data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse AI evaluation response"
            )

        # Get token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Check if evaluation already exists
        existing_evaluation = await db.evaluation.find_unique(
            where={"answerId": answer_id}
        )
        
        evaluation_update_data = {
            "questionText": answer.question.questionText,  # ✅ NEW: Store question text
            "answerText": answer.answerText,               # ✅ NEW: Store answer text
            "interviewId": answer.interviewId,                  # ✅ NEW: Store interview ID
            "factualAccuracy": evaluation_data.get("factualAccuracy", "Fair"),
            "factualAccuracyExplanation": evaluation_data.get("factualAccuracyExplanation", "No explanation provided"),
            "completeness": evaluation_data.get("completeness", "Fair"),
            "completenessExplanation": evaluation_data.get("completenessExplanation", "No explanation provided"),
            "relevance": evaluation_data.get("relevance", "Fair"),
            "relevanceExplanation": evaluation_data.get("relevanceExplanation", "No explanation provided"),
            "coherence": evaluation_data.get("coherence", "Fair"),
            "coherenceExplanation": evaluation_data.get("coherenceExplanation", "No explanation provided"),
            "score": float(evaluation_data.get("score", 3.0)),
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "finalEvaluation": evaluation_data.get("finalEvaluation", "No final evaluation provided"),
        }
        
        if existing_evaluation:
            # Update existing evaluation
            updated_evaluation = await db.evaluation.update(
                where={"answerId": answer_id},
                data=evaluation_update_data
            )
        else:
            # Create new evaluation
            updated_evaluation = await db.evaluation.create(
                data={
                    "answerId": answer_id,
                    **evaluation_update_data
                }
            )
        
        # Return combined response
        return EvaluationWithDetailsResponse(
            id=updated_evaluation.id,
            questionText=answer.question.questionText,
            answerText=answer.answerText,
            interviewId=answer.interviewId,
            expectedAnswerFormat=answer.question.expectedAnswerFormat,
            factualAccuracy=updated_evaluation.factualAccuracy,
            factualAccuracyExplanation=updated_evaluation.factualAccuracyExplanation,
            completeness=updated_evaluation.completeness,
            completenessExplanation=updated_evaluation.completenessExplanation,
            relevance=updated_evaluation.relevance,
            relevanceExplanation=updated_evaluation.relevanceExplanation,
            coherence=updated_evaluation.coherence,
            coherenceExplanation=updated_evaluation.coherenceExplanation,
            score=updated_evaluation.score,
            inputTokens=updated_evaluation.inputTokens,
            outputTokens=updated_evaluation.outputTokens,
            finalEvaluation=updated_evaluation.finalEvaluation,
            createdAt=updated_evaluation.createdAt,
            updatedAt=updated_evaluation.updatedAt,
            answeredAt=answer.answeredAt,
            evaluatedAt=updated_evaluation.evaluatedAt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-evaluation failed: {str(e)}"
        )

# ✅ NEW: Get evaluation by interview_id and answer_id
@router.get("/interviews/{interview_id}/answers/{answer_id}/evaluation", response_model=EvaluationWithDetailsResponse)
async def get_evaluation_by_interview_and_answer(
    interview_id: str,
    answer_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth)
):
    """Get evaluation by interview_id and answer_id"""
    db = get_db()
    
    # Get answer with evaluation, question, and interview data
    answer = await db.answer.find_unique(
        where={"id": answer_id},
        include={
            "question": {
                "include": {
                    "interview": {"include": {"user": True}}
                }
            },
            "evaluation": True
        }
    )
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )
    
    if answer.interviewId != interview_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer does not belong to the specified interview"
        )
    
    # Authorization check
    if isinstance(auth_data, dict) and "interview" in auth_data:
        if auth_data["interview"].id != interview_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this evaluation"
            )
    elif isinstance(auth_data, UserResponse):
        if answer.question.interview.userId != auth_data.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this evaluation"
            )
    
    if not answer.evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found for this answer"
        )
    
    # Return combined response
    return EvaluationWithDetailsResponse(
        id=answer.evaluation.id,
        questionText=answer.evaluation.questionText,  # ✅ Now from evaluation table
        answerText=answer.evaluation.answerText,      # ✅ Now from evaluation table
        expectedAnswerFormat=answer.question.expectedAnswerFormat,
        factualAccuracy=answer.evaluation.factualAccuracy,
        factualAccuracyExplanation=answer.evaluation.factualAccuracyExplanation,
        completeness=answer.evaluation.completeness,
        completenessExplanation=answer.evaluation.completenessExplanation,
        relevance=answer.evaluation.relevance,
        relevanceExplanation=answer.evaluation.relevanceExplanation,
        coherence=answer.evaluation.coherence,
        coherenceExplanation=answer.evaluation.coherenceExplanation,
        score=answer.evaluation.score,
        inputTokens=answer.evaluation.inputTokens,
        outputTokens=answer.evaluation.outputTokens,
        finalEvaluation=answer.evaluation.finalEvaluation,
        createdAt=answer.evaluation.createdAt,
        updatedAt=answer.evaluation.updatedAt,
        answeredAt=answer.answeredAt,
        evaluatedAt=answer.evaluation.evaluatedAt
    )

@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a question"""
    db = get_db()
    
    question = await db.question.find_unique(
        where={"id": question_id},
        include={"interview": {"include": {"user": True}}}
    )
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    if question.interview.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this question"
        )
    
    await db.question.delete(where={"id": question_id})
    
    return {"message": "Question deleted successfully"}

@router.get("/interview/{interview_id}/stats")
async def get_interview_question_stats(
    interview_id: str,
    current_user = Depends(get_current_user)
):
    """Get statistics for questions in an interview"""
    db = get_db()
    
    # Verify interview exists and belongs to user
    interview = await db.interview.find_unique(
        where={"id": interview_id},
        include={"user": True}
    )
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view stats for this interview"
        )
    
    # Get question and answer statistics
    questions = await db.question.find_many(
        where={"interviewId": interview_id},
        include={"answers": {"include": {"evaluation": True}}}
    )
    
    total_questions = len(questions)
    answered_questions = len([q for q in questions if q.answers])
    evaluated_questions = len([q for q in questions if q.answers and any(a.evaluation for a in q.answers)])
    
    average_score = None
    if evaluated_questions > 0:
        scores = []
        for question in questions:
            for answer in question.answers:
                if answer.evaluation and answer.evaluation.score is not None:
                    scores.append(answer.evaluation.score)
        if scores:
            average_score = sum(scores) / len(scores)
    
    return {
        "interviewId": interview_id,
        "totalQuestions": total_questions,
        "answeredQuestions": answered_questions,
        "evaluatedQuestions": evaluated_questions,
        "averageScore": average_score,
        "completionRate": (answered_questions / total_questions * 100) if total_questions > 0 else 0,
        "evaluationRate": (evaluated_questions / total_questions * 100) if total_questions > 0 else 0
    }
