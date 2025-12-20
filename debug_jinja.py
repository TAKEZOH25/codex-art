from jinja2 import Environment, FileSystemLoader
import os

print(f"CWD: {os.getcwd()}")
loader = FileSystemLoader("templates")
env = Environment(loader=loader)
print(f"Searchpath: {loader.searchpath}")
print(f"Templates found: {env.list_templates()}")
try:
    t = env.get_template("pages/index.html")
    print("Success loading pages/index.html")
except Exception as e:
    print(f"Error loading pages/index.html: {e}")
try:
    t = env.get_template("layouts/base.html")
    print("Success loading layouts/base.html")
except Exception as e:
    print(f"Error loading layouts/base.html: {e}")
