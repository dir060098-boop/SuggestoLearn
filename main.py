import sys
from PyQt6.QtWidgets import QApplication
from src.database import init_db
from src.ui.main_window import MainWindow


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("SuggestoLearn")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
