"""        if self.provacatuer_setting:
            ALL_UNITS.append(Provocateur(self, self.provacatuer_setting[0], self.provacatuer_setting[1], None,
                                         event.x(), event.y()))
            self.provacatuer_setting.clear()
        else:
            if event.button() == Qt.LeftButton:
                ALL_UNITS.append(self.selected_unit(self, event.x(), event.y(), None))
            else:
                self.provacatuer_setting.append(event.x())
                self.provacatuer_setting.append(event.y())"""
"""

class GameTexture(QWidget):
    def __init__(self, parent, img):
        super().__init__(parent)
        self._pixmap = QPixmap(img)
        self.show()

    def paintEvent(self, event) -> None:
        print(self.pos())
        qp = QPainter()
        qp.drawPixmap(self._pixmap.rect(), self._pixmap)

    def width(self):
        return self._pixmap.width()

    def height(self):
        return self._pixmap.height()

    def clear(self):
        self.deleteLater()
"""


"""    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(10, 30, 700, 500)
        self.btn = QtWidgets.QPushButton("Start", self)
        self.btn.move(20, 20)
        self.btn.pressed.connect(self.test)

        a = QtWidgets.QPushButton("Clear", self)
        a.move(120, 20)
        a.pressed.connect(lambda x=0: (ALL_UNITS.clear(), ALL_BULLETS.clear(), gc.collect()))
        self.started = False

        self.__loop = QtCore.QTimer(self)
        self.__loop.timeout.connect(self.mainLoop)
        self.__loop.start(int(DELTA_TIME * 1000))
        print("=>", int(DELTA_TIME * 1000))

        self.provacatuer_setting = []

        self.selected_unit = Shooter

        x = 20
        y = 50
        self.btns = []
        for i in [Shooter, Fighter, Sniper, Assasin, ShieldUnit, Decelerator]:
            self.btns.append(QtWidgets.QPushButton(self))
            self.btns[-1].pressed.connect(self.blabla)
            self.btns[-1].setText(i.__name__)
            self.btns[-1].move(x, y)
            x += 100

    def blabla(self):
        t = self.sender().text()
        if t == 'Fighter':
            self.selected_unit = Fighter
        elif t == 'Shooter':
            self.selected_unit = Shooter
        elif t == 'Sniper':
            self.selected_unit = Sniper
        elif t == 'Assasin':
            self.selected_unit = Assasin
        elif t == 'ShieldUnit':
            self.selected_unit = ShieldUnit
        elif t == 'Decelerator':
            self.selected_unit = Decelerator

    def test(self):
        if not self.started:
            teams = ['blue', 'blue', 'red', 'green', 'greed', 'purple']
            time.sleep(0.02)
            self.started = True
            self.btn.setText('Stop')

        else:

            ALL_UNITS.clear()
            ALL_BULLETS.clear()
            gc.collect()

            self.started = False
            self.btn.setText('Start')

    def mainLoop(self):
        if self.started:
            for i in ALL_BULLETS:
                i.update()

                for g in ALL_UNITS:
                    if i.collides_with(g) and (i.team != g.team or g.team is None) and g != i.owner:
                        i.give_damage(g)
                        ALL_BULLETS.remove(i)
            for i in ALL_UNITS:
                if i.health <= 0:
                    ALL_UNITS.remove(i)
                i.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.provacatuer_setting:
            ALL_UNITS.append(Provocateur(self, self.provacatuer_setting[0], self.provacatuer_setting[1], None,
                                         event.x(), event.y()))
            self.provacatuer_setting.clear()
        else:
            if event.button() == Qt.LeftButton:
                if self.selected_unit.__name__ == 'ShieldUnit':
                    color = (255, 255, 255)
                else:
                    color = (randint(0, 255), randint(0, 255), randint(0, 255))
                ALL_UNITS.append(
                    self.selected_unit(self, event.x(), event.y(), color))
            else:
                self.provacatuer_setting.append(event.x())
                self.provacatuer_setting.append(event.y())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter(self)
        qp.begin(self)
        qp.drawRect(BORDERS['l'], BORDERS['t'], BORDERS['r'] - BORDERS['l'], BORDERS['b'] - BORDERS['t'])

    def closeEvent(self, event):
        self.started = False
        time.sleep(0.06)
        
    ----------------------
            if self.left + x > BORDERS['l'] and self.right + x < BORDERS['r'] and \
                self.top + y > BORDERS['t'] and self.bottom + x < BORDERS['b'] and \
                type(self) != BaseBulletAttack and type(self) != DeceleratorBulletAttack:
            
        elif type(self) == BaseBulletAttack or type(self) == DeceleratorBulletAttack:
            self.x += x
            self.y += y
            self.update_edges()
            if not (self.left + x >= BORDERS['l'] and self.right + x <= BORDERS['r'] and
                    self.top + y >= BORDERS['t'] and self.bottom + x <= BORDERS['b']):
                self.rect.hide()
    """

from sys import stdin
a = [i.strip() for i in stdin.readlines()]
counter = 0
for i in a:
    if i.startswith('#') or i == '':
        continue
    counter += 1
print(counter)
