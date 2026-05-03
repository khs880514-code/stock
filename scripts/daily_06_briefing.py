from app.config import load_config
from app.main import run_demo


if __name__ == "__main__":
    print(run_demo(load_config()))

