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

def load_highscore() -> int:
    try:
        return int(HS_PATH.read_text())
    except (FileNotFoundError, ValueError):
        return 0

def save_highscore(val: int):
    HS_PATH.write_text(str(val))

pg.init()

pg.mixer.init()

jump_sfx = pg.mixer.Sound(resource_path('sound/sfx_wing.mp3'))
point_sfx = pg.mixer.Sound(resource_path('sound/sfx_point.mp3'))
crash_sfx = pg.mixer.Sound(resource_path('sound/crash.mp3'))


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
WHITE = (255, 255, 255)

# Game Variables
gr_scroll = 0
scroll_spd = 4
flying = False
game_over = False
gap = 200
frequency = 1500
last_pipe = pg.time.get_ticks() - frequency
score = 0
high_score = load_highscore()
pass_pipe = False
game_over_time = 0
hit_time = 0
fall_sfx_played = False
pipe_queue = deque()  # Initialize

# Load Images
bg = pg.image.load(resource_path('img/bg.png'))
ground = pg.image.load(resource_path('img/ground.png'))
restart_btn = pg.image.load(resource_path('img/restart.png'))

# Draw text with center anchor
def draw_text(text, font, text_color, x, y):
    img = font.render(text, True, text_color)
    rect = img.get_rect(center=(x, y))
    screen.blit(img, rect)

# Reset game
def reset_game():
    pipe_group.empty()
    pipe_queue.clear()
    explosion_group.empty()      
    bird_group.add(flappy)       
    flappy.rect.x = 100
    flappy.rect.y = int(HEIGHT / 2)
    flappy.vel = 0
    flappy.image = flappy.images[0]
    flappy.index = 0
    flappy.counter = 0
    return 0


# Bird class
class Bird(pg.sprite.Sprite):
    def __init__(self, x, y):
        pg.sprite.Sprite.__init__(self)
        self.images = [pg.image.load(resource_path(f'img/bird{n}.png')) for n in range(1, 4)]
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect(center=(x, y))
        self.counter = 0
        self.vel = 0
        self.clicked = False

    def update(self):
        if flying:
            self.vel += 0.5 # Gravity
            self.vel = min(self.vel, 8) # Velocity Limit
            if self.rect.bottom < 768:
                self.rect.y += int(self.vel)

        if not game_over and flying:
            keys = pg.key.get_pressed()
            if (pg.mouse.get_pressed()[0] == 1 or keys[pg.K_SPACE]) and not self.clicked:
                self.clicked = True
                self.vel = -10 # Jump
                jump_sfx.play()
            if pg.mouse.get_pressed()[0] == 0 and not keys[pg.K_SPACE]:
                self.clicked = False

            self.counter += 1
            if self.counter > 5:
                self.counter = 0
                self.index = (self.index + 1) % len(self.images)

            self.image = pg.transform.rotate(self.images[self.index], self.vel * -2) # Rotate bird
        else:
            self.image = pg.transform.rotate(self.images[self.index], -90)

# Pipe class
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

# Button class
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
    
class ExplosionParticle(pg.sprite.Sprite):
    def __init__(self, x, y, image_part):
        super().__init__()
        self.image = image_part
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = [random.uniform(-5, 5), random.uniform(-5, -1)]
        self.gravity = 0.3

    def update(self):
        self.vel[1] += self.gravity
        self.rect.x += int(self.vel[0])
        self.rect.y += int(self.vel[1])
        if self.rect.top > HEIGHT:
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



# Sprite groups
bird_group = pg.sprite.Group()
pipe_group = pg.sprite.Group()
flappy = Bird(100, int(HEIGHT / 2)) # Bird Start Pos
bird_group.add(flappy)

explosion_group = pg.sprite.Group()


button = Button(WIDTH // 2 - 50, HEIGHT // 2, restart_btn)


bg_overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
bg_overlay.fill((0, 0, 0, 100)) 


# Game loop
run = True
while run:
    clock.tick(FPS)
    screen.blit(bg, (0, 0))       
    screen.blit(bg_overlay, (0, 0)) 

    bird_group.draw(screen)
    bird_group.update()
    pipe_group.draw(screen)

    explosion_group.update()
    explosion_group.draw(screen)

    screen.blit(ground, (gr_scroll, 768))

    if not game_over and flying:
        # Pipe generation
        time_now = pg.time.get_ticks()
        if time_now - last_pipe > frequency:
            pipe_height = random.randint(-300, 100)
            top_pipe = Pipe(WIDTH, HEIGHT // 2 + pipe_height, 1)
            btm_pipe = Pipe(WIDTH, HEIGHT // 2 + pipe_height, -1)
            pipe_group.add(top_pipe)
            pipe_group.add(btm_pipe)
            pipe_queue.append((top_pipe, btm_pipe)) # Enqueue
            last_pipe = time_now

        # Scroll
        gr_scroll -= scroll_spd
        if abs(gr_scroll) > 35:
            gr_scroll = 0

        pipe_group.update()

    # Score checking
    if not game_over and flying and len(pipe_queue) > 0:
        next_top, next_btm = pipe_queue[0]
        if flappy.rect.left > next_top.rect.right:
            score += 1
            pass_pipe = False
            point_sfx.play()
            pipe_queue.popleft() # Dequeue

    draw_text(str(score), font, WHITE, WIDTH // 2, 50)

    # Collision Bird and Pipe
    if pg.sprite.groupcollide(bird_group, pipe_group, False, False) or flappy.rect.top < 0:
        if not game_over:
            game_over = True
            crash_sfx.play()

            explosion_parts = create_explosion(flappy.rect.centerx, flappy.rect.centery, flappy.image)
            explosion_group.add(explosion_parts)            
            bird_group.remove(flappy)

            game_over_time = pg.time.get_ticks()
            if score > high_score:
                high_score = score
                save_highscore(high_score)

    # Collision Bird and Ground
    if flappy.rect.bottom >= 768:
        if not game_over:
            game_over = True
            crash_sfx.play()
            explosion_parts = create_explosion(flappy.rect.centerx, flappy.rect.centery, flappy.image)
            explosion_group.add(explosion_parts)            
            bird_group.remove(flappy)
            game_over_time = pg.time.get_ticks()
            if score > high_score:
                high_score = score
                save_highscore(high_score)


    # Game Over UI
    if game_over:
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_text("GAME OVER", font, WHITE, WIDTH // 2, HEIGHT // 2 - 200)
        draw_text(f"SCORE = {score}", font, WHITE, WIDTH // 2, HEIGHT // 2 - 120)
        draw_text(f"HIGH SCORE = {high_score}", font, WHITE, WIDTH // 2, HEIGHT // 2 - 40)

        # Delay restart button
        if pg.time.get_ticks() - game_over_time > 1000:
            if button.draw():
                game_over = False
                score = reset_game()

    # Start screen
    if not flying and not game_over:
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_text("PRESS SPACEBAR TO START", font, WHITE, WIDTH // 2, HEIGHT // 2)

    for event in pg.event.get():
        if event.type == pg.QUIT:
            run = False
        if event.type == pg.KEYDOWN and event.key == pg.K_SPACE: # If Spacebar pressed
            if not flying and not game_over:
                flying = True 
                flappy.vel = -10 # Jump
            elif game_over and pg.time.get_ticks() - game_over_time > 1000: # Adds delay when game over
                game_over = False
                score = reset_game()
        if event.type == pg.MOUSEBUTTONDOWN: # If mouse button clicked
            if not flying and not game_over:
                flying = True
                flappy.vel = -10 # Jump

    pg.display.update()

pg.quit()