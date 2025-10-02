import sys
import argparse
from PySide6.QtWidgets import QApplication
from terminal import MainWindow

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vfs-path", required=True,
        help="Path to the VFS location"
    )
    parser.add_argument(
        "--startup-script", required=True,
        help="Path to startup script"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # отладочный вывод всех параметров при старте
    print("Debug parameters:")
    print(f"vfs_path = {args.vfs_path}")
    print(f"startup_script = {args.startup_script}")

    app = QApplication()
    window = MainWindow(
        vfs_path=args.vfs_path,
        startup_script=args.startup_script
    )
    window.show()
    sys.exit(app.exec())
