# there are three primitive types:
#   void: psuedotype
#   string
#   number
# var str: string = ask("")
# 
# if str == "a"
#     say_wait("case 1", 2)
# elseif str == "b"
#     say_wait("case 2", 2)
# end
# 
# if str == "c": say_wait("single-line if")

costume "costume.png"
sound "ufo-hit.wav"

func main(): void
    var somevar: number = 3
    var my_var: number = 3 * somevar + 3
    var my_other_var: string = "Hello, world!"
end

on flag: main
