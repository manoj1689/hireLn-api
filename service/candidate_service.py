import json
from typing import Tuple
from models.schemas import CandidateCreate, UserResponse
from service.activity_service import ActivityHelpers


async def create_candidate_from_parsed_data(
    candidate_data: CandidateCreate,
    current_user: UserResponse,
    db
) -> Tuple[bool, str]:
    try:
        # Already validated Pydantic model, so no need to recreate it
        existing_candidate = await db.candidate.find_unique(where={"email": candidate_data.email})
        if existing_candidate:
            return False, f"Candidate with email {candidate_data.email} already exists"
        
        candidate_dict = candidate_data.model_dump()

        for key in ["education","experience","certifications", "projects", "previousJobs", "personalInfo"]:
            if key in candidate_dict and candidate_dict[key] is not None:
                candidate_dict[key] = json.dumps(candidate_dict[key])

        candidate = await db.candidate.create(data=candidate_dict)

        await ActivityHelpers.log_candidate_added(
            user_id=current_user.id,
            candidate_id=candidate.id,
            candidate_name=candidate.name
        )

        return True, f"Candidate '{candidate.name}' created successfully"

    except Exception as e:
        return False, f"Failed to create candidate: {str(e)}"
