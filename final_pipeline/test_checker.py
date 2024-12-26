from generator import Generator
from checker import Checker

def test_checker_simple():
    # Создаем экземпляр Generator (используя ваш system_prompt)
    system_prompt = "You are a Python code generator..." 
    generator = Generator(system_prompt)
    
    # Создаем тестовый файл с некорректным кодом
    test_file = "test_code.py"
    incorrect_code = """
    def print_hello()
        print("Hello, World!")
    
    def calculate_sum(a b):
        return a + b
    """
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(incorrect_code)
    
    # Пытаемся выполнить код и получаем ошибку
    try:
        exec(incorrect_code)
    except SyntaxError as e:
        # Создаем checker и пытаемся исправить код
        checker = Checker(generator)
        checker.check_and_fix(test_file, str(e))
        
        # Проверяем исправленный код
        with open(test_file, "r", encoding="utf-8") as f:
            fixed_code = f.read()
        print("Исправленный код:")
        print(fixed_code)
        
        # Пробуем выполнить исправленный код
        try:
            exec(fixed_code)
            print("Код успешно исправлен и выполнен!")
        except Exception as e:
            print(f"Ошибка после исправления: {e}")

test_checker_simple()