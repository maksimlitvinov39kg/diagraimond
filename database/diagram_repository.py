from datetime import datetime
from sqlalchemy import text, inspect
from database.connection import engine

def get_diagram_types():
    """Retrieve all available diagram types from the database."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM diagram_types"))
        rows = result.fetchall()
        return [row[1] for row in rows]

def get_id_from_name(diagram_type):
    """Map diagram type name to its ID."""
    diagram_types = {
        "Bar Chart": 1,
        "Pie Chart": 2,
        "Process": 3,
        "Line Graph": 4
    }
    return diagram_types.get(diagram_type)

def add_diagram_request(user_id, prompt, diagram_type):
    """Add a new diagram request record to the database."""
    with engine.connect() as connection:
        current_time = datetime.now()
        diagram_id = get_id_from_name(diagram_type)
        
        insert_request_query = text("""
            INSERT INTO diagram_requests (user_id, prompt, created_at, diagram_type_id)
            VALUES (:user_id, :prompt, :created_at, :diagram_type_id) RETURNING id
        """)

        result = connection.execute(
            insert_request_query, 
            {
                "user_id": user_id,
                "prompt": prompt,
                "created_at": current_time,
                "diagram_type_id": diagram_id
            }
        )
        rows = result.fetchone()
        connection.commit()
        return rows[0]  # Return the request ID

def add_diagram_image(request_id, image_path, format="png"):
    """Add a new diagram image record associated with a request."""
    with engine.connect() as connection:
        current_time = datetime.now()
        
        insert_image_query = text("""
            INSERT INTO diagram_images (request_id, image_path, format, created_at)
            VALUES (:request_id, :image_path, :format, :created_at)
        """)
            
        connection.execute(
            insert_image_query,
            {
                "request_id": request_id,
                "image_path": image_path,
                "format": format,
                "created_at": current_time
            }
        )
        connection.commit()

def get_user_recent_prompts(telegram_id, limit=3):
    """Get the most recent prompts for a user."""
    with engine.connect() as connection:
        query = text("""
            SELECT prompt
            FROM diagram_requests dr
            JOIN users u ON dr.user_id = u.id
            WHERE u.telegram_id = :telegram_id
            ORDER BY dr.created_at DESC
            LIMIT :limit
        """)
        
        result = connection.execute(query, {"telegram_id": telegram_id, "limit": limit})
        return [row[0] for row in result.fetchall()]

def get_available_export_formats():
    """Get all available export formats."""
    with engine.connect() as connection:
        query = text("""
            SELECT name
            FROM export_formats
            WHERE is_active = TRUE
        """)
        result = connection.execute(query)
        return [row[0] for row in result.fetchall()]

def get_available_templates():
    """Get all available prompt templates."""
    with engine.connect() as connection:
        query = text("""
            SELECT name
            FROM prompt_templates
            WHERE is_public = TRUE
            ORDER BY name ASC
        """)
        result = connection.execute(query)
        return [row[0] for row in result.fetchall()]

def get_all_tables():
    """Get the names of all tables in the database."""
    inspector = inspect(engine)
    return inspector.get_table_names()

def add_favourite(telegram_id, diagram_id):
    with engine.connect() as connection:
        check_query = text("SELECT 1 FROM diagram_requests WHERE id = :diagram_id")
        exists = connection.execute(check_query, {"diagram_id": diagram_id}).scalar()
        print(exists)
        if not exists:
            return exists, None

        insert_query = text("""
            INSERT INTO user_favorites (user_id, diagram_id, saved_at)
            VALUES (
                (SELECT id FROM users WHERE telegram_id = :telegram_id),
                    :diagram_id,
                    NOW()
                )
        """)
        connection.execute(insert_query, {
            "telegram_id": telegram_id,
            "diagram_id": diagram_id
        })
        connection.commit()
        return exists

def get_favourites(telegram_id):
    with engine.connect() as connection:
            query = text("""
                SELECT uf.diagram_id, dr.prompt, uf.saved_at
                FROM user_favorites uf
                JOIN diagram_requests dr ON uf.diagram_id = dr.id
                WHERE uf.user_id = (SELECT id FROM users WHERE telegram_id = :telegram_id)
                ORDER BY uf.saved_at DESC
            """)
            result = connection.execute(query, {"telegram_id": telegram_id})
            rows = result.fetchall()
            return rows