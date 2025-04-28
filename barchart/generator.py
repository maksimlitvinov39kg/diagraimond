import os
from generator import Generator

class BarChartGenerator(Generator):
    def __init__(self, prompt_type="python"):
        """
        Инициализация генератора для столбчатой диаграммы.

        Args:
            prompt_type (str): Тип промпта ("python" или "yaml").
        """
        if prompt_type not in ["python", "yaml"]:
            raise ValueError("Invalid prompt_type. Must be 'python' or 'yaml'.")

        if prompt_type == "python":
            prompt_file = os.path.join(os.path.dirname(__file__), 'system_prompt_python.txt')
        else:
            prompt_file = os.path.join(os.path.dirname(__file__), 'system_prompt_yaml.txt')
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()

        if prompt_type == "python":
            super().__init__(system_prompt_python=prompt_content)
        else:
            super().__init__(system_prompt_python=None, system_prompt_yaml=prompt_content)
