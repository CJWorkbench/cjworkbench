This is a prototype to dynamically load Python modules during runtime. For now,
there are five files:

1. `add.py` and `subtract.py` -> the two modules that can be loaded dynamically.
2. `multiply.py` and `divide.py` -> the two modules that error while _trying_ to
   load, because they don't have the _calculate_ function.
3. `validator.py` -> runs through validations before the module is loaded
4. `app.py` -> the flask module that is responsible for checking if modules are
   valid, and if so, load them. If, on the other hand, the module isn't valid,
   the user should see a sensible error message.

To start the application, run the following commands in iTerm/Terminal/the
terminal emulator of your choice:
```
export FLASK_APP=app.py
flask run
```
Once the app starts, you can load two of the modules (add and subtract) by
hitting the endpoints http://127.0.0.1:5000/load/subtract and
http://127.0.0.1:5000/load/add. 

Loading http://127.0.0.1:5000/load/divide, http://127.0.0.1:5000/load/multiply
or any other module will result in an error. 

Once the modules are loaded, you can run some mathematical operations. 
e.g.: http://127.0.0.1:5000/subtract?a=1&b=2 should return -1. 
Similarly, http://127.0.0.1:5000/add?a=1&b=2 should return 3. 

If you attempt to run the above commands (add/subtract) before loading the
modules, you'll get an error.

There are a couple of assumptions here:
1. The class name is the titlecase version of the module name (this won't
   necessarily be the case, but perhaps we can drive this off config?)
2. The classes are manually initialised right now, i.e. Add() and Subtract() are
   explicitly called in app.py. **Do we want to make this more generic?**
