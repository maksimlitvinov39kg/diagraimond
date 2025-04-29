import os
from dotenv import load_dotenv
from openai import OpenAI


def load_prompt(filename):
    """
    Загружает содержимое промпта из файла.
    """
    prompt_path = os.path.join("prompts", filename)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


class Generator:
    def __init__(self):
        """
        Инициализация генератора с загрузкой системных промптов из файлов.
        """
        load_dotenv()
        api_key = os.getenv("HF_API_KEY")
        if api_key is None:
            raise ValueError("API key not found in environment variables.")

        self.client = OpenAI(
            base_url="https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-Coder-32B-Instruct/v1",
            api_key=api_key
        )

        # Загрузка промптов из файлов
        self.system_prompts = {
            "Bar Chart": load_prompt("barchart_prompt.txt"),
            "Line Graph": load_prompt("linegraph_prompt.txt"),
            "Pie Chart": load_prompt("piechart_prompt.txt"),
            "Process": load_prompt("process_prompt.txt"), 
        }

    def generate_diagram(self, diagram_type, description, user_id, generation_counter):
        """
        Генерирует Python-код диаграммы по описанию и возвращает результат:
        (success: bool, error: str|None, code_file: str, image_file: str|None)
        """
        system_prompt = self.system_prompts.get(diagram_type)
        if not system_prompt:
            return False, f"Unsupported diagram type: {diagram_type}", None, None

        output_code_file = f"output_{user_id}_{generation_counter}.py"
        output_image_file = f"output_{user_id}_{generation_counter}.png"

        try:
            result_image_path = self._generate_python_from_text(
                text=description,
                output_file=output_code_file,
                output_image_file=output_image_file,
                system_prompt=system_prompt
            )

            if result_image_path:
                return True, None, output_code_file, result_image_path
            else:
                return False, "Ошибка при выполнении кода", output_code_file, None
        except Exception as e:
            return False, f"Exception during generation: {str(e)}", None, None

    def _generate_python_from_text(self, text, output_file, output_image_file, system_prompt):
        """
        Генерация Python-скрипта на основе текстового описания и сохранение изображения.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Описание: {text} , file_name : {output_image_file}"}
        ]

        completion = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            temperature=0.7,
            n=1,
            max_tokens=1500,
        )

        generated_content = completion.choices[0].message.content

        try:
            if "```python" in generated_content:
                code_start = generated_content.find("```python") + len("```python")
                code_end = generated_content.find("```", code_start)
                cleaned_content = generated_content[code_start:code_end].strip()
            else:
                cleaned_content = generated_content.strip()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            print(f"Файл успешно сохранён: {output_file}")

            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    code = f.read()
                exec_globals = {}
                exec(code, exec_globals)
                # os.rename('output.png',output_image_file)
                print(f"Изображение создано: {output_image_file}")
                return output_image_file
            except Exception as e:
                print(f"Ошибка при выполнении кода: {e}")
                return None

        except Exception as e:
            print(f"Ошибка при обработке сгенерированного кода: {e}")
            return None