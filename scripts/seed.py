import asyncio
from database import connect_db, get_db
from auth.jwt_handler import get_password_hash

async def seed_database():
    """Seed the database with initial data"""
    await connect_db()
    db = get_db()
    
    # Create a default company
    company = await db.company.create(
        data={
            "id": "default_company",
            "name": "TechCorp Inc.",
            "description": "A leading technology company",
            "website": "https://techcorp.com",
            "size": "100-500",
            "industry": "Technology"
        }
    )
    
    # Create a default user
    hashed_password = get_password_hash("password123")
    user = await db.user.create(
        data={
            "email": "admin@techcorp.com",
            "name": "Admin User",
            "password": hashed_password,
            "role": "ADMIN",
            "companyId": company.id
        }
    )
    
    # Create sample jobs
    jobs_data = [
        {
            "title": "Senior Frontend Developer",
            "description": "We are looking for a Senior Frontend Developer to join our team.",
            "department": "Engineering",
            "location": "San Francisco, CA",
            "employmentType": "FULL_TIME",
            "salaryMin": 120000,
            "salaryMax": 180000,
            "requirements": ["React", "TypeScript", "5+ years experience"],
            "responsibilities": ["Build user interfaces", "Collaborate with designers"],
            "skills": ["React", "TypeScript", "JavaScript", "CSS"],
            "status": "ACTIVE",
            "createdById": user.id,
            "companyId": company.id
        },
        {
            "title": "Product Manager",
            "description": "Seeking an experienced Product Manager to drive product strategy.",
            "department": "Product",
            "location": "Remote",
            "employmentType": "FULL_TIME",
            "salaryMin": 130000,
            "salaryMax": 200000,
            "requirements": ["3+ years PM experience", "Technical background"],
            "responsibilities": ["Define product roadmap", "Work with engineering"],
            "skills": ["Product Strategy", "Analytics", "Communication"],
            "status": "ACTIVE",
            "createdById": user.id,
            "companyId": company.id
        }
    ]
    
    for job_data in jobs_data:
        await db.job.create(data=job_data)
    
    # Create sample candidates
    candidates_data = [
        {
            "email": "john.doe@example.com",
            "name": "John Doe",
            "phone": "+1-555-0123",
            "skills": ["React", "TypeScript", "Node.js"],
            "experience": "5 years",
            "education": "Bachelor's in Computer Science",
            "location": "San Francisco, CA"
        },
        {
            "email": "jane.smith@example.com",
            "name": "Jane Smith",
            "phone": "+1-555-0124",
            "skills": ["Product Management", "Analytics", "Agile"],
            "experience": "4 years",
            "education": "MBA",
            "location": "New York, NY"
        }
    ]
    
    for candidate_data in candidates_data:
        await db.candidate.create(data=candidate_data)
    
    print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
