import time
import csv
import sqlite3

from files import CreativeModeUi, CompanyModeUi, MainMenuUi, SelectLevelUi, AboutUnitsUi

from files.global_variables import *

from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QInputDialog, QFileDialog, QColorDialog, QLabel, \
    QMessageBox
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer

from threading import Timer


def get_current_level():
    con = sqlite3.connect('files/Saving.sqlite')
    data = con.execute("""SELECT value FROM LastSaving WHERE title = 'currentLvl'""").fetchone()
    con.close()
    return data[0]


def set_current_level(value):
    con = sqlite3.connect('files/Saving.sqlite')
    con.execute(f"""update LastSaving set value = {value} where title = 'currentLvl'""")
    con.commit()
    con.close()


def is_unit_available(unit_name):
    con = sqlite3.connect('files/Saving.sqlite')
    unit_name = 'Shield' if unit_name == 'ShieldUnit' else unit_name
    data = con.execute(f"""SELECT is_available FROM available_units WHERE name = '{unit_name}'""").fetchone()[0]
    con.close()
    return data


def set_availability(unit_name, value):
    con = sqlite3.connect('files/Saving.sqlite')
    con.execute(f"""UPDATE available_units SET is_available = {value}  WHERE name = '{unit_name}'""")
    con.commit()
    con.close()


class GameTexture(QWidget):
    def __init__(self, parent, img, team, draw_team):
        super().__init__(parent)
        self._pixmap = QPixmap(img)
        self._old_rect = self.rect
        self.rect = self._pixmap
        self.resize(self.rect.width(), self.rect.height() + 5)
        self.show()
        self.team = team

        self._draw_team = draw_team
        self._transparency = 1

    def paintEvent(self, event) -> None:
        qp = QPainter(self)
        qp.setOpacity(self._transparency)
        qp.drawPixmap(self.rect.rect(), self._pixmap)
        if self.team and self._draw_team:
            qp.setBrush(QColor(*self.team))
            qp.setOpacity(1)
            qp.drawRect(3, int(self.height() + 2), self.width() - 7, 2)
        qp.end()

    def width(self):
        return self.rect.width()

    def height(self):
        return self.rect.height()

    def setPixmap(self, filename):
        self.rect = QPixmap(filename)

    def setTransparency(self, value):
        self._transparency = value
        self.repaint()

    def clear(self):
        try:
            self.deleteLater()
        except RuntimeError:
            pass


class GameObject:
    def __init__(self, parent, texture, x, y, speed, team_name, team_color):
        self.parent = parent

        draw_team = type(self) not in (BaseBulletAttack, Shield, DeceleratorBulletAttack)
        self.rect = GameTexture(parent, texture, team_color, draw_team)
        self.rect.move(int(x), int(y))
        self.rect.show()

        self.x = x
        self.y = y
        self.center_x = self.x + self.rect.width() / 2
        self.center_y = self.y + self.rect.height() / 2
        self.top = y
        self.bottom = y + self.rect.size().height()
        self.left = x
        self.right = x + self.rect.size().width()

        self.speed = speed
        self.base_speed = speed
        self.team_name = team_name
        self.team_color = team_color

    def __del__(self):
        self.rect.clear()

    def move(self, x, y):
        self.x += x
        self.y += y
        self.update_edges()

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.update_edges()

    def update_edges(self):
        self.rect.move(int(self.x), int(self.y))
        self.center_x = self.x + self.rect.width() / 2
        self.center_y = self.y + self.rect.height() / 2
        self.top = self.y
        self.bottom = self.y + self.rect.size().height()
        self.left = self.x
        self.right = self.x + self.rect.size().width()

    def collides_with(self, other_cube, x=0, y=0):
        if self.right + x >= other_cube.left and self.bottom + y >= other_cube.top and \
                self.left + x <= other_cube.right and self.top + y <= other_cube.bottom:
            return True
        return False


class BaseUnit(GameObject):
    def __init__(self, parent, texture, x, y, team_name, team_color, hp, speed):

        self.health = hp

        super().__init__(parent, texture, x, y, speed, team_name, team_color)

        self._moving_to: tuple = (0, 0)
        self.primary_target_value = 0
        self._vector = (0, 0)
        self.speed = speed
        self._last_effect_time = -999
        self.shield = None

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.__del__()

    def get_slowing_down_effect(self, effect_time):
        if time.time() - self._last_effect_time >= effect_time + 0.1:
            self.speed = self.base_speed * 0.5
            self._last_effect_time = time.time()
            Timer(effect_time, self.remove_slowing_effect).start()

    def remove_slowing_effect(self):
        self.speed = self.base_speed

    # Moves to point(x2, y2) [ Allows the moving_update ]
    def move_to(self, x2, y2):
        k = ((x2 - self.x) ** 2 + (y2 - self.y) ** 2) ** 0.5
        if k:
            self._vector = ((x2 - self.x) / k, (y2 - self.y) / k)
            self._moving_to = (x2, y2)

    def set_primary_target_value(self, value):
        self.primary_target_value = value

    # Updates moving. Works if _moving_to is not Empty, that is, when the function was called 'move_to'
    # Check collision before moving.
    def moving_update(self):
        if sum(self._moving_to) != 0:
            colliding_units = []

            for i in ALL_UNITS:
                if self.collides_with(i, self._vector[0] * self.speed, self._vector[1] * self.speed) and i != self:
                    if type(i) == Shield:  # If shield not our team we add it do colliding units
                        if i.owner.team_name != self.team_name or self.team_name is None:
                            colliding_units.append(i)
                    else:
                        colliding_units.append(i)

            if self.shield:
                for i in filter(lambda x: x.team_name != self.team_name or self.team_name is None, ALL_UNITS):
                    if self.shield.collides_with(i, self._vector[0] * self.speed, self._vector[1] * self.speed):
                        colliding_units.append(i)

            obj = self.shield if self.shield else self

            if not colliding_units:
                self.move(self._vector[0] * self.speed, self._vector[1] * self.speed)
            elif len(colliding_units) == 1:
                y_colliding = min(abs(obj.top - colliding_units[0].bottom),
                                  abs(obj.bottom - colliding_units[0].top))
                x_colliding = min(abs(obj.right - colliding_units[0].left),
                                  abs(obj.left - colliding_units[0].right))
                if x_colliding > y_colliding:
                    self.move(self._vector[0] * self.speed, 0)
                else:
                    self.move(0, self._vector[1] * self.speed)

            if self.left < self._moving_to[0] + self.rect.width() / 2 < self.right and \
                    self.top < self._moving_to[1] + self.rect.height() / 2 < self.bottom:
                self._moving_to = (0, 0)

            k = ((self._moving_to[0] - self.x) ** 2 + (self._moving_to[1] - self.y) ** 2) ** 0.5
            self._vector = ((self._moving_to[0] - self.x) / k, (self._moving_to[1] - self.y) / k)


class BaseBulletAttack(GameObject):
    def __init__(self, parent, texture, owner, enemy, speed, damage, attack_radius):
        self.owner = owner
        if owner.top <= enemy.bottom and owner.bottom >= enemy.top:
            x1 = owner.right if owner.right <= enemy.left else owner.left
            y1 = owner.center_y
        elif owner.left <= enemy.right and owner.right >= enemy.left:
            x1 = owner.center_x
            y1 = owner.top if owner.top >= enemy.bottom else owner.bottom
        else:
            x1 = owner.right if owner.right <= enemy.left else owner.left
            y1 = owner.top if owner.top >= enemy.bottom else owner.bottom

        x1 -= 5
        y1 -= 5
        x2 = enemy.center_x - 5
        y2 = enemy.center_y - 5

        super(BaseBulletAttack, self).__init__(parent, texture, x1, y1, speed, owner.team_name, owner.team_color)

        k = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        self._vector = ((x2 - x1) / k, (y2 - y1) / k)
        self._attack_radius = attack_radius
        self._damage = damage
        self.start_pos = x1, y1

    def __del__(self):
        self.rect.clear()
        if self in ALL_BULLETS:
            ALL_BULLETS.remove(self)

    def update(self):
        self.move(self._vector[0] * self.speed, self._vector[1] * self.speed)
        if ((self.x - self.start_pos[0]) ** 2 + (self.y - self.start_pos[1]) ** 2) ** 0.5 > self._attack_radius:
            self.__del__()

    def give_damage(self, obj):
        obj.take_damage(self._damage)
        self._damage = 0
        self.__del__()


class BaseAttackUnit(BaseUnit):
    def __init__(self, parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                 bullet_damage, bullet_texture, reload_time):
        self.bullet_texture = bullet_texture
        self.bullet_attack_radius = bullet_attack_radius
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.reload_time = reload_time
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed)
        self.last_shot = -999
        self.is_moving = False
        self._assasin_base_damage = 0

    # Finds
    def update(self):
        nearest = None
        for i in ALL_UNITS:
            if i == self or i == nearest or (i.team_name == self.team_name and self.team_name is not None) or \
                    type(i) == Shield:
                continue
            elif nearest is not None:
                if nearest.primary_target_value < i.primary_target_value:
                    nearest = i
                elif nearest.shield and not i.shield and type(i) != Assasin:
                    nearest = i
                elif (((self.x - i.x) ** 2 + (self.y - i.y) ** 2) ** 0.5 <
                      ((self.x - nearest.x) ** 2 + (self.y - nearest.y) ** 2) ** 0.5) and \
                        nearest.primary_target_value == i.primary_target_value:
                    nearest = i
            else:
                nearest = i if i.primary_target_value >= 0 or self._assasin_base_damage else None

        # if no enemy or team_name
        if nearest:
            self.move_to(nearest.x, nearest.y)

            if ((self.center_x - nearest.center_x) ** 2 + (self.center_y - nearest.center_y) ** 2) ** 0.5 \
                    < self.bullet_attack_radius:

                self.is_moving = False

                if time.time() - self.last_shot >= self.reload_time:

                    self.last_shot = time.time()

                    if type(nearest) == Shield:
                        self.shot_to(nearest.owner)

                    else:
                        self.shot_to(nearest)

                    if self._assasin_base_damage:
                        self.bullet_damage = self._assasin_base_damage
            else:
                self.is_moving = True
                self.moving_update()

    def shot_to(self, a: GameObject):
        ALL_BULLETS.append(
            BaseBulletAttack(self.parent, self.bullet_texture, self, a, self.bullet_speed,
                             self.bullet_damage, self.bullet_attack_radius))


class Shooter(BaseAttackUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        texture = UNITS_CHARACTERISTICS["Shooter"]["texture"]
        hp = UNITS_CHARACTERISTICS["Shooter"]["hp"]
        speed = UNITS_CHARACTERISTICS["Shooter"]["speed"]
        bullet_attack_radius = UNITS_CHARACTERISTICS["Shooter"]["bullet_attack_radius"]
        bullet_speed = UNITS_CHARACTERISTICS["Shooter"]["bullet_speed"]
        bullet_damage = UNITS_CHARACTERISTICS["Shooter"]["bullet_damage"]
        bullet_texture = UNITS_CHARACTERISTICS["Shooter"]["bullet_texture"]
        reload_time = UNITS_CHARACTERISTICS["Shooter"]["reload_time"]

        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                         bullet_damage, bullet_texture, reload_time)


class Fighter(BaseAttackUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        texture = UNITS_CHARACTERISTICS["Fighter"]["texture"]
        hp = UNITS_CHARACTERISTICS["Fighter"]["hp"]
        speed = UNITS_CHARACTERISTICS["Fighter"]["speed"]
        bullet_attack_radius = UNITS_CHARACTERISTICS["Fighter"]["bullet_attack_radius"]
        bullet_speed = UNITS_CHARACTERISTICS["Fighter"]["bullet_speed"]
        bullet_damage = UNITS_CHARACTERISTICS["Fighter"]["bullet_damage"]
        bullet_texture = UNITS_CHARACTERISTICS["Fighter"]["bullet_texture"]
        reload_time = UNITS_CHARACTERISTICS["Fighter"]["reload_time"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                         bullet_damage,
                         bullet_texture, reload_time)


class Provocateur(BaseUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        texture = UNITS_CHARACTERISTICS["Provocateur"]["texture"]
        hp = UNITS_CHARACTERISTICS["Provocateur"]["hp"]
        speed = UNITS_CHARACTERISTICS["Provocateur"]["speed"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed)
        self.set_primary_target_value(2)

        self.start_pos = x, y
        self.end_pos = None
        self._direction = 'from start to end'

    def set_end_pos(self, x2, y2):
        self.end_pos = x2, y2
        self.move_to(*self.end_pos)

    def update(self):
        self.moving_update()
        if sum(self._moving_to) == 0 and self.end_pos:
            if self._direction == 'from start to end':
                self.move_to(*self.start_pos)
                self._direction = 'from end to start'
            else:
                self._direction = 'from start to end'
                self.move_to(*self.end_pos)


class Sniper(BaseAttackUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        texture = UNITS_CHARACTERISTICS["Sniper"]["texture"]
        hp = UNITS_CHARACTERISTICS["Sniper"]["hp"]
        speed = UNITS_CHARACTERISTICS["Sniper"]["speed"]
        bullet_attack_radius = UNITS_CHARACTERISTICS["Sniper"]["bullet_attack_radius"]
        bullet_speed = UNITS_CHARACTERISTICS["Sniper"]["bullet_speed"]
        bullet_damage = UNITS_CHARACTERISTICS["Sniper"]["bullet_damage"]
        bullet_texture = UNITS_CHARACTERISTICS["Sniper"]["bullet_texture"]
        reload_time = UNITS_CHARACTERISTICS["Sniper"]["reload_time"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                         bullet_damage,
                         bullet_texture, reload_time)


class Assasin(BaseAttackUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        hp = UNITS_CHARACTERISTICS["Assasin"]["hp"]
        speed = UNITS_CHARACTERISTICS["Assasin"]["speed"]
        texture = UNITS_CHARACTERISTICS["Assasin"]["texture"]
        bullet_attack_radius = UNITS_CHARACTERISTICS["Assasin"]["bullet_attack_radius"]
        bullet_speed = UNITS_CHARACTERISTICS["Assasin"]["bullet_speed"]
        bullet_first_damage = UNITS_CHARACTERISTICS["Assasin"]["bullet_first_damage"]
        bullet_texture = UNITS_CHARACTERISTICS["Assasin"]["bullet_texture"]
        reload_time = UNITS_CHARACTERISTICS["Assasin"]["reload_time"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                         bullet_first_damage, bullet_texture, reload_time)
        self._assasin_base_damage = UNITS_CHARACTERISTICS["Assasin"]["bullet_base_damage"]

    def update(self):
        super().update()
        if self.is_moving:
            self.set_primary_target_value(-1)
            self.rect.setTransparency(0.5)
        else:
            self.set_primary_target_value(0)
            self.rect.setTransparency(1)


class Shield(BaseUnit):
    def __init__(self, parent, owner):
        texture = 'files/img/Shield.png'
        hp = 30
        super(Shield, self).__init__(parent, texture, owner.x, owner.y, owner.team_name, owner.team_color, hp, 0)
        self.set_position((owner.x - (self.rect.width() - owner.rect.width()) / 2),
                          (owner.y - (self.rect.height() - owner.rect.height()) / 2))
        self.owner = owner

    def __del__(self):
        self.owner.shield = None
        self.rect.clear()

    def update(self):
        self.set_position((self.owner.x - (self.rect.width() - self.owner.rect.width()) / 2),
                          (self.owner.y - (self.rect.height() - self.owner.rect.height()) / 2))


class ShieldUnit(BaseUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        texture = UNITS_CHARACTERISTICS["Shield"]["GameTexture"]
        hp = UNITS_CHARACTERISTICS["Shield"]["hp"]
        speed = UNITS_CHARACTERISTICS["Shield"]["speed"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed)
        self.shield = Shield(self.parent, self)
        ALL_UNITS.append(self.shield)

    def update(self):
        nearest = None
        for i in filter(lambda x: x.team_name == self.team_name and self.team_name is not None and x != self,
                        ALL_UNITS):
            if type(i) == Shield:
                continue
            elif nearest:
                if i.health < nearest.health:
                    nearest = i
            else:
                nearest = i

        if nearest:
            self.move_to(nearest.x, nearest.y)

        self.moving_update()


class DeceleratorBulletAttack(BaseBulletAttack):
    def give_damage(self, obj):
        obj.take_damage(self._damage)
        obj.get_slowing_down_effect(2)
        self._damage = 0
        self.__del__()


class Decelerator(BaseAttackUnit):
    def __init__(self, parent, x, y, team_name, team_color):
        hp = UNITS_CHARACTERISTICS["Decelerator"]["hp"]
        speed = UNITS_CHARACTERISTICS["Decelerator"]["speed"]
        texture = UNITS_CHARACTERISTICS["Decelerator"]["texture"]
        bullet_attack_radius = UNITS_CHARACTERISTICS["Decelerator"]["bullet_attack_radius"]
        bullet_damage = UNITS_CHARACTERISTICS["Decelerator"]["bullet_damage"]
        bullet_speed = UNITS_CHARACTERISTICS["Decelerator"]["bullet_speed"]
        bullet_texture = UNITS_CHARACTERISTICS["Decelerator"]["bullet_texture"]
        reload_time = UNITS_CHARACTERISTICS["Decelerator"]["reload_time"]
        super().__init__(parent, texture, x, y, team_name, team_color, hp, speed, bullet_attack_radius, bullet_speed,
                         bullet_damage, bullet_texture, reload_time)

    def shot_to(self, a: GameObject):
        ALL_BULLETS.append(
            DeceleratorBulletAttack(self.parent, self.bullet_texture, self, a, self.bullet_speed,
                                    self.bullet_damage, self.bullet_attack_radius))


class CreativeModeWidget(QWidget, CreativeModeUi.Ui_Form):
    def __init__(self):
        super(CreativeModeWidget, self).__init__()
        self.setupUi(self)

        self.NotificationLabel.setText('')
        self.TipaMap.hide()

        for i in range(self.gridLayout.count()):
            if i == 5:
                continue
            elif i == 8:
                self.gridLayout.itemAt(i).widget().pressed.connect(self.clearUnits)
            else:
                self.gridLayout.itemAt(i).widget().pressed.connect(self.pickUnit)
        self.StartGameButton.pressed.connect(self.startGame)
        self.AddToTeamButton.pressed.connect(self.addToTeam)
        self.AddTeamButton.pressed.connect(self.addTeam)
        self.ClearTeams.pressed.connect(self.clearTeams)
        self.ExportButton.pressed.connect(self.exportGame)
        self.ImportButton.pressed.connect(self.importGame)
        self.GoBackButton.pressed.connect(self.goBack)

        self.current_picked_unit = None
        self.current_unit_team = (None, None)
        self.cpul = None
        self.setMouseTracking(True)
        self.started = False
        self.provocateur_settings = False
        self.provocateur_lines = []
        self.teams = []

        self.__loop = QTimer(self)
        self.__loop.timeout.connect(self.mainLoop)
        self.__loop.start(int(DELTA_TIME * 1000))

        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Team', 'Color'])
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)

    def goBack(self):
        ALL_UNITS.clear()
        ALL_BULLETS.clear()
        self.window = MainMenu()
        self.window.show()
        self.close()
        self.deleteLater()

    def addTeam(self, from_import=None):
        if from_import:
            name = from_import[0]
            color = from_import[1]
            if name not in map(lambda z: z[0], self.teams):
                x = self.tableWidget.rowCount()
                self.tableWidget.setRowCount(x + 1)
                self.tableWidget.setItem(x, 0, QTableWidgetItem(name))
                self.tableWidget.setItem(x, 1, QTableWidgetItem(color))
                self.tableWidget.resizeColumnsToContents()
                self.NotificationLabel.setText('')
                self.teams.append((name, ([int(i) for i in color[1:-1].split(',')])))
            else:
                self.NotificationLabel.setText('Imported team already exists')

        else:
            name = QInputDialog.getText(self, 'Name of team', 'Please, enter the name of team')[0]
            if len(name) > 10:
                self.NotificationLabel.setText('Maximum 10 symbol')
            elif len(name) == 0:
                self.NotificationLabel.setText('Please, enter the name of team')
            elif name not in map(lambda z: z[0], self.teams):
                color = QColorDialog.getColor()
                color1 = f'{color.red()}, {color.green()}, {color.blue()}'
                x = self.tableWidget.rowCount()
                self.tableWidget.setRowCount(x + 1)
                self.tableWidget.setItem(x, 0, QTableWidgetItem(name))
                self.tableWidget.setItem(x, 1, QTableWidgetItem(str(color1)))
                self.tableWidget.resizeColumnsToContents()
                self.NotificationLabel.setText('')
                self.teams.append((name, (color.red(), color.green(), color.blue())))
            else:
                self.NotificationLabel.setText('This team already exists')

    def addToTeam(self):
        if self.teams:
            team, ok_pressed = QInputDialog.getItem(self, "Choosing Team", "Please Choose The Team",
                                                    map(lambda x: x[0], self.teams + [(None, None)]), 1,
                                                    False)
            if ok_pressed and team != '':
                self.current_unit_team = self.teams[list(map(lambda x: x[0], self.teams)).index(team)]
            elif team == '':
                self.current_unit_team = (None, None)
            self.NotificationLabel.setText('')
        else:
            self.NotificationLabel.setText('Add at least one team')

    def clearTeams(self):
        self.teams.clear()
        self.tableWidget.clear()
        self.tableWidget.setHorizontalHeaderLabels(['Team', 'Color'])

    def clearUnits(self):
        for i in ALL_UNITS:
            i.__del__()
        ALL_UNITS.clear()
        for i in ALL_BULLETS:
            i.__del__()
        ALL_BULLETS.clear()
        self.provocateur_lines.clear()
        self.repaint()

    def pickUnit(self):
        text = self.sender().text()
        if text == 'Shooter':
            self.current_picked_unit = Shooter
        elif text == 'Fighter':
            self.current_picked_unit = Fighter
        elif text == 'Sniper':
            self.current_picked_unit = Sniper
        elif text == 'Provocateur':
            self.current_picked_unit = Provocateur
        elif text == 'Assasin':
            self.current_picked_unit = Assasin
        elif text == 'Decelerator':
            self.current_picked_unit = Decelerator
        elif text == 'Shield':
            self.current_picked_unit = ShieldUnit

        _px = QPixmap(UNITS_CHARACTERISTICS[text]["texture"])
        if not self.cpul:
            self.cpul = QLabel(self)
            self.cpul.setMouseTracking(True)
        self.cpul.setPixmap(_px)
        self.cpul.move(50, 50)
        self.cpul.show()
        self.cpul.resize(_px.width(), _px.height())

    def startGame(self):
        if self.started:
            self.started = False
            self.StartGameButton.setText('Start')

        else:
            self.started = True
            self.NotificationLabel.setText('')
            self.StartGameButton.setText('Stop')

        if self.cpul:
            self.cpul.deleteLater()
            self.cpul = None

    def exportGame(self):
        name_of_file, ok_pressed = QInputDialog.getText(self, 'Name Of File', 'Please, write name of file')
        if ok_pressed:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
            if path:
                name_of_file = '/' + name_of_file.replace('.csv', '') + '.csv'
                with open(path + name_of_file, mode='w', newline='') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    for i in self.teams:
                        writer.writerow([*i])
                    writer.writerow(['BELOW UNITS'])
                    for i in ALL_UNITS:
                        name = i.__class__.__name__
                        if name == 'Provocateur':
                            writer.writerow([name, *i.start_pos, *i.end_pos, i.team_name, i.team_color])
                        else:
                            writer.writerow([name, i.x, i.y, i.team_name, i.team_color])

    def importGame(self):
        path = QFileDialog.getOpenFileName(self, 'Pick the exported .csv file', '', 'CSV File (*.csv)')[0]
        if path:

            with open(path, encoding='utf8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                units = False
                for index, i in enumerate(reader):
                    if i[0] == 'BELOW UNITS':
                        units = True
                        continue
                    if units:
                        text = i[0]
                        team = i[3] if text != 'Provocateur' else i[5]
                        team_color = i[4] if text != 'Provocateur' else i[6]
                        team = team if team else None
                        if team_color:
                            team_color = [int(i) for i in team_color[1:-1].split(',')]
                        else:
                            team_color = None
                        if text == 'Shooter':
                            ALL_UNITS.append(Shooter(self, float(i[1]), float(i[2]), team, team_color))
                        elif text == 'Fighter':
                            ALL_UNITS.append(Fighter(self, float(i[1]), float(i[2]), team, team_color))
                        elif text == 'Sniper':
                            ALL_UNITS.append(Sniper(self, float(i[1]), float(i[2]), team, team_color))
                        elif text == 'Provocateur':
                            ALL_UNITS.append(Provocateur(self, float(i[1]), float(i[2]), team, team_color))
                            ALL_UNITS[-1].set_end_pos(float(i[3]), float(i[4]))
                            self.provocateur_lines.append((int(ALL_UNITS[-1].center_x), int(ALL_UNITS[-1].center_y),
                                                           int(float(i[3]) + ALL_UNITS[-1].rect.width() / 2),
                                                           int(float(i[4]) + ALL_UNITS[-1].rect.height() / 2),
                                                           ALL_UNITS[-1].team_color))
                        elif text == 'Assasin':
                            ALL_UNITS.append(Assasin(self, float(i[1]), float(i[2]), team, team_color))
                        elif text == 'Decelerator':
                            ALL_UNITS.append(Decelerator(self, float(i[1]), float(i[2]), team, team_color))
                        elif text == 'Shield':
                            ALL_UNITS.append(ShieldUnit(self, float(i[1]), float(i[2]), team, team_color))
                    else:
                        self.addTeam(from_import=[i[0], i[1]])

    def mainLoop(self):
        if self.started and not self.provocateur_settings:

            alive_teams = []
            for i in ALL_UNITS:
                if i.team_name not in alive_teams:
                    alive_teams.append(i.team_name)

            if len(ALL_UNITS) == 1 or (len(alive_teams) == 1 and alive_teams[0] is not None):
                winner = ALL_UNITS[0].team_name if ALL_UNITS[0].team_name else ALL_UNITS[0].__class__.__name__
                self.NotificationLabel.setText('Winner - ' + winner)
                for i in ALL_BULLETS:
                    i.__del__()
                ALL_BULLETS.clear()
                self.startGame()  # we gonna stop

            deleted_bullets = []
            for i in ALL_BULLETS:
                i.update()
                for g in ALL_UNITS:
                    if i.collides_with(g) and (i.team_name != g.team_name or g.team_name is None) and g != i.owner:
                        i.give_damage(g)

            for i in ALL_UNITS:
                if i.health <= 0:
                    ALL_UNITS.remove(i)
                i.update()
            for i in deleted_bullets:
                ALL_BULLETS.remove(i)

    def disableButtons(self):
        self.StartGameButton.setDisabled(True)
        self.AddTeamButton.setDisabled(True)
        self.ImportButton.setDisabled(True)
        self.ExportButton.setDisabled(True)
        self.ClearTeams.setDisabled(True)
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().setDisabled(True)

    def enableButtons(self):
        self.StartGameButton.setEnabled(True)
        self.AddTeamButton.setEnabled(True)
        self.ImportButton.setEnabled(True)
        self.ExportButton.setEnabled(True)
        self.ClearTeams.setEnabled(True)
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().setEnabled(True)

    def mouseMoveEvent(self, event):
        if self.cpul:
            if BORDERS['l'] < event.x() and event.x() + self.cpul.width() < BORDERS['r'] and \
                    BORDERS['t'] < event.y() and event.y() + self.cpul.height() < BORDERS['b']:
                self.cpul.move(event.x(), event.y())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.provocateur_settings and self.cpul:
            self.cpul.deleteLater()
            self.cpul = None

    def mousePressEvent(self, event):
        if self.cpul and event.button() == Qt.LeftButton:
            can_place = True
            for i in ALL_UNITS:
                if self.cpul.x() <= i.right and self.cpul.x() + self.cpul.width() >= i.left and \
                        self.cpul.y() <= i.bottom and self.cpul.y() + self.cpul.height() >= i.top:
                    can_place = False

            if self.provocateur_settings and can_place:
                ALL_UNITS[-1].set_end_pos(self.cpul.x(), self.cpul.y())
                self.enableButtons()
                self.provocateur_settings = False
                self.provocateur_lines.append((int(ALL_UNITS[-1].center_x), int(ALL_UNITS[-1].center_y),
                                               int(self.cpul.x() + self.cpul.width() / 2),
                                               int(self.cpul.y() + self.cpul.height() / 2), ALL_UNITS[-1].team_color))
                self.repaint()

            elif can_place:
                a = 25 if self.current_picked_unit == ShieldUnit else 0

                ALL_UNITS.append(self.current_picked_unit(self, self.cpul.x() + a, self.cpul.y() + a,
                                                          *self.current_unit_team))
                self.NotificationLabel.setText("")
                if self.current_picked_unit.__name__ == 'Provocateur':
                    self.provocateur_settings = True
                    self.disableButtons()

            else:
                self.NotificationLabel.setText("You can't place there")
        elif self.cpul and event.button() == Qt.RightButton and not self.provocateur_settings:
            self.cpul.deleteLater()
            self.cpul = None

    def paintEvent(self, event) -> None:
        qp = QPainter(self)
        qp.drawRect(BORDERS['l'], BORDERS['t'], BORDERS['r'] - BORDERS['l'],
                    BORDERS['b'] - BORDERS['t'])
        for i in self.provocateur_lines:
            if i[4]:
                qp.setPen(QColor(*i[4]))
            else:
                qp.setPen(QColor(0, 0, 0))
            qp.drawLine(i[0], i[1], i[2], i[3])
        qp.end()


class CompanyModeWidget(QWidget, CompanyModeUi.Ui_Form):
    def __init__(self, number_of_level):
        super(CompanyModeWidget, self).__init__()
        self.setupUi(self)

        self.NotificationLabel.setText('')
        self.TipaMap.hide()
        self.number_of_lvl = number_of_level

        for i in range(self.gridLayout.count()):
            if i == 6:
                self.gridLayout.itemAt(i).widget().pressed.connect(self.clearUnits)
            else:
                self.gridLayout.itemAt(i).widget().pressed.connect(self.pickUnit)
        self.StartGameButton.pressed.connect(self.startGame)
        self.GoBackButton.pressed.connect(self.goBack)

        self.current_picked_unit = None
        self.cpul = None
        self.setMouseTracking(True)
        self.started = False
        self.provocateur_settings = False
        self.provocateur_lines = []
        self.provocateur_lines_enemy = []
        self.units = []
        self.make_available_after_win = []
        self.unit_cost = 999
        self.current_money = -1
        self.default_money = -1
        self.reload_level()

        self.__loop = QTimer(self)
        self.__loop.timeout.connect(self.mainLoop)
        self.__loop.start(int(DELTA_TIME * 1000))

    def goBack(self):
        ALL_UNITS.clear()
        ALL_BULLETS.clear()
        self.window = SelectLevelWidget()
        self.window.show()
        self.close()
        self.deleteLater()

    def reload_level(self):
        self.clearUnits(True)
        with open(f"files/levels/level{self.number_of_lvl}.csv", encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            for index, i in enumerate(reader):
                text = i[0]
                if text == 'Money':
                    self.current_money = int(i[1])
                    self.default_money = int(i[1])
                elif text == 'Reward':
                    self.make_available_after_win.clear()
                    self.make_available_after_win += i[1:]
                elif text == 'Shooter':
                    ALL_UNITS.append(Shooter(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                elif text == 'Fighter':
                    ALL_UNITS.append(Fighter(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                elif text == 'Sniper':
                    ALL_UNITS.append(Sniper(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                elif text == 'Provocateur':
                    ALL_UNITS.append(Provocateur(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                    ALL_UNITS[-1].set_end_pos(float(i[3]), float(i[4]))
                    self.provocateur_lines_enemy.append((int(ALL_UNITS[-1].center_x), int(ALL_UNITS[-1].center_y),
                                                         int(float(i[3]) + ALL_UNITS[-1].rect.width() / 2),
                                                         int(float(i[4]) + ALL_UNITS[-1].rect.height() / 2),
                                                         (255, 0, 0)))
                elif text == 'Assasin':
                    ALL_UNITS.append(Assasin(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                elif text == 'Decelerator':
                    ALL_UNITS.append(Decelerator(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
                elif text == 'Shield':
                    ALL_UNITS.append(ShieldUnit(self, float(i[1]), float(i[2]), "Red", (255, 0, 0)))
            self.label.setText('Money: ' + str(self.default_money))
            self.NotificationLabel.setText('')
            self.repaint()

    def clearUnits(self, after_win=False):
        if after_win:
            for i in ALL_UNITS:
                i.__del__()
            ALL_UNITS.clear()
        else:
            for i in self.units:
                i.__del__()
            self.units.clear()
            for i in ALL_UNITS:
                if i.__class__.__name__ == 'Shield' and i.team_name == 'Blue':
                    i.__del__()
        for i in ALL_BULLETS:
            i.__del__()
        ALL_BULLETS.clear()
        self.provocateur_lines.clear()
        self.current_money = self.default_money
        self.label.setText('Money: ' + str(self.default_money))
        self.repaint()

    def pickUnit(self):
        text, self.unit_cost = self.sender().text().split()
        self.unit_cost = int(self.unit_cost.replace('[', '').replace(']', ''))
        if text == 'Shooter':
            self.current_picked_unit = Shooter
        elif text == 'Fighter':
            self.current_picked_unit = Fighter
        elif text == 'Sniper':
            self.current_picked_unit = Sniper
        elif text == 'Provocateur':
            self.current_picked_unit = Provocateur
        elif text == 'Assasin':
            self.current_picked_unit = Assasin
        elif text == 'Decelerator':
            self.current_picked_unit = Decelerator
        elif text == 'Shield':
            self.current_picked_unit = ShieldUnit

        _px = QPixmap(UNITS_CHARACTERISTICS[text]["texture"])
        if not self.cpul:
            self.cpul = QLabel(self)
            self.cpul.setMouseTracking(True)
        self.cpul.setPixmap(_px)
        self.cpul.move(50, 50)
        self.cpul.show()
        self.cpul.resize(_px.width(), _px.height())

    def startGame(self):
        self.started = True
        self.sender().setText('Stop')
        for i in self.units:
            ALL_UNITS.append(i)
        self.disableButtons()
        self.repaint()
        self.units.clear()

        if self.cpul:
            self.cpul.deleteLater()
            self.cpul = None
        self.NotificationLabel.setText('')

    def mainLoop(self):
        if self.started and not self.provocateur_settings:

            alive_teams = []
            for i in ALL_UNITS:
                if i.team_name not in alive_teams:
                    alive_teams.append(i.team_name)

            if len(alive_teams) == 1:
                winner = alive_teams[0]

                if winner == 'Red':
                    try_again = QMessageBox.question(self, 'You lose!', 'You Lose! Try again?')
                else:
                    for i in self.make_available_after_win:
                        set_availability(i, True)
                    if get_current_level() == self.number_of_lvl:
                        set_current_level(self.number_of_lvl + 1)
                    if self.number_of_lvl < 7:
                        temp = ', '.join(self.make_available_after_win)
                        try_again = QMessageBox.question(self, 'You win!',
                                                         f'You unlocked {temp}!\nTry again this level?')
                    elif self.number_of_lvl == 10:
                        try_again = QMessageBox.question(self, 'You win!', 'Congratulations! You have passed the '
                                                                           'game!\nTry again this level?')
                    else:
                        try_again = QMessageBox.question(self, 'You win!', 'You win!\nTry again this level?')

                if try_again == QMessageBox.Yes:
                    self.enableButtons()
                    self.StartGameButton.setText('Start')
                    self.started = False
                    self.reload_level()

                else:
                    self.goBack()
                self.started = False

            deleted_bullets = []
            for i in ALL_BULLETS:
                i.update()
                for g in ALL_UNITS:
                    if i.collides_with(g) and (i.team_name != g.team_name or g.team_name is None) and g != i.owner:
                        i.give_damage(g)

            for i in ALL_UNITS:
                if i.health <= 0:
                    ALL_UNITS.remove(i)
                i.update()

            for i in deleted_bullets:
                ALL_BULLETS.remove(i)

    def disableButtons(self):
        self.StartGameButton.setDisabled(True)
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().setDisabled(True)

    def enableButtons(self):
        self.StartGameButton.setEnabled(True)
        for i in range(self.gridLayout.count()):
            self.gridLayout.itemAt(i).widget().setEnabled(True)

    def mouseMoveEvent(self, event):
        if self.cpul:
            if self.current_picked_unit.__name__ == 'Provocateur' and self.provocateur_settings and \
                    BORDERS['l'] < event.x() and event.x() + self.cpul.width() < BORDERS['r'] and \
                    BORDERS['t'] < event.y() and event.y() + self.cpul.height() < BORDERS['b']:
                self.cpul.move(event.x(), event.y())
            elif BORDERS['l'] < event.x() and \
                    event.x() + self.cpul.width() < int(BORDERS['l'] + (BORDERS['r'] - BORDERS['l']) / 2) and \
                    BORDERS['t'] < event.y() and event.y() + self.cpul.height() < BORDERS['b']:
                self.cpul.move(event.x(), event.y())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.provocateur_settings and self.cpul:
            self.cpul.deleteLater()
            self.cpul = None

    def mousePressEvent(self, event):
        if self.cpul and event.button() == Qt.LeftButton:
            can_place = True
            for i in self.units:
                if self.cpul.x() <= i.right and self.cpul.x() + self.cpul.width() >= i.left and \
                        self.cpul.y() <= i.bottom and self.cpul.y() + self.cpul.height() >= i.top:
                    can_place = False

            if self.provocateur_settings and can_place:
                self.units[-1].set_end_pos(self.cpul.x(), self.cpul.y())
                self.enableButtons()
                self.provocateur_settings = False
                self.provocateur_lines.append((int(self.units[-1].center_x), int(self.units[-1].center_y),
                                               int(self.cpul.x() + self.cpul.width() / 2),
                                               int(self.cpul.y() + self.cpul.height() / 2), (0, 0, 255)))
                self.repaint()

            elif can_place and self.cpul.x() + self.cpul.width() < BORDERS['l'] + (BORDERS['r'] - BORDERS['l']) / 2:
                if self.current_money - self.unit_cost >= 0 and is_unit_available(self.current_picked_unit.__name__):
                    a = 25 if self.current_picked_unit == ShieldUnit else 0
                    self.current_money -= self.unit_cost
                    self.label.setText('Money: ' + str(self.current_money))
                    self.units.append(self.current_picked_unit(self, self.cpul.x() + a, self.cpul.y() + a,
                                                               'Blue', (0, 0, 255)))
                    self.NotificationLabel.setText("")
                    if self.current_picked_unit.__name__ == 'Provocateur':
                        self.provocateur_settings = True
                        self.disableButtons()
                elif not is_unit_available(self.current_picked_unit.__name__):
                    self.NotificationLabel.setText("You didn't unlocked this unit!")
                else:
                    self.NotificationLabel.setText("You don't have enough money!")

            else:
                self.NotificationLabel.setText("You can't place there")
        elif self.cpul and event.button() == Qt.RightButton and not self.provocateur_settings:
            self.cpul.deleteLater()
            self.cpul = None

    def paintEvent(self, event) -> None:
        qp = QPainter(self)
        qp.drawRect(BORDERS['l'], BORDERS['t'], BORDERS['r'] - BORDERS['l'],
                    BORDERS['b'] - BORDERS['t'])
        if not self.started:
            qp.setPen(QColor(0, 0, 0))
            qp.drawLine(int(BORDERS['l'] + (BORDERS['r'] - BORDERS['l']) / 2),
                        BORDERS['t'],
                        int(BORDERS['l'] + (BORDERS['r'] - BORDERS['l']) / 2),
                        BORDERS['b'])
        for i in self.provocateur_lines:
            if i[4]:
                qp.setPen(QColor(*i[4]))
            else:
                qp.setPen(QColor(0, 0, 0))
            qp.drawLine(i[0], i[1], i[2], i[3])
        for i in self.provocateur_lines_enemy:
            if i[4]:
                qp.setPen(QColor(*i[4]))
            else:
                qp.setPen(QColor(0, 0, 0))
            qp.drawLine(i[0], i[1], i[2], i[3])
        qp.end()


class SelectLevelWidget(QWidget, SelectLevelUi.Ui_Form):
    def __init__(self):
        super(SelectLevelWidget, self).__init__()
        self.setupUi(self)
        for i in range(self.gridLayout.count()):
            if int(self.gridLayout.itemAt(i).widget().text()) > get_current_level():
                self.gridLayout.itemAt(i).widget().setDisabled(True)
            else:
                self.gridLayout.itemAt(i).widget().pressed.connect(self.open_lvl)
        self.GoBackButton.pressed.connect(self.goBack)

    def goBack(self):
        self.window = MainMenu()
        self.window.show()
        self.close()

    def open_lvl(self):
        self.window = CompanyModeWidget(int(self.sender().text()))
        self.window.show()
        self.close()


class AboutUnits(QWidget, AboutUnitsUi.Ui_Form):
    def __init__(self):
        super(AboutUnits, self).__init__()
        self.setupUi(self)
        self.LeftButton.pressed.connect(lambda x=-1: self.changePage(x))
        self.RightButton.pressed.connect(lambda x=1: self.changePage(x))
        self.GoBackButton.pressed.connect(self.goBack)
        self.current = UNITS_CHARACTERISTICS['Shooter']
        self.current_number = 0
        self.nameLine.textEdited.connect(self.showUnitCharacteristic)
        self.unlockedLine.textEdited.connect(self.showUnitCharacteristic)
        self.healthLine.textEdited.connect(self.showUnitCharacteristic)
        self.speedLine.textEdited.connect(self.showUnitCharacteristic)
        self.attackRadiusLine.textEdited.connect(self.showUnitCharacteristic)
        self.bulletSpeedLine.textEdited.connect(self.showUnitCharacteristic)
        self.bulletDamageLine.textEdited.connect(self.showUnitCharacteristic)
        self.reloadTimeLine.textEdited.connect(self.showUnitCharacteristic)
        self.showUnitCharacteristic()

    def goBack(self):
        self.window = MainMenu()
        self.window.show()
        self.close()

    def changePage(self, val):
        self.current_number += val
        self.current_number -= 7 if self.current_number > 6 else 0
        self.current_number += 7 if self.current_number < -6 else 0
        self.current = UNITS_CHARACTERISTICS[list(UNITS_CHARACTERISTICS.keys())[self.current_number]]
        self.showUnitCharacteristic()

    def showUnitCharacteristic(self):
        self.textureLabel.setPixmap(QPixmap(self.current['texture']))
        name = list(UNITS_CHARACTERISTICS.keys())[self.current_number]
        self.nameLine.setText(name)
        self.healthLine.setText(str(self.current['hp']))
        self.speedLine.setText(str(self.current['speed']))
        if "bullet_attack_radius" in self.current.keys():
            self.attackRadiusLine.setText(str(self.current["bullet_attack_radius"]))
            self.bulletSpeedLine.setText(str(self.current["bullet_speed"]))
            if "bullet_damage" in self.current.keys():
                self.bulletDamageLine.setText(str(self.current["bullet_damage"]))
            else:
                self.bulletDamageLine.setText('First shot: ' + str(self.current["bullet_first_damage"]) + '; Default: '
                                              + str(self.current["bullet_base_damage"]))
            self.reloadTimeLine.setText(str(self.current["reload_time"]) + ' sec')
        else:
            self.attackRadiusLine.setText('No Info')
            self.bulletSpeedLine.setText('No Info')
            self.bulletDamageLine.setText('No Info')
            self.reloadTimeLine.setText('No Info')
        self.unlockedLine.setText('Yes' if is_unit_available(name) else 'No')
        self.descriptionLabel.setText('Description:\n' + self.current["description"])


class MainMenu(QWidget, MainMenuUi.Ui_Form):
    def __init__(self):
        super(MainMenu, self).__init__()
        self.setupUi(self)
        self.StartGameButton.pressed.connect(self.start_game)
        self.AllUnitsButton.pressed.connect(self.all_units_info)
        self.QuitButton.pressed.connect(self.quit_game)

    def start_game(self):
        type_of_game, ok_pressed = QInputDialog.getItem(self, 'Game Mode', 'Please, choose game mode:',
                                                        ['Company', 'Creative'], 0, False)
        if ok_pressed and type_of_game == 'Creative':
            self.window = CreativeModeWidget()
            self.window.show()
            self.close()
        elif ok_pressed and type_of_game == 'Company':
            self.window = SelectLevelWidget()
            self.window.show()
            self.close()

    def all_units_info(self):
        self.window = AboutUnits()
        self.window.show()
        self.close()

    def quit_game(self):
        self.close()
