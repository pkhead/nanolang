# nanolang
compiles a C-ish language into a goboscript project with cursed spaghettified gobocode that aims to be an affront to God.
but it works!

written in python, because i'm lazy. very early in development.

feature list (barely implemented):
- local variables
- functions with return values
- pointer access
- malloc and free, like in C

unimplemented:
- optimization: lift variables off from stack if variable isn't ever addressed or if function isn't recursive  
- structs
- arrays

## usage
prerequisities:
- [goboscript](https://github.com/aspizu/goboscript)
- Python 3

```bash
# make sure goboscript is installed
goboscript -V

# create sb3 project from examples/hello_world
nanolang examples/hello_world --sb3 helloworld.sb3

# create goboscript project at location without building sb3
nanolang examples/hello_world -o hello_world
```

> [!NOTE]
> calling nanolang from the source repository actually creates an error.
> substitute `nanolang` with `python .`.