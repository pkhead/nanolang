import os
import shutil

from lexer import parse_tokens, TokenQueue
from astgen import parse_program
from gbgen import generate_program

class ProjectCompilationException(Exception):
    pass

def file_ast(abspath, project_dir, output_dir, stage=None):
    tokens = TokenQueue(parse_tokens(abspath))
    return parse_program(tokens, os.path.relpath(project_dir, output_dir), stage)

def emit_ast(ast, sprite_name, output_dir, stage=None):
    with open(os.path.join(output_dir, sprite_name + '.gs'), 'w') as f:
        return generate_program(ast, f, None if stage == None else stage)

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
    

    # first, generate asts
    targets = []
    targets.append({
        'ast': file_ast(os.path.join(project_dir, 'stage.nano'), project_dir, output_dir),
        'name': 'stage'
    })

    for file_info in nano_files:
        if file_info['filename'] == 'stage.nano': continue
        targets.append({
            'ast': file_ast(os.path.join(project_dir, file_info['filename']), project_dir, output_dir, targets[0]['ast']),
            'name': file_info['extsplit'][0]
        })

    # then, emit files
    stage_gen = None
    for target in targets:
        gen = emit_ast(target['ast'], target['name'], output_dir, stage_gen)
        if target['name'] == 'stage':
            stage_gen = gen
