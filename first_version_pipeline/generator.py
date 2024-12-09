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
            
    def generate_yaml_from_text(self, text, output_file="diagram.yaml"):
        """
        Генерирует YAML из текстового описания с помощью OpenAI и сохраняет в файл.

        Args:
            text: Текстовое описание диаграммы.
            output_file: Путь к выходному YAML файлу.
        """
        m_prompt = {"role": "system", "content": self.system_prompt}
        message = f"Создай YAML описание диаграммы на основе следующего текста: {text}"

        messages = [
            m_prompt,
            {"role": "user", "content": message}
        ]

        completion = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            temperature=0.9,
            n=1,
            max_tokens=1500,
        )

        yaml_content = completion.choices[0].message.content

        try:
            
            if "```yaml" in yaml_content:
                yaml_start = yaml_content.find("```yaml") + len("```yaml")
                yaml_end = yaml_content.find("```", yaml_start)
                yaml_cleaned = yaml_content[yaml_start:yaml_end].strip()
            else:
                yaml_cleaned = yaml_content.strip()

            yaml_data = yaml.safe_load(yaml_cleaned)

            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
            print(f"YAML успешно сохранен в файл: {output_file}")
        except yaml.YAMLError as e:
            print(f"Ошибка при обработке YAML данных: {e}")
        except Exception as e:
            print(f"Ошибка при сохранении YAML в файл: {e}")


