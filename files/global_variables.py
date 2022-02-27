DELTA_TIME = 1 / 60
ALL_BULLETS = []
ALL_UNITS = []
BORDERS = {"t": 50, "b": 550, "l": 50, "r": 550}
UNITS_CHARACTERISTICS = {
    "Shooter": {
        "texture": "files/img/Shooter.png",
        "hp": 20,
        "speed": 2,
        "bullet_attack_radius": 200,
        "bullet_speed": 5,
        "bullet_damage": 5,
        "bullet_texture": "files/img/Bullet.png",
        "reload_time": 1,
        "description": "Shoots at enemies. The first unit."},

    "Fighter": {
        "texture": "files/img/Fighter.png",
        "hp": 25,
        "speed": 2,
        "bullet_attack_radius": 30,
        "bullet_speed": 5,
        "bullet_damage": 1.5,
        "bullet_texture": "files/img/Punch.png",
        "reload_time": 0.2,
        "description": "Beats enemies. Given after passing the first level."},

    "Sniper": {
        "texture": "files/img/Sniper.png",
        "hp": 5,
        "speed": 2,
        "bullet_attack_radius": 800,
        "bullet_speed": 20,
        "bullet_damage": 40,
        "bullet_texture": "files/img/Bullet.png",
        "reload_time": 5,
        "description": "Shoots at enemies from a pretty long distance. Has a very small hit point."},

    "Provocateur": {
        "texture": "files/img/Provocateur.png",
        "hp": 18,
        "speed": 4,
        "description": "Distracts enemy units on itself. Can't attack."},

    "Assasin": {
        "hp": 7,
        "speed": 5,
        "texture": "files/img/Assasin.png",
        "bullet_attack_radius": 35,
        "bullet_speed": 5,
        "bullet_first_damage": 10,
        "bullet_base_damage": 4,
        "bullet_texture": "files/img/Punch.png",
        "reload_time": 0.2,
        "description": "Enters a state of invisibility until it reaches the enemy."
                       "The first hit causes big damage."},

    "Decelerator": {
        "hp": 15,
        "speed": 3,
        "texture": "files/img/Decelerator.png",
        "bullet_attack_radius": 300,
        "bullet_damage": 1,
        "bullet_speed": 5,
        "bullet_texture": "files/img/DeceleratorBullet.png",
        "reload_time": 0.5,
        "description": "Bullets slows down enemies twice. Has the smallest damage."},

    "Shield": {
        "texture": "files/img/ShieldUnitP.png",
        "GameTexture": "files/img/ShieldUnit.png",
        "hp": 30,
        "speed": 3,
        "description": "Has a shield that covers allies. Goes to the ally with the least amount of hp."}
}
