try:
    from cyber_qin import main
    from cyber_qin.gui.views import library_view

    _ = (main, library_view)
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
    exit(1)
except SyntaxError as e:
    print(f"Syntax error: {e}")
    exit(1)
