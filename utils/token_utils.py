import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

def generate_interview_token(length: int = 32) -> str:
    """
    Generate a secure random token for interview access.
    
    Args:
        length: Length of the token to generate
        
    Returns:
        A secure random token string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_token_expiry(hours: int = 48) -> datetime:
    """
    Generate token expiry time.
    
    Args:
        hours: Number of hours from now when token should expire
        
    Returns:
        Timezone-aware datetime object for token expiry
    """
    return datetime.now(timezone.utc) + timedelta(hours=hours)

def is_token_expired(expiry_time: Optional[datetime]) -> bool:
    """
    Check if a token has expired.
    
    Args:
        expiry_time: The expiry time to check (can be None)
        
    Returns:
        True if token is expired, False otherwise
    """
    if expiry_time is None:
        return True
    
    # Ensure we're comparing timezone-aware datetimes
    current_time = datetime.now(timezone.utc)
    
    # If expiry_time is naive, assume it's UTC
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    
    return current_time > expiry_time

def validate_token_format(token: str) -> bool:
    """
    Validate that a token has the correct format.
    
    Args:
        token: The token to validate
        
    Returns:
        True if token format is valid, False otherwise
    """
    if not token:
        return False
    
    # Check length (should be 32 characters by default)
    if len(token) < 16 or len(token) > 64:
        return False
    
    # Check that it only contains alphanumeric characters
    return token.isalnum()

def get_current_utc_time() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)
