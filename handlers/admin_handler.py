from telebot import types
from database.user_repository import check_is_admin
from database.diagram_repository import get_all_tables
from database.admin_repository import (
    get_table_columns, 
    get_primary_key_columns, 
    insert_into_table, 
    get_table_foreign_keys,
    get_reference_values,
    delete_from_table,
    get_column_values,
    update_table_value,
    get_row_by_column_value
)

# Отслеживание состояний для административных функций
admin_states = {}
admin_data = {}

def register_admin_handlers(bot):
    """Регистрация всех обработчиков, связанных с административными командами."""
    
    @bot.message_handler(commands=["admin"])
    def admin_access(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        admin_states[message.from_user.id] = 'admin_wait_for_actions'
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        insert_btn = types.KeyboardButton('INSERT')
        update_btn = types.KeyboardButton('UPDATE')
        delete_btn = types.KeyboardButton('DELETE')
        markup.add(insert_btn, update_btn, delete_btn)
        bot.send_message(
            message.chat.id, 
            "Добро пожаловать в панель администратора.\nВыберите действие:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == 'INSERT' and admin_states.get(message.from_user.id) == 'admin_wait_for_actions')
    def select_insert_action(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        tables = get_all_tables()
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [types.KeyboardButton(table) for table in tables]
        markup.add(*buttons)

        bot.send_message(
            message.chat.id, 
            "Выбрано действие: INSERT\nВыберите таблицу:",
            reply_markup=markup
        )
        admin_states[message.from_user.id] = 'admin_select_table'
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_select_table')
    def handle_table_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        table_name = message.text
        
        # Проверяем, что таблица существует
        tables = get_all_tables()
        if table_name not in tables:
            bot.send_message(message.chat.id, f"Таблица '{table_name}' не существует. Пожалуйста, выберите таблицу из списка.")
            return
            
        # Получаем информацию о столбцах таблицы
        columns = get_table_columns(table_name)
        foreign_keys = get_table_foreign_keys(table_name)
        primary_keys = get_primary_key_columns(table_name)
        
        # Сохраняем информацию о таблице для последующего использования
        admin_data[message.from_user.id] = {
            'table_name': table_name,
            'columns': columns,
            'foreign_keys': foreign_keys,
            'primary_keys': primary_keys,
            'column_values': {},
            'current_column_index': 0
        }
        
        # Запускаем процесс заполнения данных для столбцов
        start_column_input(message, bot)
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_input_column_value')
    def handle_column_value_input(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        # Получаем информацию о текущем столбце
        current_index = data['current_column_index']
        column_name, column_type, required = data['columns'][current_index]
        
        # Сохраняем введенное значение
        if message.text != 'NULL' and message.text != 'Пропустить':
            data['column_values'][column_name] = message.text
        
        # Переходим к следующему столбцу
        data['current_column_index'] += 1
        
        # Если обработали все столбцы, выполняем вставку данных
        if data['current_column_index'] >= len(data['columns']):
            success, msg = insert_into_table(data['table_name'], data['column_values'])
            bot.send_message(message.chat.id, msg)
            
            # Сбрасываем состояние пользователя
            admin_states[user_id] = 'admin_wait_for_actions'
            del admin_data[user_id]
            
            # Показываем меню администратора
            markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
            insert_btn = types.KeyboardButton('INSERT')
            update_btn = types.KeyboardButton('UPDATE')
            delete_btn = types.KeyboardButton('DELETE')
            markup.add(insert_btn, update_btn, delete_btn)
            bot.send_message(
                message.chat.id, 
                "Выберите следующее действие:",
                reply_markup=markup
            )
        else:
            # Продолжаем заполнение следующего столбца
            start_column_input(message, bot)
            
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_select_fk_value')
    def handle_fk_value_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        # Получаем информацию о текущем столбце
        current_index = data['current_column_index']
        column_name, _, _ = data['columns'][current_index]
        
        # Ищем соответствующий внешний ключ
        fk_info = None
        for fk in data['foreign_keys']:
            if fk['column'] == column_name:
                fk_info = fk
                break
                
        if not fk_info:
            bot.send_message(message.chat.id, "Произошла ошибка с внешним ключом. Пожалуйста, начните заново.")
            return
            
        # Получаем выбранное значение
        selected_text = message.text
        
        # Находим соответствующий ID
        reference_values = get_reference_values(fk_info['referenced_table'], fk_info['referenced_column'])
        selected_id = None
        
        for id_val, display_val in reference_values:
            if str(display_val) == selected_text:
                selected_id = id_val
                break
                
        if selected_id is None:
            bot.send_message(message.chat.id, "Неверное значение. Пожалуйста, выберите из списка.")
            return
            
        # Сохраняем значение внешнего ключа
        data['column_values'][column_name] = selected_id
        
        # Переходим к следующему столбцу
        data['current_column_index'] += 1
        
        # Если обработали все столбцы, выполняем вставку данных
        if data['current_column_index'] >= len(data['columns']):
            success, msg = insert_into_table(data['table_name'], data['column_values'])
            bot.send_message(message.chat.id, msg)
            
            # Сбрасываем состояние пользователя
            admin_states[user_id] = 'admin_wait_for_actions'
            del admin_data[user_id]
            
            # Показываем меню администратора
            markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            insert_btn = types.KeyboardButton('INSERT')
            markup.add(insert_btn)
            bot.send_message(
                message.chat.id, 
                "Выберите следующее действие:",
                reply_markup=markup
            )
        else:
            # Продолжаем заполнение следующего столбца
            start_column_input(message, bot)

    @bot.message_handler(func=lambda message: message.text == 'DELETE' and admin_states.get(message.from_user.id) == 'admin_wait_for_actions')
    def select_delete_action(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        tables = get_all_tables()
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [types.KeyboardButton(table) for table in tables]
        markup.add(*buttons)

        bot.send_message(
            message.chat.id, 
            "Выбрано действие: DELETE\nВыберите таблицу для удаления данных:",
            reply_markup=markup
        )
        admin_states[message.from_user.id] = 'admin_delete_select_table'
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_delete_select_table')
    def handle_delete_table_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        table_name = message.text
        
        # Проверяем, что таблица существует
        tables = get_all_tables()
        if table_name not in tables:
            bot.send_message(message.chat.id, f"Таблица '{table_name}' не существует. Пожалуйста, выберите таблицу из списка.")
            return
            
        # Получаем информацию о столбцах таблицы
        columns = get_table_columns(table_name)
        primary_keys = get_primary_key_columns(table_name)
        
        # Создаем кнопки для выбора столбца для условия удаления
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # Предпочтительно используем первичные ключи или ID-поля
        for col_name, col_type, _ in columns:
            if col_name in primary_keys or col_name.lower() in ['id', f"{table_name.lower()}_id"]:
                markup.add(types.KeyboardButton(col_name))
        
        # Добавляем остальные столбцы
        for col_name, col_type, _ in columns:
            if col_name not in primary_keys and col_name.lower() not in ['id', f"{table_name.lower()}_id"]:
                markup.add(types.KeyboardButton(col_name))
                
        admin_data[message.from_user.id] = {
            'table_name': table_name,
            'columns': columns,
            'primary_keys': primary_keys
        }
        
        admin_states[message.from_user.id] = 'admin_delete_select_column'
        bot.send_message(
            message.chat.id, 
            "Выберите столбец, по которому будет выполняться удаление:",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_delete_select_column')
    def handle_delete_column_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        column_name = message.text
        
        # Проверяем, что выбран существующий столбец
        column_exists = False
        for col_name, _, _ in data['columns']:
            if col_name == column_name:
                column_exists = True
                break
                
        if not column_exists:
            bot.send_message(message.chat.id, f"Столбец '{column_name}' не существует. Пожалуйста, выберите столбец из списка.")
            return
            
        # Сохраняем выбранный столбец
        data['delete_column'] = column_name
        
        # Получаем список возможных значений этого столбца
        values = get_column_values(data['table_name'], column_name)
        
        if not values:
            bot.send_message(message.chat.id, f"В таблице '{data['table_name']}' нет данных в столбце '{column_name}'.")
            
            # Возвращаемся к выбору действий
            admin_states[user_id] = 'admin_wait_for_actions'
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            insert_btn = types.KeyboardButton('INSERT')
            delete_btn = types.KeyboardButton('DELETE')
            markup.add(insert_btn, delete_btn)
            bot.send_message(
                message.chat.id, 
                "Выберите действие:",
                reply_markup=markup
            )
            return
            
        # Создаем кнопки для выбора значения
        markup = types.ReplyKeyboardMarkup(row_width=1)
        
        # Ограничиваем количество отображаемых значений
        max_buttons = 20
        for i, value in enumerate(values):
            if i >= max_buttons:
                break
            markup.add(types.KeyboardButton(str(value)))
            
        admin_states[user_id] = 'admin_delete_select_value'
        bot.send_message(
            message.chat.id, 
            f"Выберите значение для условия WHERE {column_name} = ?:",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_delete_select_value')
    def handle_delete_value_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        value = message.text
        column_name = data['delete_column']
        table_name = data['table_name']
        
        # Удаляем записи
        success, msg, rows = delete_from_table(table_name, column_name, value)
        bot.send_message(message.chat.id, msg)
        
        # Возвращаемся к выбору действий
        admin_states[user_id] = 'admin_wait_for_actions'
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        insert_btn = types.KeyboardButton('INSERT')
        update_btn = types.KeyboardButton('UPDATE')
        delete_btn = types.KeyboardButton('DELETE')
        markup.add(insert_btn, update_btn, delete_btn)
        bot.send_message(
            message.chat.id, 
            "Выберите следующее действие:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == 'UPDATE' and admin_states.get(message.from_user.id) == 'admin_wait_for_actions')
    def select_update_action(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        tables = get_all_tables()
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [types.KeyboardButton(table) for table in tables]
        markup.add(*buttons)

        bot.send_message(
            message.chat.id, 
            "Выбрано действие: UPDATE\nВыберите таблицу для изменения данных:",
            reply_markup=markup
        )
        admin_states[message.from_user.id] = 'admin_update_select_table'
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_select_table')
    def handle_update_table_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        table_name = message.text
        
        # Проверяем, что таблица существует
        tables = get_all_tables()
        if table_name not in tables:
            bot.send_message(message.chat.id, f"Таблица '{table_name}' не существует. Пожалуйста, выберите таблицу из списка.")
            return
            
        # Получаем информацию о столбцах таблицы
        columns = get_table_columns(table_name)
        primary_keys = get_primary_key_columns(table_name)
        
        # Создаем кнопки для выбора столбца для условия WHERE
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # Предпочтительно используем первичные ключи или ID-поля
        for col_name, col_type, _ in columns:
            if col_name in primary_keys or col_name.lower() in ['id', f"{table_name.lower()}_id"]:
                markup.add(types.KeyboardButton(col_name))
        
        # Добавляем остальные столбцы
        for col_name, col_type, _ in columns:
            if col_name not in primary_keys and col_name.lower() not in ['id', f"{table_name.lower()}_id"]:
                markup.add(types.KeyboardButton(col_name))
                
        admin_data[message.from_user.id] = {
            'table_name': table_name,
            'columns': columns,
            'primary_keys': primary_keys
        }
        
        admin_states[message.from_user.id] = 'admin_update_select_where_column'
        bot.send_message(
            message.chat.id, 
            "Выберите столбец для условия WHERE (по какому полю искать запись):",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_select_where_column')
    def handle_update_where_column_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        column_name = message.text
        
        # Проверяем, что выбран существующий столбец
        column_exists = False
        for col_name, _, _ in data['columns']:
            if col_name == column_name:
                column_exists = True
                break
                
        if not column_exists:
            bot.send_message(message.chat.id, f"Столбец '{column_name}' не существует. Пожалуйста, выберите столбец из списка.")
            return
            
        # Сохраняем выбранный столбец
        data['where_column'] = column_name
        
        # Получаем список возможных значений этого столбца
        values = get_column_values(data['table_name'], column_name)
        
        if not values:
            bot.send_message(message.chat.id, f"В таблице '{data['table_name']}' нет данных в столбце '{column_name}'.")
            
            # Возвращаемся к выбору действий
            admin_states[user_id] = 'admin_wait_for_actions'
            markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
            insert_btn = types.KeyboardButton('INSERT')
            update_btn = types.KeyboardButton('UPDATE')
            delete_btn = types.KeyboardButton('DELETE')
            markup.add(insert_btn, update_btn, delete_btn)
            bot.send_message(
                message.chat.id, 
                "Выберите действие:",
                reply_markup=markup
            )
            return
            
        # Создаем кнопки для выбора значения
        markup = types.ReplyKeyboardMarkup(row_width=1)
        
        # Ограничиваем количество отображаемых значений
        max_buttons = 20
        for i, value in enumerate(values):
            if i >= max_buttons:
                break
            markup.add(types.KeyboardButton(str(value)))
            
        admin_states[user_id] = 'admin_update_select_where_value'
        bot.send_message(
            message.chat.id, 
            f"Выберите значение для условия WHERE {column_name} = ?:",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_select_where_value')
    def handle_update_where_value_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        where_value = message.text
        where_column = data['where_column']
        table_name = data['table_name']
        
        # Сохраняем выбранное значение
        data['where_value'] = where_value
        
        # Получаем запись для отображения текущих значений
        row = get_row_by_column_value(table_name, where_column, where_value)
        
        if not row:
            bot.send_message(message.chat.id, f"Запись с {where_column} = {where_value} не найдена.")
            # Возвращаемся к выбору действий
            admin_states[user_id] = 'admin_wait_for_actions'
            markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
            insert_btn = types.KeyboardButton('INSERT')
            update_btn = types.KeyboardButton('UPDATE')
            delete_btn = types.KeyboardButton('DELETE')
            markup.add(insert_btn, update_btn, delete_btn)
            bot.send_message(
                message.chat.id, 
                "Выберите действие:",
                reply_markup=markup
            )
            return
            
        # Создаем кнопки для выбора столбца для обновления
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        # Исключаем первичные ключи из списка обновляемых столбцов
        for col_name, col_type, _ in data['columns']:
            if col_name not in data['primary_keys']:
                markup.add(types.KeyboardButton(col_name))
                
        # Формируем текущие значения для отображения
        current_values = "\n".join([f"{col}: {val}" for col, val in row.items()])
        
        admin_states[user_id] = 'admin_update_select_column'
        bot.send_message(
            message.chat.id, 
            f"Текущие значения записи:\n{current_values}\n\nВыберите столбец для обновления:",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_select_column')
    def handle_update_column_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        update_column = message.text
        
        # Проверяем, что выбран существующий столбец
        column_exists = False
        column_info = None
        for col_info in data['columns']:
            if col_info[0] == update_column:
                column_exists = True
                column_info = col_info
                break
                
        if not column_exists:
            bot.send_message(message.chat.id, f"Столбец '{update_column}' не существует. Пожалуйста, выберите столбец из списка.")
            return
            
        # Сохраняем выбранный столбец
        data['update_column'] = update_column
        
        # Проверяем, является ли столбец внешним ключом
        foreign_keys = get_table_foreign_keys(data['table_name'])
        is_foreign_key = False
        fk_info = None
        
        for fk in foreign_keys:
            if fk['column'] == update_column:
                is_foreign_key = True
                fk_info = fk
                break
                
        if is_foreign_key and fk_info:
            # Если столбец - внешний ключ, показываем возможные значения
            admin_states[user_id] = 'admin_update_select_fk_value'
            
            reference_values = get_reference_values(fk_info['referenced_table'], fk_info['referenced_column'])
            
            markup = types.ReplyKeyboardMarkup(row_width=1)
            buttons = [types.KeyboardButton(str(display_val)) for _, display_val in reference_values]
            markup.add(*buttons)
            
            bot.send_message(
                message.chat.id, 
                f"Выберите новое значение для столбца '{update_column}':",
                reply_markup=markup
            )
        else:
            # Обычный ввод значения
            admin_states[user_id] = 'admin_update_input_value'
            
            # Получаем текущее значение
            row = get_row_by_column_value(data['table_name'], data['where_column'], data['where_value'])
            current_value = row.get(update_column, 'NULL') if row else 'NULL'
            
            markup = types.ReplyKeyboardRemove()
            
            bot.send_message(
                message.chat.id, 
                f"Текущее значение столбца '{update_column}': {current_value}\n\nВведите новое значение:",
                reply_markup=markup
            )
            
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_input_value')
    def handle_update_value_input(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        new_value = message.text
        
        # Обновляем значение в базе данных
        success, msg, rows = update_table_value(
            data['table_name'],
            data['where_column'],
            data['where_value'],
            data['update_column'],
            new_value
        )
        
        bot.send_message(message.chat.id, msg)
        
        # Возвращаемся к выбору действий
        admin_states[user_id] = 'admin_wait_for_actions'
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        insert_btn = types.KeyboardButton('INSERT')
        update_btn = types.KeyboardButton('UPDATE')
        delete_btn = types.KeyboardButton('DELETE')
        markup.add(insert_btn, update_btn, delete_btn)
        bot.send_message(
            message.chat.id, 
            "Выберите следующее действие:",
            reply_markup=markup
        )
        
    @bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'admin_update_select_fk_value')
    def handle_update_fk_value_selection(message):
        if not check_is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Вы не имеете доступа.")
            return
            
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        selected_text = message.text
        update_column = data['update_column']
        
        # Ищем соответствующий внешний ключ
        foreign_keys = get_table_foreign_keys(data['table_name'])
        fk_info = None
        
        for fk in foreign_keys:
            if fk['column'] == update_column:
                fk_info = fk
                break
                
        if not fk_info:
            bot.send_message(message.chat.id, "Произошла ошибка с внешним ключом. Пожалуйста, начните заново.")
            return
            
        # Находим соответствующий ID
        reference_values = get_reference_values(fk_info['referenced_table'], fk_info['referenced_column'])
        selected_id = None
        
        for id_val, display_val in reference_values:
            if str(display_val) == selected_text:
                selected_id = id_val
                break
                
        if selected_id is None:
            bot.send_message(message.chat.id, "Неверное значение. Пожалуйста, выберите из списка.")
            return
            
        # Обновляем значение в базе данных
        success, msg, rows = update_table_value(
            data['table_name'],
            data['where_column'],
            data['where_value'],
            update_column,
            selected_id
        )
        
        bot.send_message(message.chat.id, msg)
        
        # Возвращаемся к выбору действий
        admin_states[user_id] = 'admin_wait_for_actions'
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        insert_btn = types.KeyboardButton('INSERT')
        update_btn = types.KeyboardButton('UPDATE')
        delete_btn = types.KeyboardButton('DELETE')
        markup.add(insert_btn, update_btn, delete_btn)
        bot.send_message(
            message.chat.id, 
            "Выберите следующее действие:",
            reply_markup=markup
        )
        user_id = message.from_user.id
        data = admin_data.get(user_id)
        
        if not data:
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
            return
            
        current_index = data['current_column_index']
        if current_index >= len(data['columns']):
            # Все столбцы обработаны
            return
            
        column_name, column_type, required = data['columns'][current_index]
        
        # Проверяем, является ли столбец первичным ключом или автоинкрементным
        is_primary = column_name in data['primary_keys']
        is_autoincrement = 'integer' in column_type.lower() and is_primary
        
        # Пропускаем автоинкрементные столбцы
        if is_autoincrement:
            data['current_column_index'] += 1
            start_column_input(message, bot)
            return
            
        # Проверяем, является ли столбец внешним ключом
        is_foreign_key = False
        fk_info = None
        
        for fk in data['foreign_keys']:
            if fk['column'] == column_name:
                is_foreign_key = True
                fk_info = fk
                break
                
        if is_foreign_key and fk_info:
            # Если столбец - внешний ключ, показываем возможные значения
            admin_states[user_id] = 'admin_select_fk_value'
            
            reference_values = get_reference_values(fk_info['referenced_table'], fk_info['referenced_column'])
            
            markup = types.ReplyKeyboardMarkup(row_width=1)
            buttons = [types.KeyboardButton(str(display_val)) for _, display_val in reference_values]
            markup.add(*buttons)
            
            bot.send_message(
                message.chat.id, 
                f"Выберите значение для столбца '{column_name}' (тип: {column_type}, обязательный: {'Да' if required else 'Нет'}):",
                reply_markup=markup
            )
        else:
            # Обычный ввод значения
            admin_states[user_id] = 'admin_input_column_value'
            
            markup = types.ReplyKeyboardRemove()
            if not required:
                markup = types.ReplyKeyboardMarkup(row_width=1)
                markup.add(types.KeyboardButton('NULL'), types.KeyboardButton('Пропустить'))
                
            bot.send_message(
                message.chat.id, 
                f"Введите значение для столбца '{column_name}' (тип: {column_type}, обязательный: {'Да' if required else 'Нет'}):",
                reply_markup=markup
            )

def start_column_input(message, bot):
    """
    Запускает процесс ввода значения для текущего столбца.
    
    Args:
        message: Сообщение Telegram
        bot: Экземпляр бота Telegram
    """
    user_id = message.from_user.id
    data = admin_data.get(user_id)
    
    if not data:
        bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните заново с команды /admin.")
        return
        
    current_index = data['current_column_index']
    if current_index >= len(data['columns']):
        # Все столбцы обработаны
        return
        
    column_name, column_type, required = data['columns'][current_index]
    
    # Проверяем, является ли столбец первичным ключом или автоинкрементным
    is_primary = column_name in data['primary_keys']
    is_autoincrement = 'integer' in column_type.lower() and is_primary
    
    # Пропускаем автоинкрементные столбцы
    if is_autoincrement:
        data['current_column_index'] += 1
        start_column_input(message, bot)
        return
        
    # Проверяем, является ли столбец внешним ключом
    is_foreign_key = False
    fk_info = None
    
    for fk in data['foreign_keys']:
        if fk['column'] == column_name:
            is_foreign_key = True
            fk_info = fk
            break
            
    if is_foreign_key and fk_info:
        # Если столбец - внешний ключ, показываем возможные значения
        admin_states[user_id] = 'admin_select_fk_value'
        
        reference_values = get_reference_values(fk_info['referenced_table'], fk_info['referenced_column'])
        
        markup = types.ReplyKeyboardMarkup(row_width=1)
        buttons = [types.KeyboardButton(str(display_val)) for _, display_val in reference_values]
        markup.add(*buttons)
        
        bot.send_message(
            message.chat.id, 
            f"Выберите значение для столбца '{column_name}' (тип: {column_type}, обязательный: {'Да' if required else 'Нет'}):",
            reply_markup=markup
        )
    else:
        # Обычный ввод значения
        admin_states[user_id] = 'admin_input_column_value'
        
        markup = types.ReplyKeyboardRemove()
        if not required:
            markup = types.ReplyKeyboardMarkup(row_width=1)
            markup.add(types.KeyboardButton('NULL'), types.KeyboardButton('Пропустить'))
            
        bot.send_message(
            message.chat.id, 
            f"Введите значение для столбца '{column_name}' (тип: {column_type}, обязательный: {'Да' if required else 'Нет'}):",
            reply_markup=markup
        )