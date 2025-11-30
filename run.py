import sys
import os

# Add the current directory to sys.path to ensure 'app' module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
