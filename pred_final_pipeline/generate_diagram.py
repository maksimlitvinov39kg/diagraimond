import os
import subprocess
from typing import Tuple, Optional

from process.generator import ProcessGenerator
from piechart.generator import PieChartGenerator
from barchart.generator import BarChartGenerator
from linegraph.generator import LineGraphGenerator

def load_generator(generator_type):
    if generator_type == "Process":
        return ProcessGenerator()
    elif generator_type == "PieChart":
        return PieChartGenerator()
    elif generator_type == "BarChart":
        return BarChartGenerator()
    elif generator_type == "LineGraph":
        return LineGraphGenerator()
    else:
        return None

def generate_diagram(generator_type, description, filename) -> Tuple[bool, Optional[str], Optional[str], Optional[list]]:
    generator = load_generator(generator_type)
    if generator and description:
        output_python_file = f"{generator_type.lower()}_code.py"
        output_image_file = f"output.png"
        temporary_files = []
        temporary_files.append(output_python_file)
        temporary_files.append(output_image_file)
        generator.generate_python_from_text(description, output_file=output_python_file)

        result = subprocess.run(
            ["python", output_python_file],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and os.path.exists(output_image_file):
            return (True, output_image_file, None, temporary_files)
    return (False, None, result.stderr, temporary_files)
