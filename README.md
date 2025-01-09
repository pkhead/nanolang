# nanolang
compiles a C-ish language into a goboscript project with cursed spaghettified gobocode that aims to be an affront to God.
but it works!

written in python, because i'm lazy. very early in development.

feature list:
- local variables
- functions with return values
- pointer access
- malloc and free, like in C

unimplemented:
- structs
- arrays

plans for a nanolang rewrite:
- make the language resemble C more (braces, semicolons, etc), i think this current design is a bit weird maybe
- make generated code be single-threaded, solving issues with maintaining stacks.
- unique sprite/clone api to work around the single-threaded limitation. demonstrative C code:
```
sprite_t *sprite = sprite_create();
sprite->costume_name = "alien.png";
sprite->x = 0;
sprite->y = 0;
update_sprites(); // sends messages to all created sprites (really clones) to update themselves based off the data in their assigned sprite_t*
```

however, the chances that i will actually do this rewrite are slim considering there are like 20 other attempts at doing basically the same thing and I question if people would actually use this tool. basically seems like a waste of time to me. it would be fun though, but I have other projects I want to work on.

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

### language documentation
haven't made comprehensive documentation yet. check out the [code examples](examples). also, all built-in methods are listed in [this neatly organized code file](builtin_methods.py)
