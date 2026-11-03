"""
Root entrypoint redirecting to BAS-RPL/app.py.
Allows launching via either:
    streamlit run app.py
or
    streamlit run BAS-RPL/app.py
"""

import os
import sys

# Add BAS-RPL to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
bas_rpl_dir = os.path.join(root_dir, "BAS-RPL")
if bas_rpl_dir not in sys.path:
    sys.path.insert(0, bas_rpl_dir)

# Execute the primary Streamlit app
import importlib.util

spec = importlib.util.spec_from_file_location("bas_rpl_app", os.path.join(bas_rpl_dir, "app.py"))
bas_rpl_app = importlib.util.module_from_spec(spec)
sys.modules["bas_rpl_app"] = bas_rpl_app
spec.loader.exec_module(bas_rpl_app)
