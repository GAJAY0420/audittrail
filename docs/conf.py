import os
import sys
from datetime import datetime
from pathlib import Path

import django
from django.conf import settings as django_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if not django_settings.configured:
    django.setup()

project = "Tiger Audit Trail"
author = "AJAY"
copyright = f"{datetime.now().year}, TigerLab"
release = "1.0"
version = release


# -------------------------------------------------------------------
# Extensions
# -------------------------------------------------------------------

extensions = [
    "myst_parser",  # Markdown support
    "sphinx.ext.autodoc",  # Automatic doc from docstrings
    "sphinx.ext.napoleon",  # Google/Numpy style docstrings
    "sphinx.ext.viewcode",  # View source links
    "sphinx.ext.autosummary",  # Auto function summaries
    "sphinx.ext.intersphinx",  # Cross-link external docs
    "sphinx.ext.todo",  # TODO directive support
    "sphinx.ext.mathjax",  # Math/latex
    "sphinx_autodoc_typehints",  # Type annotations rendered
    "sphinx_copybutton",  # Click-to-copy code blocks
]
autosummary_generate = True
autodoc_mock_imports = ["boto3", "confluent_kafka", "pymongo", "dynamodb"]
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -------------------------------------------------------------------
# Theme
# -------------------------------------------------------------------
html_theme = "furo"  # classic, sphinx_rtd_theme, alabaster, furo
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "light_logo": "None",
    "sidebar_hide_name": False,
    "dark_logo": "None",
    "navigation_with_keys": True,
}

html_title = project + " Developer Documentation"
language = "en"

# -------------------------------------------------------------------
# Markdown via MyST
# -------------------------------------------------------------------
myst_enable_extensions = [
    "deflist",
    "colon_fence",
    "html_admonition",
    "attrs_block",
]

# -------------------------------------------------------------------
# External docs mapping (optional)
# -------------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/stable/", None),
    "celery": ("https://docs.celeryq.dev/en/stable/", None),
    "boto3": (
        "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html",
        None,
    ),
    "confluent_kafka": (
        "https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html",
        None,
    ),
    "pymongo": ("https://pymongo.readthedocs.io/en/stable/", None),
}

# -------------------------------------------------------------------
# Misc
# -------------------------------------------------------------------
todo_include_todos = True
