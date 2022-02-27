import sys
import os

from PyQt5.QtWidgets import QApplication
from files.classes import *


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    # if no database
    if not os.path.isfile('files/Saving.sqlite'):
        con = sqlite3.connect('files/Saving.sqlite')
        con.execute("""CREATE TABLE lastSaving ( title STRING, value INTEGER); """)
        con.execute("""CREATE TABLE available_units (name         STRING  PRIMARY KEY,is_available BOOLEAN);""")
        con.execute("""INSERT INTO lastSaving VALUES('currentLvl', 1)""")
        for i in UNITS_CHARACTERISTICS.keys():
            con.execute(f"""INSERT INTO available_units VALUES('{i}', False)""")
        con.execute("""UPDATE available_units SET is_available = True WHERE name = 'Shooter'""")
        con.commit()

    app = QApplication(sys.argv)
    w = MainMenu()
    w.show()

    sys.excepthook = except_hook
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
