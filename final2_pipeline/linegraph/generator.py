import os
from generator import Generator 

class LineGraphGenerator(Generator):
    def __init__(self):
        linegraph_prompt_file = os.path.join(os.path.dirname(__file__), 'prompt.txt')
        
        with open(linegraph_prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
  
        super().__init__(system_prompt_python=system_prompt)

