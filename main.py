import pygame as pg
import random
from collections import deque
import pathlib, json, sys, os

def resource_path(rel_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, rel_path)

APP_DIR  = pathlib.Path(os.getenv("APPDATA", pathlib.Path.home())) / "FlappyBird"
APP_DIR.mkdir(exist_ok=True)

HS_PATH  = APP_DIR / "highscore.txt"
ACHIEVEMENTS_PATH = APP_DIR / "achievements.json"

def load_highscore() -> int:
    try:
        return int(HS_PATH.read_text())
    except (FileNotFoundError, ValueError):
        return 0

def save_highscore(val: int):
    HS_PATH.write_text(str(val))

def load_achievements(master_list: list) -> list:
    try:
        with open(ACHIEVEMENTS_PATH, 'r') as f:
            saved_achievements = json.load(f)
        saved_status = {ach["name"]: ach["unlocked"] for ach in saved_achievements}
        for achievement in master_list:
            if achievement["name"] in saved_status:
                achievement["unlocked"] = saved_status[achievement["name"]]
        return master_list
    except (FileNotFoundError, json.JSONDecodeError):
        return master_list

def save_achievements(achievements_to_save: list):
    with open(ACHIEVEMENTS_PATH, 'w') as f:
        json.dump(achievements_to_save, f, indent=4)

pg.init()
pg.mixer.init()

jump_sfx = pg.mixer.Sound(resource_path('sound/sfx_wing.mp3'))
point_sfx = pg.mixer.Sound(resource_path('sound/sfx_point.mp3'))
crash_sfx = pg.mixer.Sound(resource_path('sound/crash.mp3'))
powerup_sfx = pg.mixer.Sound(resource_path('sound/sfx_pop.mp3'))


clock = pg.time.Clock()
FPS = 60
WIDTH = 864
HEIGHT = 936

screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption('Flappy Bird')
icon = pg.image.load(resource_path('img/bird2.png'))
pg.display.set_icon(icon)

# Define font and color
font = pg.font.SysFont('Bauhaus 93', 60)
achievement_font = pg.font.SysFont('Bauhaus 93', 35)
desc_font = pg.font.SysFont('Arial', 20)
button_font = pg.font.SysFont('Bauhaus 93', 30)
patch_notes_font_title = pg.font.SysFont('Bauhaus 93', 50)
patch_notes_font_body = pg.font.SysFont('Arial', 24)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)
GOLD = (255, 215, 0)

# Game state and variables
game_state = "start_menu"
patch_notes_shown_this_session = False
gr_scroll = 0
scroll_spd = 4
gap = 200
frequency = 1500
last_pipe = pg.time.get_ticks() - frequency
score = 0
high_score = load_highscore()
pipe_queue = deque()
game_over_time = 0
bird_tier = 0

# Gameplay variables for achievements
flap_count = 0
time_of_last_flap = 0

# Achievement Variable Lists
master_achievements_list = [
    {"type": "score", "req": 10, "name": "Bronze Flapper", "description": "Reach a score of 10.", "unlocked": False},
    {"type": "score", "req": 25, "name": "Silver Flapper", "description": "Reach a score of 25.", "unlocked": False},
    {"type": "score", "req": 50, "name": "Golden God", "description": "Reach a score of 50.", "unlocked": False},
    {"type": "event", "id": "icarus", "name": "Icarus", "description": "Fly too close to the sun (the ceiling).", "unlocked": False},
    {"type": "event", "id": "grounded", "name": "Groundbreaking Discovery", "description": "End your run by hitting the ground.", "unlocked": False},
    {"type": "event", "id": "close_shave", "name": "Close Shave", "description": "Pass through a pipe gap very close to a pipe.", "unlocked": False},
    {"type": "event", "id": "zen_flapper", "name": "Zen Flapper", "description": "Score 3 with 10 flaps or less.", "unlocked": False},
    {"type": "event", "id": "nyepi", "name": "Nyepi Silence", "description": "Survive for 1 second without flapping.", "unlocked": False}
]
achievements = load_achievements(master_achievements_list)
achievement_text = ""
achievement_display_timer = 0

# Load Images
bg = pg.image.load(resource_path('img/bg.png'))
ground = pg.image.load(resource_path('img/ground.png'))
restart_btn_img = pg.image.load(resource_path('img/restart.png'))

def draw_text(text, font, text_color, x, y, center=True):
    img = font.render(text, True, text_color)
    if center:
        rect = img.get_rect(center=(x, y))
    else:
        rect = img.get_rect(midleft=(x, y))
    screen.blit(img, rect)

def draw_wrapped_text(surface, text, font, color, rect):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < rect.width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    y = rect.top
    for line in lines:
        img = font.render(line, True, color)
        surface.blit(img, (rect.left, y))
        y += font.get_linesize()
    return y

def draw_achievement_notification(text, font, text_color, x, y):
    img = font.render(text, True, text_color)
    rect = img.get_rect(center=(x, y))
    bg_surface = pg.Surface(rect.inflate(20, 20).size, pg.SRCALPHA)
    pg.draw.rect(bg_surface, (0, 0, 0, 150), bg_surface.get_rect(), border_radius=10)
    screen.blit(bg_surface, rect.inflate(20, 20).topleft)
    screen.blit(img, rect)

def check_achievements(current_score):
    for ach in achievements:
        if ach.get("type") == "score" and not ach["unlocked"] and current_score >= ach["req"]:
            unlock_achievement(ach)
    # Zen Flapper
    if current_score == 3 and flap_count <= 10:
        unlock_event_achievement("zen_flapper")

def unlock_event_achievement(event_id):
    for ach in achievements:
        if ach.get("type") == "event" and ach.get("id") == event_id and not ach["unlocked"]:
            unlock_achievement(ach)
            break

def unlock_achievement(achievement_to_unlock):
    global achievement_text, achievement_display_timer
    achievement_to_unlock["unlocked"] = True
    achievement_text = f"UNLOCKED: {achievement_to_unlock['name']}"
    achievement_display_timer = pg.time.get_ticks()
    save_achievements(achievements)

def reset_game():
    global score, last_pipe, flap_count, time_of_last_flap, bird_tier
    pipe_group.empty()
    pipe_queue.clear()
    explosion_group.empty()
    effect_group.empty()
    bird_group.add(flappy)       
    flappy.rect.x = 100
    flappy.rect.y = int(HEIGHT / 2)
    flappy.vel = 0
    flappy.change_skin('default')
    flappy.index = 0
    flappy.counter = 0
    score = 0
    flap_count = 0
    time_of_last_flap = pg.time.get_ticks()
    last_pipe = pg.time.get_ticks() - frequency
    bird_tier = 0

class Bird(pg.sprite.Sprite):
    def __init__(self, x, y):
        pg.sprite.Sprite.__init__(self)
        self.skins = {
            "default": [pg.image.load(resource_path(f'img/bird{n}.png')) for n in range(1, 4)],
            "red": [pg.image.load(resource_path(f'img/bird_red{n}.png')) for n in range(1, 4)],
            "blue": [pg.image.load(resource_path(f'img/bird_blue{n}.png')) for n in range(1, 4)],
            "asli": [pg.image.load(resource_path(f'img/bird_asli{n}.png')) for n in range(1, 4)]
        }
        self.images = self.skins["default"]
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect(center=(x, y))
        self.counter = 0
        self.vel = 0
        self.clicked = False

    def update(self):
        global flap_count, time_of_last_flap
        if game_state == "playing":
            self.vel += 0.5
            self.vel = min(self.vel, 8)
            if self.rect.bottom < 768:
                self.rect.y += int(self.vel)
            keys = pg.key.get_pressed()
            if (pg.mouse.get_pressed()[0] == 1 or keys[pg.K_SPACE]) and not self.clicked:
                self.clicked = True
                self.vel = -10
                jump_sfx.play()
                flap_count += 1
                time_of_last_flap = pg.time.get_ticks()
            if pg.mouse.get_pressed()[0] == 0 and not keys[pg.K_SPACE]:
                self.clicked = False
            self.counter += 1
            if self.counter > 5:
                self.counter = 0
                self.index = (self.index + 1) % len(self.images)
            self.image = pg.transform.rotate(self.images[self.index], self.vel * -2)
        elif game_state == "game_over":
            self.image = pg.transform.rotate(self.images[self.index], -90)
    
    def change_skin(self, skin_name):
        if skin_name in self.skins:
            self.images = self.skins[skin_name]

class Pipe(pg.sprite.Sprite):
    def __init__(self, x, y, position):
        pg.sprite.Sprite.__init__(self)
        self.image = pg.image.load(resource_path('img/pipe.png'))
        self.rect = self.image.get_rect()
        if position == 1:
            self.image = pg.transform.flip(self.image, False, True)
            self.rect.bottomleft = [x, y - gap // 2]
        if position == -1:
            self.rect.topleft = [x, y + gap // 2]
    def update(self):
        self.rect.x -= scroll_spd
        if self.rect.right < 0:
            self.kill()

class Button():
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
    def draw(self):
        action = False
        pos = pg.mouse.get_pos()
        if self.rect.collidepoint(pos) and pg.mouse.get_pressed()[0] == 1:
            action = True
        screen.blit(self.image, (self.rect.x, self.rect.y))
        return action

class TextButton():
    def __init__(self, text, x, y, width, height, font, bg_color=(0,0,0,100), hover_color=(255,255,255,50)):
        self.text = text
        self.rect = pg.Rect(x, y, width, height)
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.clicked = False
    def draw(self):
        action = False
        pos = pg.mouse.get_pos()
        bg_surface = pg.Surface((self.rect.width, self.rect.height), pg.SRCALPHA)
        if self.rect.collidepoint(pos):
            pg.draw.rect(bg_surface, self.hover_color, bg_surface.get_rect(), border_radius=10)
            if pg.mouse.get_pressed()[0] == 1 and not self.clicked:
                self.clicked = True
                action = True
        else:
            pg.draw.rect(bg_surface, self.bg_color, bg_surface.get_rect(), border_radius=10)
        if pg.mouse.get_pressed()[0] == 0:
            self.clicked = False
        screen.blit(bg_surface, self.rect.topleft)
        draw_text(self.text, self.font, WHITE, self.rect.centerx, self.rect.centery)
        return action

class ExplosionParticle(pg.sprite.Sprite):
    def __init__(self, x, y, image_part):
        super().__init__()
        self.image = image_part
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = [random.uniform(-5, 5), random.uniform(-5, -1)]
        self.gravity = 0.3
    def update(self):
        if game_state == "playing" or game_state == "game_over":
            self.vel[1] += self.gravity
            self.rect.x += int(self.vel[0])
            self.rect.y += int(self.vel[1])
            if self.rect.top > HEIGHT:
                self.kill()

class PowerUpParticle(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = random.randint(5, 12)
        self.image = pg.Surface((size, size), pg.SRCALPHA)
        color = (random.randint(220, 255), random.randint(100, 220), random.randint(0, 50))
        pg.draw.circle(self.image, color, self.image.get_rect().center, self.image.get_width() // 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = [random.uniform(-6, 6), random.uniform(-6, 6)]
        self.gravity = 0.1
        self.alpha = 255
        self.alpha_decay = random.randint(8, 12)
    def update(self):
        self.vel[1] += self.gravity
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.alpha -= self.alpha_decay
        if self.alpha > 0:
            self.image.set_alpha(self.alpha)
        else:
            self.kill()

def create_explosion(x, y, image):
    particles = []
    width, height = image.get_size()
    tile_size = 16
    for i in range(0, width, tile_size):
        for j in range(0, height, tile_size):
            w = min(tile_size, width - i)
            h = min(tile_size, height - j)
            part = image.subsurface(pg.Rect(i, j, w, h))
            particles.append(ExplosionParticle(x + i - width // 2, y + j - height // 2, part))
    return particles

def create_powerup_effect(x, y):
    for _ in range(35):
        effect_group.add(PowerUpParticle(x, y))

# Sprite groups
bird_group = pg.sprite.Group()
pipe_group = pg.sprite.Group()
flappy = Bird(100, int(HEIGHT / 2))
bird_group.add(flappy)
explosion_group = pg.sprite.Group()
effect_group = pg.sprite.Group()

# Button instances
restart_button = Button(WIDTH // 2 - 50, HEIGHT // 2, restart_btn_img)
achievements_button = TextButton("ACHIEVEMENTS", WIDTH // 2 - 150, HEIGHT // 2 + 100, 300, 50, button_font)
back_button = TextButton("BACK", WIDTH // 2 - 150, HEIGHT - 150, 300, 50, button_font)
continue_button = TextButton("CONTINUE", WIDTH // 2 - 150, HEIGHT // 2 + 200, 300, 50, button_font)

# Content for the patch notes
patch_notes_content = [
    {"type": "header", "text": "Welcome! Here's what's new:"},
    {"type": "bullet", "text": "A full Achievement System to track your progress and hunt for secrets."},
    {"type": "bullet", "text": "Your high scores and unlocked achievements are now saved permanently."},
    {"type": "bullet", "text": "Evolve your bird with new colors as you reach higher scores!"}
]

run = True
while run:
    clock.tick(FPS)
    screen.blit(bg, (0, 0))

    bg_overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    bg_overlay.fill((0, 0, 0, 75))
    screen.blit(bg_overlay, (0,0))

    bird_group.draw(screen)
    pipe_group.draw(screen)
    explosion_group.draw(screen)
    effect_group.draw(screen)
    explosion_group.update()
    effect_group.update()
    screen.blit(ground, (gr_scroll, 768))

    if not patch_notes_shown_this_session:
        game_state = "patch_notes"

    if game_state == "playing":
        bird_group.update()
        pipe_group.update()
        
        time_now = pg.time.get_ticks()
        if time_now - last_pipe > frequency:
            pipe_height = random.randint(-300, 100)
            top_pipe = Pipe(WIDTH, HEIGHT // 2 + pipe_height, 1)
            btm_pipe = Pipe(WIDTH, HEIGHT // 2 + pipe_height, -1)
            pipe_group.add(top_pipe, btm_pipe)
            pipe_queue.append((top_pipe, btm_pipe))
            last_pipe = time_now

        gr_scroll -= scroll_spd
        if abs(gr_scroll) > 35:
            gr_scroll = 0
            
        if len(pipe_queue) > 0:
            next_top, next_btm = pipe_queue[0]
            if flappy.rect.left > next_top.rect.right:
                if abs(flappy.rect.top - next_top.rect.bottom) < 10 or abs(flappy.rect.bottom - next_btm.rect.top) < 10:
                    unlock_event_achievement("close_shave")
                score += 1
                check_achievements(score)
                point_sfx.play()
                pipe_queue.popleft()

                if bird_tier == 0 and score >= 10:
                    create_powerup_effect(flappy.rect.centerx, flappy.rect.centery)
                    powerup_sfx.play()
                    flappy.change_skin("red")
                    bird_tier = 1
                elif bird_tier == 1 and score >= 25:
                    create_powerup_effect(flappy.rect.centerx, flappy.rect.centery)
                    powerup_sfx.play()
                    flappy.change_skin("blue")
                    bird_tier = 2
                elif bird_tier == 2 and score >= 50:
                    create_powerup_effect(flappy.rect.centerx, flappy.rect.centery)
                    powerup_sfx.play()
                    flappy.change_skin("asli")
                    bird_tier = 3

        # Nyepi
        if pg.time.get_ticks() - time_of_last_flap > 1500:
            unlock_event_achievement("nyepi")

        if pg.sprite.groupcollide(bird_group, pipe_group, False, False) or flappy.rect.top < 0:
            if flappy.rect.top < 0:
                unlock_event_achievement("icarus")
            game_state = "game_over"
            crash_sfx.play()
            explosion_parts = create_explosion(flappy.rect.centerx, flappy.rect.centery, flappy.image)
            explosion_group.add(explosion_parts)
            bird_group.remove(flappy)
            game_over_time = pg.time.get_ticks()
            if score > high_score:
                high_score = score
                save_highscore(high_score)

        if flappy.rect.bottom >= 768:
            unlock_event_achievement("grounded")
            game_state = "game_over"
            crash_sfx.play()
            explosion_parts = create_explosion(flappy.rect.centerx, flappy.rect.centery, flappy.image)
            explosion_group.add(explosion_parts)
            bird_group.remove(flappy)
            game_over_time = pg.time.get_ticks()
            if score > high_score:
                high_score = score
                save_highscore(high_score)

    elif game_state == "start_menu":
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_text("PRESS SPACEBAR TO START", font, WHITE, WIDTH // 2, HEIGHT // 2)
        if achievements_button.draw():
            game_state = "achievements_menu"

    elif game_state == "achievements_menu":
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        draw_text("My Achievements", font, WHITE, WIDTH // 2, 80)
        
        y_pos = 180
        for achievement in achievements:
            name_color = WHITE if achievement["unlocked"] else GREY
            desc_color = (200, 200, 200) if achievement["unlocked"] else GREY
            icon = "★" if achievement["unlocked"] else "☆"
            icon_color = GOLD if achievement["unlocked"] else GREY
            draw_text(icon, achievement_font, icon_color, WIDTH // 2 - 250, y_pos, center=True)
            draw_text(achievement["name"], achievement_font, name_color, WIDTH // 2 - 220, y_pos, center=False)
            draw_text(achievement["description"], desc_font, desc_color, WIDTH // 2 - 220, y_pos + 30, center=False)
            y_pos += 80
            
        if back_button.draw():
            game_state = "start_menu"

    elif game_state == "patch_notes":
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        panel_rect = pg.Rect(0, 0, 700, 550)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2)
        pg.draw.rect(screen, (10, 10, 30), panel_rect, border_radius=15)
        pg.draw.rect(screen, WHITE, panel_rect, width=2, border_radius=15)
        
        draw_text("Patch Note 1.1", patch_notes_font_title, WHITE, WIDTH // 2, panel_rect.top + 60)
        
        y_pos = panel_rect.top + 140
        for item in patch_notes_content:
            if item["type"] == "header":
                draw_text(item["text"], button_font, WHITE, WIDTH // 2, y_pos)
                y_pos += 60
            elif item["type"] == "bullet":
                text_rect = pg.Rect(panel_rect.left + 50, y_pos, panel_rect.width - 100, 200)
                draw_text("•", patch_notes_font_body, WHITE, text_rect.left - 20, text_rect.top, center=False)
                y_pos = draw_wrapped_text(screen, item["text"], patch_notes_font_body, WHITE, text_rect)
                y_pos += 15

        continue_button.rect.centerx = WIDTH // 2
        continue_button.rect.bottom = panel_rect.bottom - 40
        if continue_button.draw():
            patch_notes_shown_this_session = True
            game_state = "start_menu"

    elif game_state == "game_over":
        bird_group.update()
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_text("GAME OVER", font, WHITE, WIDTH // 2, HEIGHT // 2 - 200)
        draw_text(f"SCORE = {score}", font, WHITE, WIDTH // 2, HEIGHT // 2 - 120)
        draw_text(f"HIGH SCORE = {high_score}", font, WHITE, WIDTH // 2, HEIGHT // 2 - 40)
        if pg.time.get_ticks() - game_over_time > 1000:
            if restart_button.draw():
                reset_game()
                game_state = "start_menu"

    if game_state == "playing":
        draw_text(str(score), font, WHITE, WIDTH // 2, 50)
        if achievement_text and pg.time.get_ticks() - achievement_display_timer < 3000:
            draw_achievement_notification(achievement_text, button_font, WHITE, WIDTH // 2, 120)
        else:
            achievement_text = ""

    for event in pg.event.get():
        if event.type == pg.QUIT:
            run = False
        if game_state != "patch_notes":
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if game_state == "start_menu":
                    reset_game()
                    game_state = "playing"
                elif game_state == "game_over" and pg.time.get_ticks() - game_over_time > 1000:
                    reset_game()
                    game_state = "start_menu"
            if event.type == pg.MOUSEBUTTONDOWN:
                if game_state == "start_menu" and not achievements_button.rect.collidepoint(event.pos):
                    reset_game()
                    game_state = "playing"

    pg.display.update()

pg.quit()
