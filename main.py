import sys
from src.database import init_db

def main():
    init_db()

    # UI bootstrap will go here in Week 2
    print("SuggestoLearn — база данных инициализирована.")

if __name__ == "__main__":
    main()
