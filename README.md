# About
The point of this programming language is simple: make *every* function (Even printing text!) from a library.  
The interpreter only provides basic things: variables, strings, and math. That's it!  
To do anything besides adding numbers and strings, you need to **include** libraries, using `.include ~/[library-name].epp`.  

# Writing your first program
To write a simple `Hello, world!` program, we need the `stdio` library.  
```
.include ~/stdio.epp
```
This library provides us with two functions, `stdio:get()` and `stdio:print()`.  
`stdio:print` is the function we need. This functon accepts a string to print, in our case `"Hello, world!"`.  
```
.include ~/stdio.epp
stdio:print("Hello, world!")
```
And with that, you made your first program!
