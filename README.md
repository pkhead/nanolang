# nanolang
compiles a C-ish language into a goboscript project with cursed spaghettified gobocode that aims to be an affront to God.

written in python, because i'm lazy. very early in development. completion is unlikely since I don't think many people would use this tool anyway.

feature list (barely implemented):
- local variables
- functions with return values
- pointer access
- dynamically allocatable memory
- structs, arrays

## usage
prerequisities:
- [goboscript](https://github.com/aspizu/goboscript)
- python 3

currently, filepaths are hardcoded.
```bash
# compile src.nano to goboscript
python main.py

# compile to sb3
goboscript build -i out
```