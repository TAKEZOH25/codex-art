import sys
import traceback

try:
    import importlib
    import generate
    importlib.reload(generate)  # Force reload
    generate.main()
except Exception as e:
    with open("error_full.txt", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    print(traceback.format_exc())
