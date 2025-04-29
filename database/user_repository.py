from datetime import datetime
from sqlalchemy import text
from database.connection import engine

def get_or_create_user(telegram_id, username):
    """
    Get user by telegram_id or create a new user if not exists.
    Returns the user record.
    """
    default_role_id = 1
    
    query = text("SELECT * FROM users WHERE telegram_id = :telegram_id")
    with engine.connect() as connection:
        result = connection.execute(query, {"telegram_id": telegram_id})
        user = result.fetchone()
        
        if user:
            return user
        else:
            current_time = datetime.now()
            insert_query = text("""
                INSERT INTO users (telegram_id, name, registered_at, is_active) 
                VALUES (:telegram_id, :name, :registered_at, :is_active)
                RETURNING *
            """)
        
            result = connection.execute(
                insert_query, 
                {
                    "telegram_id": telegram_id,
                    "name": username,  
                    "registered_at": current_time,
                    "is_active": True
                }
            )
            new_user = result.fetchone()
            user_id = new_user.id

            # Assign default role to the new user
            insert_role_query = text("""
                INSERT INTO user_roles (user_id, role_id, assigned_at)
                VALUES (:user_id, :role_id, :assigned_at)
            """)

            connection.execute(
                insert_role_query,
                {
                    "user_id": user_id,
                    "role_id": default_role_id,
                    "assigned_at": current_time
                }
            )
            connection.commit()
            return new_user

def check_is_admin(telegram_id):
    """Check if user has admin role (role_id = 3)."""
    with engine.connect() as conn:
        query = text("""
            SELECT ur.role_id 
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE u.telegram_id = :telegram_id
        """)
        
        result = conn.execute(query, {"telegram_id": telegram_id}).scalar()
        return result == 3
    
def check_is_subscriber(telegram_id):
    """Check if user has subscriber role (role_id = 2) or admin role (role_id = 3)."""
    with engine.connect() as conn:
        query = text("""
            SELECT ur.role_id 
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE u.telegram_id = :telegram_id
        """)
        
        result = conn.execute(query, {"telegram_id": telegram_id}).scalar()
        return (result == 3 or result == 2)

def get_user_id_by_telegram_id(telegram_id):
    """Get user ID by telegram ID."""
    with engine.connect() as connection:
        query = text("""
            SELECT id FROM users 
            WHERE telegram_id = :telegram_id
        """)
        result = connection.execute(query, {"telegram_id": telegram_id})
        user = result.fetchone()
        return user[0] if user else None