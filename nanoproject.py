import os
import shutil

from lexer import parse_tokens, TokenQueue
from astgen import parse_program
from gbgen import generate_program

class ProjectCompilationException(Exception):
    pass

def compile(project_dir, output_dir, output_file=None):
    project_dir = os.path.abspath(project_dir)
    output_dir = os.path.abspath(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    nano_files = []
    has_stage = False

    for filename in os.listdir(project_dir):
        abs_path = os.path.join(project_dir, filename)
        if not os.path.isfile(abs_path):
            continue

        extsplit = os.path.splitext(filename)

        if extsplit[1] == '.nano':
            nano_files.append({
                'abspath': abs_path,
                'filename': filename,
                'extsplit': extsplit
            })

            if filename == 'stage.nano':
                has_stage = True
    
    if not has_stage:
        raise ProjectCompilationException("no stage.nano")
    
    for file_info in nano_files:
        tokens = TokenQueue(parse_tokens(file_info['abspath']))
        program = parse_program(tokens, os.path.relpath(project_dir, output_dir))
        
        with open(os.path.join(output_dir, file_info['extsplit'][0] + '.gs'), 'w') as f:
            generate_program(program, f, file_info['filename'] == 'stage.nano')
