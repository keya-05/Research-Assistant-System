import langchain_tavily
import pkgutil

print(f"Package: {langchain_tavily.__name__}")
print(f"Members: {dir(langchain_tavily)}")

if hasattr(langchain_tavily, "__path__"):
    for loader, module_name, is_pkg in pkgutil.walk_packages(langchain_tavily.__path__, langchain_tavily.__name__ + "."):
        print(f"Submodule: {module_name}")
        try:
            mod = __import__(module_name, fromlist=["*"])
            print(f"  Members of {module_name}: {dir(mod)}")
        except Exception as e:
            print(f"  Could not import {module_name}: {e}")
