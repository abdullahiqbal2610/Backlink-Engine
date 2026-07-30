import inspect
from browser_use import Controller
with open("controller_source.txt", "w", encoding="utf-8") as f:
    f.write(inspect.getsource(Controller))
