import os
from dotenv import load_dotenv
from openai import OpenAI

class Generator:
    def __init__(self, system_prompt_python, system_prompt_yaml=None):
        """
        Инициализация генератора с загрузкой системных промптов для разных типов диаграмм.
        """
        load_dotenv()
        api_key = os.getenv("HF_API_KEY")
        if api_key is None:
            raise ValueError("API key not found in environment variables.")
        
        self.client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=api_key,
        )

        self.system_prompt_python = system_prompt_python
        self.system_prompt_yaml = system_prompt_yaml

    def generate_yaml_from_text(self, text, output_file="process_diagram.yaml"):
        """
        Генерация YAML для процессной диаграммы.
        """
        self._generate_output_from_text(
            text=text,
            output_file=output_file,
            mode="yaml",
            file_format="yaml",
            max_tokens=3000,
        )

    def generate_python_from_text(self, text, output_file="graph_code.py",output_image_file = "graph_output.png"):
        """
        Генерация Python-кода для графовой модели из текстового описания.
        """
        self._generate_output_from_text(
            text=text,
            output_file=output_file,
            output_image_file = output_image_file,
            mode="python",
            file_format="python",
            max_tokens=1500,
        )

    def _generate_output_from_text(self, text, output_file, output_image_file, mode, file_format, max_tokens):
        """
        Общая функция для генерации выходных данных (Python-код или YAML).

        Args:
            text: Текстовое описание.
            output_file: Путь к выходному файлу.
            mode: Режим генерации ("yaml" или "python").
            file_format: Формат файла ("yaml" или "python").
            max_tokens: Максимальное количество токенов.
        """
        if mode == "yaml":
            system_prompt = self.system_prompt_yaml
        else:
            system_prompt = self.system_prompt_python
        m_prompt = {"role": "system", "content": system_prompt}

        user_message = f"Описание: {text}"

        messages = [m_prompt, {"role": "user", "content": user_message}]

        completion = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            temperature=0.7,
            n=1,
            max_tokens=max_tokens,
        )

        generated_content = completion.choices[0].message.content

        try:
            if f"```{file_format}" in generated_content:
                code_start = generated_content.find(f"```{file_format}") + len(f"```{file_format}")
                code_end = generated_content.find("```", code_start)
                cleaned_content = generated_content[code_start:code_end].strip()
                cleaned_content.replace("output.png", output_image_file)
            else:
                cleaned_content = generated_content.strip()
            cleaned_content = cleaned_content.replace("plt.savefig(\"output.png\")", "plt.savefig(\""+output_image_file+"\")")
            print(cleaned_content)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            print(f"Файл успешно сохранён: {output_file}")
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
'''import matplotlib.pyplot as plt

# Данные для анализа
X1 = [20230131, 20230228, 20230331, 20230430, 20230531, 20230630, 20230731, 20230831, 20230930, 20231031, 20231130, 20231231]
Y1 = [4.9671, 3.6174, 13.6075, 28.4551, 32.4912, 26.1737, 27.4896, 36.1224, 43.4145, 38.4040, 40.6321, 34.4565]

# Построение графика
plt.figure(figsize=(16, 9))
plt.plot(X1, Y1, label="Значения", color="green")

# Настройки графика
plt.title("Значения по месяцам 2023 года", fontsize=16)
plt.xlabel("Дата", fontsize=14)
plt.ylabel("Значение", fontsize=14)
plt.grid(True)
plt.xticks(rotation=45)
plt.legend(fontsize=12)
plt.savefig("output.png")'''