from sqlalchemy import text, inspect
from database.connection import engine

def get_table_columns(table_name):
    """
    Получает список столбцов таблицы и их типы данных.
    
    Args:
        table_name (str): Имя таблицы
        
    Returns:
        list: Список кортежей (имя_столбца, тип_данных, обязательность)
    """
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    
    # Преобразуем информацию о столбцах в более удобный формат
    result = []
    for column in columns:
        name = column['name']
        column_type = str(column['type'])
        nullable = column['nullable']
        result.append((name, column_type, not nullable))
        
    return result

def get_primary_key_columns(table_name):
    """
    Получает список столбцов, составляющих первичный ключ таблицы.
    
    Args:
        table_name (str): Имя таблицы
        
    Returns:
        list: Список имен столбцов, входящих в первичный ключ
    """
    inspector = inspect(engine)
    pk_constraint = inspector.get_pk_constraint(table_name)
    return pk_constraint.get('constrained_columns', [])

def insert_into_table(table_name, column_values):
    """
    Вставляет новую запись в указанную таблицу.
    
    Args:
        table_name (str): Имя таблицы
        column_values (dict): Словарь {имя_столбца: значение}
        
    Returns:
        tuple: (успех, сообщение)
    """
    columns = ', '.join(column_values.keys())
    placeholders = ', '.join([f":{col}" for col in column_values.keys()])
    
    query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING *")
    
    try:
        with engine.connect() as connection:
            result = connection.execute(query, column_values)
            connection.commit()
            inserted_row = result.fetchone()
            return True, f"Запись успешно добавлена в таблицу {table_name}. ID: {inserted_row[0] if inserted_row else 'N/A'}"
    except Exception as e:
        return False, f"Ошибка при добавлении записи: {str(e)}"

def get_table_foreign_keys(table_name):
    """
    Получает информацию о внешних ключах таблицы.
    
    Args:
        table_name (str): Имя таблицы
        
    Returns:
        list: Список словарей с информацией о внешних ключах
    """
    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    # Преобразуем информацию о внешних ключах в более понятный формат
    result = []
    for fk in foreign_keys:
        result.append({
            'column': fk['constrained_columns'][0],
            'referenced_table': fk['referred_table'],
            'referenced_column': fk['referred_columns'][0]
        })
        
    return result

def get_reference_values(table_name, column_name):
    """
    Получает возможные значения для столбца с внешним ключом.
    
    Args:
        table_name (str): Имя таблицы, на которую ссылается внешний ключ
        column_name (str): Имя столбца в таблице, на который ссылается внешний ключ
        
    Returns:
        list: Список кортежей (id, отображаемое_значение)
    """
    # Для отображения добавим второй столбец, если он есть
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    
    # Ищем текстовый столбец для отображения (обычно name, title и т.п.)
    display_column = None
    for col in columns:
        if col['name'] != column_name and any(t in str(col['type']).lower() for t in ['char', 'text']):
            display_column = col['name']
            break
    
    if display_column:
        query = text(f"SELECT {column_name}, {display_column} FROM {table_name} ORDER BY {display_column}")
    else:
        query = text(f"SELECT {column_name}, {column_name} FROM {table_name} ORDER BY {column_name}")
    
    with engine.connect() as connection:
        result = connection.execute(query)
        return [(row[0], row[1]) for row in result.fetchall()]

def delete_from_table(table_name, column_name, value):
    """
    Удаляет запись из указанной таблицы по заданному значению столбца.
    
    Args:
        table_name (str): Имя таблицы
        column_name (str): Имя столбца для условия WHERE
        value: Значение для условия WHERE
        
    Returns:
        tuple: (успех, сообщение, количество_удаленных_строк)
    """
    query = text(f"DELETE FROM {table_name} WHERE {column_name} = :value RETURNING *")
    
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"value": value})
            deleted_rows = result.rowcount
            connection.commit()
            
            if deleted_rows > 0:
                return True, f"Успешно удалено записей: {deleted_rows}", deleted_rows
            else:
                return False, f"Записи с {column_name} = {value} не найдены", 0
    except Exception as e:
        return False, f"Ошибка при удалении записи: {str(e)}", 0

def get_column_values(table_name, column_name, limit=100):
    """
    Получает уникальные значения указанного столбца из таблицы.
    
    Args:
        table_name (str): Имя таблицы
        column_name (str): Имя столбца
        limit (int): Максимальное количество возвращаемых значений
        
    Returns:
        list: Список значений столбца
    """
    query = text(f"SELECT DISTINCT {column_name} FROM {table_name} ORDER BY {column_name} LIMIT :limit")
    
    with engine.connect() as connection:
        result = connection.execute(query, {"limit": limit})
        return [row[0] for row in result.fetchall()]

def update_table_value(table_name, condition_column, condition_value, update_column, new_value):
    """
    Обновляет значение в указанной таблице.
    
    Args:
        table_name (str): Имя таблицы
        condition_column (str): Имя столбца для условия WHERE
        condition_value: Значение для условия WHERE
        update_column (str): Имя обновляемого столбца
        new_value: Новое значение
        
    Returns:
        tuple: (успех, сообщение, количество_обновленных_строк)
    """
    query = text(f"UPDATE {table_name} SET {update_column} = :new_value WHERE {condition_column} = :condition_value RETURNING *")
    
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"new_value": new_value, "condition_value": condition_value})
            updated_rows = result.rowcount
            connection.commit()
            
            if updated_rows > 0:
                return True, f"Успешно обновлено записей: {updated_rows}", updated_rows
            else:
                return False, f"Записи с {condition_column} = {condition_value} не найдены", 0
    except Exception as e:
        return False, f"Ошибка при обновлении записи: {str(e)}", 0

def get_row_by_column_value(table_name, column_name, value):
    """
    Получает строку из таблицы по значению столбца.
    
    Args:
        table_name (str): Имя таблицы
        column_name (str): Имя столбца для условия WHERE
        value: Значение для условия WHERE
        
    Returns:
        dict: Словарь с данными строки {имя_столбца: значение}
    """
    query = text(f"SELECT * FROM {table_name} WHERE {column_name} = :value")
    
    with engine.connect() as connection:
        result = connection.execute(query, {"value": value})
        row = result.fetchone()
        
        if row:
            # Преобразуем строку в словарь
            column_names = list(result.keys())
            return {column_names[i]: row[i] for i in range(len(column_names))}
        else:
            return None