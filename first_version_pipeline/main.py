import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import yaml
from generator import Generator

@st.cache_data
def load_diagram(filepath):
    """
    Загрузка данных из YAML файла.
    """
    try:
        with open(filepath, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        st.error(f"Ошибка загрузки YAML файла: {e}")
        return None

@st.cache_data
def create_graph(data):
    """
    Создание графа из данных YAML.
    """
    if not data:
        return None

    G = nx.DiGraph() 
    for node in data.get('nodes', []):
        G.add_node(node['id'], **node)

    for edge in data.get('edges', []):
        G.add_edge(edge['from'], edge['to'], **edge)

    return G

@st.cache_resource
def get_generator():
    """
    Получение экземпляра генератора.
    """
    return Generator()  

def draw_graph(G):
    """
    Отображение графа с использованием NetworkX и Matplotlib.
    """
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=False, node_size=1000, node_color='lightblue')
    labels = nx.get_node_attributes(G, 'label')
    nx.draw_networkx_labels(G, pos, labels=labels)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    st.pyplot(plt.gcf())
    plt.clf()

st.title("Генератор и Визуализатор Диаграмм")
generator = get_generator() 

st.header("Генерация YAML")
text_input = st.text_area("Введите описание диаграммы", placeholder="Опишите диаграмму...", height=300)
output_file = "generated_diagram.yaml"

if st.button("Сгенерировать и визуализировать YAML"):
    if text_input:
        generator.generate_yaml_from_text(text_input, output_file=output_file)
        st.success(f"YAML успешно сохранен в файл: {output_file}")

        diagram_data = load_diagram(output_file)
        if diagram_data:
            graph = create_graph(diagram_data)
            if graph:
                st.subheader("Результат:")
                draw_graph(graph)
            else:
                st.error("Не удалось создать граф.")
        else:
            st.error("Не удалось загрузить сгенерированный YAML файл.")
    else:
        st.error("Введите описание диаграммы.")
