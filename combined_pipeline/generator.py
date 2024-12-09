import os
from dotenv import load_dotenv
import yaml
from openai import OpenAI


class Generator:
    def __init__(self, system_prompt_yaml="./system_prompt_yaml.txt", system_prompt_python="./system_prompt_python.txt", system_prompt_file=None):
        """
        Инициализация генератора с загрузкой системных промптов для разных режимов и API клиента.
        Если указан `system_prompt_file`, он будет использоваться как общий промпт для всех режимов.
        """
        load_dotenv()
        api_key = os.getenv("HF_API_KEY")
        if api_key is None:
            raise ValueError("API key not found in environment variables.")

        self.client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=api_key,
        )

        if system_prompt_file:
            with open(system_prompt_file, "r", encoding="utf-8") as f:
                self.system_prompt_yaml = f.read()
                self.system_prompt_python = self.system_prompt_yaml
        else:
            with open(system_prompt_yaml, "r", encoding="utf-8") as f:
                self.system_prompt_yaml = f.read()

            with open(system_prompt_python, "r", encoding="utf-8") as f:
                self.system_prompt_python = f.read()


    def _get_system_prompt(self, mode):
        """
        Получение системного промпта в зависимости от режима генерации.

        Args:
            mode: "yaml" или "python".
        """
        if mode == "yaml":
            return self.system_prompt_yaml
        elif mode == "python":
            return self.system_prompt_python
        else:
            raise ValueError("Invalid mode. Use 'yaml' or 'python'.")

    def generate_yaml_from_text(self, text, output_file="diagram.yaml"):
        """
        Генерация YAML из текстового описания.

        Args:
            text: Текстовое описание диаграммы.
            output_file: Имя файла для сохранения YAML.
        """
        self._generate_output_from_text(
            text=text,
            output_file=output_file,
            mode="yaml",
            file_format="yaml",
            max_tokens=1500,
        )

    def generate_python_from_text(self, text, output_file="graph_code.py"):
        """
        Генерация Python-кода для графовой модели из текстового описания.

        Args:
            text: Текстовое описание диаграммы.
            output_file: Имя файла для сохранения Python-кода.
        """
        self._generate_output_from_text(
            text=text,
            output_file=output_file,
            mode="python",
            file_format="python",
            max_tokens=1500,
        )

    def _generate_output_from_text(self, text, output_file, mode, file_format, max_tokens):
        """
        Общая функция для генерации выходных данных (YAML или Python-кода).

        Args:
            text: Текстовое описание.
            output_file: Путь к выходному файлу.
            mode: Режим генерации ("yaml" или "python").
            file_format: Формат файла ("yaml" или "python").
            max_tokens: Максимальное количество токенов.
        """
        system_prompt = self._get_system_prompt(mode)
        m_prompt = {"role": "system", "content": system_prompt}

        if mode == "yaml":
            user_message = f"Создай YAML описание диаграммы на основе следующего текста: {text}"
        elif mode == "python":
            user_message = f"На основе следующего текстового описания создай Python-код для графовой модели с использованием LangGraph. Описание: {text}"

        messages = [m_prompt, {"role": "user", "content": user_message}]

        completion = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            temperature=0.7 if mode == "python" else 0.9,
            n=1,
            max_tokens=max_tokens,
        )

        generated_content = completion.choices[0].message.content

        try:
            if f"```{file_format}" in generated_content:
                code_start = generated_content.find(f"```{file_format}") + len(f"```{file_format}")
                code_end = generated_content.find("```", code_start)
                cleaned_content = generated_content[code_start:code_end].strip()
            else:
                cleaned_content = generated_content.strip()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            print(f"Файл успешно сохранён: {output_file}")
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
