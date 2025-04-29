class Checker:
    def __init__(self, generator):
        """
        Инициализация чекера с существующим экземпляром Generator
        """
        self.generator = generator
        self.client = generator.client

    def fix_code(self, code, error_message):
        """
        Исправление некомпилируемого кода с помощью ИИ
        
        Args:
            code: Исходный код, который не компилируется
            error_message: Сообщение об ошибке компиляции
        
        Returns:
            str: Исправленный код
        """
        system_prompt = """You are a Python code fixer. 
        Your task is to fix the provided code that doesn't compile.
        Return only the fixed code without any explanations."""

        user_message = f"""
        The following code has compilation errors:
        
        ```python
        {code}
        ```
        
        Error message:
        {error_message}
        
        Please fix the code and return only the corrected version.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            completion = self.client.chat.completions.create(
                model="Qwen/Qwen2.5-Coder-32B-Instruct",
                messages=messages,
                temperature=0.2,  # Используем меньшую температуру для более консервативных исправлений
                n=1,
                max_tokens=1500,
            )

            fixed_content = completion.choices[0].message.content

            # Извлекаем код из markdown-разметки, если она есть
            if "```python" in fixed_content:
                code_start = fixed_content.find("```python") + len("```python")
                code_end = fixed_content.find("```", code_start)
                fixed_code = fixed_content[code_start:code_end].strip()
            else:
                fixed_code = fixed_content.strip()

            return fixed_code

        except Exception as e:
            print(f"Ошибка при исправлении кода: {e}")
            return None

    def check_and_fix(self, output_file, error_message):
        """
        Проверка и исправление кода в файле
        
        Args:
            output_file: Путь к файлу с некомпилируемым кодом
            error_message: Сообщение об ошибке компиляции
        """
        try:
            # Читаем код из файла
            with open(output_file, 'r', encoding='utf-8') as f:
                code = f.read()

            # Исправляем код
            fixed_code = self.fix_code(code, error_message)

            if fixed_code:
                # Записываем исправленный код обратно в файл
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                print(f"Код успешно исправлен и сохранен в {output_file}")
            else:
                print("Не удалось исправить код")

        except Exception as e:
            print(f"Ошибка при работе с файлом: {e}")