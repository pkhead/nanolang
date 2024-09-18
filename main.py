#!/usr/bin/env python3
# TODO: replace all assert calls with a proper exception throw

import argparse
import nanoproject
import subprocess
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='nanolang',
        description='Nanolang to Goboscript compiler',
    )
    parser.add_argument('projectdir', help="The Nanolang project directory.")
    parser.add_argument('-o', metavar='output', help="The directory to compile the Goboscript project to. Defaults to {projectdir}/.gs")
    parser.add_argument('--sb3', metavar='path', dest='sb3', help="Call goboscript to create an sb3 file at the given path.")

    args = parser.parse_args()
    
    gs_out = os.path.join(args.projectdir, '.gs')
    nanoproject.compile(args.projectdir, gs_out)

    if args.sb3:
        proc = subprocess.run(['goboscript', 'build', '-i', gs_out, '-o', args.sb3])
        if proc.returncode != 0:
            print("errors occured when compiling goboscript project")

    # tokens = TokenQueue(parse_tokens('src.nano'))
    # program = parse_program(tokens)
    # 
    # with open('out/main.gs', 'w') as f:
    #     generate_program(program, f)