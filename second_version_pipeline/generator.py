import os
from dotenv import load_dotenv
import yaml
from openai import OpenAI

class Generator:
    def __init__(self, system_prompt_file="./system_prompt.txt"):
        """
        Инициализация генератора с загрузкой системного промпта и API клиента.
        """
        load_dotenv()
        api_key = os.getenv("HF_API_KEY")
        if api_key is None:
            raise ValueError("API key not found in environment variables.")

        self.client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=api_key
        )

        with open(system_prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
            
    def generate_python_from_text(self, text, output_file="graph_code.py"):
        """
        Генерирует Python-код для графовой модели из текстового описания и сохраняет его в файл.

        Args:
            text: Текстовое описание диаграммы.
            output_file: Путь к выходному Python-файлу.
        """
        m_prompt = {"role": "system", "content": self.system_prompt}
        message = (
            f"На основе следующего текстового описания создай Python-код для графовой модели с использованием LangGraph. "
            f"Опиши узлы и связи согласно этапам: {text}"
        )

        messages = [
            m_prompt,
            {"role": "user", "content": message}
        ]

        completion = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            temperature=0.7,
            n=1,
            max_tokens=1500,
        )

        python_code = completion.choices[0].message.content

        try:
            if "```python" in python_code:
                code_start = python_code.find("```python") + len("```python")
                code_end = python_code.find("```", code_start)
                code_cleaned = python_code[code_start:code_end].strip()
            else:
                code_cleaned = python_code.strip()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(code_cleaned)
            print(f"Python-код успешно сохранен в файл: {output_file}")
        except Exception as e:
            print(f"Ошибка при сохранении Python-кода в файл: {e}")

