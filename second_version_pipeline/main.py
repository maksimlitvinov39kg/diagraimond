import streamlit as st
import subprocess
import os
from generator import Generator

output_python_file = "generated_graph_code.py"
output_image_file = "graph_output.png"

if "text_input" not in st.session_state:
    st.session_state.text_input = ""

st.title("Генерация диаграммы из текста")

st.header("Генерация и отображение диаграммы")
text_input = st.text_area(
    "Введите описание диаграммы",
    placeholder="Опишите диаграмму здесь...",
    height=300,
    value=st.session_state.text_input
)

if st.button("Сгенерировать и создать диаграмму"):
    if text_input:
        try:
            st.session_state.text_input = text_input

            generator = Generator()
            generator.generate_python_from_text(text_input, output_file=output_python_file)
            st.success(f"Python-код успешно сгенерирован и сохранен в файл: {output_python_file}")

            result = subprocess.run(
                ["python", output_python_file, "--output", output_image_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_image_file):
                st.success("Диаграмма успешно создана!")
                st.image(output_image_file, caption="Сгенерированная диаграмма", use_column_width=True)
            else:
                st.error(f"Ошибка при выполнении Python-кода: {result.stderr}")
        except Exception as e:
            st.error(f"Произошла ошибка: {e}")
    else:
        st.error("Введите описание диаграммы.")
