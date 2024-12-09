import os
import yaml
import networkx as nx
import matplotlib.pyplot as plt
import subprocess
import streamlit as st
from generator import Generator
import atexit 
from PIL import Image

output_yaml_file = "generated_diagram.yaml"
output_python_file = "generated_graph_code.py"
output_image_file = "graph_output.png"

@st.cache_data
def create_graph(data):
    """Создание графа из данных YAML."""
    if not data:
        return None

    G = nx.DiGraph()
    for node in data.get("nodes", []):
        G.add_node(node["id"], **node)

    for edge in data.get("edges", []):
        G.add_edge(edge["from"], edge["to"], **edge)

    return G

def draw_graph(G):
    """Отображение графа с использованием NetworkX и Matplotlib."""
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=False, node_size=560, node_color="lightblue")
    labels = nx.get_node_attributes(G, "label")
    nx.draw_networkx_labels(G, pos, labels=labels)
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    st.pyplot(plt.gcf())
    plt.clf()

def cleanup_files():
    """Удаление временных файлов после завершения работы приложения."""
    files_to_remove = [output_yaml_file, output_python_file, output_image_file]
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"Удален файл: {file}")

atexit.register(cleanup_files)

st.title("Генератор и Визуализатор Диаграмм")
st.write("Введите описание диаграммы и нажмите одну из кнопок для генерации.")

text_input = st.text_area(
    "Введите описание диаграммы",
    placeholder="Введите текстовое описание...",
    height=150,
)

try:
    generator = Generator(
        system_prompt_yaml="./system_prompt_yaml.txt",
        system_prompt_python="./system_prompt_python.txt",
    )
except Exception as e:
    st.error(f"Ошибка инициализации генератора: {e}")
    generator = None

col1, col2 = st.columns(2)

if col1.button("Генерация через YAML") and generator:
    if not text_input:
        st.error("Введите описание диаграммы.")
    else:
        try:
            generator.generate_yaml_from_text(text_input, output_file=output_yaml_file)
            st.success(f"YAML успешно сгенерирован")

            with open(output_yaml_file, "r") as f:
                diagram_data = yaml.safe_load(f)

            if diagram_data:
                graph = create_graph(diagram_data)
                if graph:
                    st.subheader("Сгенерированная диаграмма (YAML):")
                    draw_graph(graph)
                else:
                    st.error("Не удалось создать граф.")
        except Exception as e:
            st.error(f"Ошибка при генерации YAML: {e}")

if col2.button("Генерация через Python") and generator:
    if not text_input:
        st.error("Введите описание диаграммы.")
    else:
        try:
            generator.generate_python_from_text(text_input, output_file=output_python_file)
            st.success(f"Python-код успешно сгенерирован")

            result = subprocess.run(
                ["python", output_python_file, "--output", output_image_file],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and os.path.exists(output_image_file):
                img = Image.open(output_image_file)
                img_width, img_height = img.size  
                
                aspect_ratio = img_width / img_height
                new_width = 512  
                new_height = int(new_width / aspect_ratio) 

                st.image(output_image_file, caption="Сгенерированная диаграмма (Python)", width=new_width)
            else:
                st.error(f"Ошибка при выполнении Python-кода: {result.stderr}")
        except Exception as e:
            st.error(f"Ошибка при генерации Python-кода: {e}")

