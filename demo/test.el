; libraries

.include ~/fs.epp
.include ~/stdio.epp
.include ~/random.epp
.include ~/table.epp
.include ~/array.epp
.include ~/type.epp

; variables

global test = 0
global array = array:array()
global table = table:table()

; random integer between 0 and 99

set test = random:random(0, 99)
stdio:print(test)

; stdio

global echo = stdio:get("name: ")
global msg = "Hello, "

stdio:print(msg, echo)

; types

; str -> interger
set test = type:toint("23")

stdio:print(test)

; str -> float
set test = type:tofloat("34.23")

stdio:print(test)

; interger -> float
set test = type:tofloat("23")

stdio:print(test)

; tables

stdio:print(table)

set table = table:add(table, "e", 3443)

set table = table:add(table, "tert", "ea sports!")

stdio:print(table)

set table = table:remove(table, "e")

stdio:print(table)

global tablei = table:get(table, "tert")

stdio:print(tablei)

; arrays

stdio:print(array)

set array = array:append(array, "hello!")

set array = array:append(array, 23)

set array = array:append(array, 34.234534)

stdio:print(array)

set array = array:remove(array, 1)

stdio:print(array)

global arrayi = array:get(array, 1)

stdio:print(arrayi)

; files

FS:write('hello.text', 'This\nIs\nMultiline!')

stdio:print(FS:read('hello.text'))
