import os
import time

def safe_remove_file(file_path, max_attempts=5, delay=1):
    """
    Safely remove a file with multiple attempts.
    
    Args:
        file_path: Path to the file to remove
        max_attempts: Maximum number of deletion attempts
        delay: Delay between attempts in seconds
        
    Returns:
        Boolean indicating success
    """
    if not os.path.exists(file_path):
        return True
        
    attempt = 0
    while attempt < max_attempts:
        try:
            os.remove(file_path)
            return True
        except IOError:
            attempt += 1
            time.sleep(delay)
    
    return False

def generate_unique_filename(prefix, user_id, counter, extension):
    """
    Generate a unique filename for output files.
    
    Args:
        prefix: Prefix for the filename
        user_id: User ID to include in filename
        counter: Counter to ensure uniqueness
        extension: File extension (without dot)
        
    Returns:
        String with unique filename
    """
    return f"{prefix}_{user_id}_{counter}.{extension}"