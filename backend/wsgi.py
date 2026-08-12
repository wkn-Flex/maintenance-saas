import sys
import os

# 把backend目录加入Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2wsgi import ASGIMiddleware
from main import app

# PythonAnywhere WSGI入口
application = ASGIMiddleware(app)
