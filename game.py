import random

import pygame

WIDTH, HEIGHT = 480, 640
FPS = 60
BG = (20, 20, 40)
GRAVITY, JUMP_SPEED, MOVE_SPEED = 0.5, -13, 4
PLAYER_W, PLAYER_H = 36, 36
PLATFORM_H = 14
COIN_R = 7
LIVES_START = 3

# ---------------------------------------------------------------------------
# Task 4 state: sparkle particles + combo counter (module level because
# on_coin_collected() only receives (coin, score), not the Game object).
# ---------------------------------------------------------------------------
particles = []   # each: [x, y, vx, vy, life]  (x, y in world coordinates)
combo = 0        # coins collected in a row without losing a life


def platform_color(index, total):
    """Task 2: gradient from green (ground) to violet (top)."""
    t = index / total if total else 0
    t = max(0.0, min(1.0, t))
    start, end = (100, 180, 100), (170, 90, 220)
    return tuple(int(s + (e - s) * t) for s, e in zip(start, end))


def moving_platform_speed(index, total):
    """Task 3: every third platform moves; higher ones move faster.

    Speeds are whole pixels/frame because Rect.x is an integer
    (fractional speeds would be truncated and behave unevenly).
    """
    if index % 3 != 0:
        return None
    if index < total / 3:
        return 1
    if index < 2 * total / 3:
        return 2
    return 3


def on_coin_collected(coin, score):
    """Task 4: spawn a sparkle burst at the coin and bump the combo counter."""
    global combo
    combo += 1
    for _ in range(14):
        angle = random.uniform(0, 6.2832)
        speed = random.uniform(1.0, 3.5)
        vec = pygame.Vector2(speed, 0).rotate_rad(angle)
        particles.append([coin.pos.x, coin.pos.y, vec.x, vec.y, random.randint(20, 35)])


def reset_combo():
    global combo
    combo = 0


def reset_effects():
    particles.clear()
    reset_combo()


def update_effects():
    for p in particles:
        p[0] += p[2]
        p[1] += p[3]
        p[3] += 0.08      # slight gravity
        p[4] -= 1
    particles[:] = [p for p in particles if p[4] > 0]


def draw_effects(screen, cam_y):
    for x, y, _vx, _vy, life in particles:
        shade = min(255, 80 + life * 6)
        radius = 1 + life // 12
        pygame.draw.circle(screen, (255, shade, 80), (int(x), int(y - cam_y)), radius)


class Platform:
    def __init__(self, index, total, x, y, w=120, movable=True):
        self.rect = pygame.Rect(x, y, w, PLATFORM_H)
        self.speed = (moving_platform_speed(index, total) or 0) if movable else 0
        self.bounds = (max(0, x - 60), min(WIDTH - w, x + 60))
        self.color = platform_color(index, total) or (100, 180, 100)

    def update(self):
        if not self.speed:
            return 0
        dx = self.speed
        if self.rect.x <= self.bounds[0] or self.rect.x >= self.bounds[1]:
            self.speed = -self.speed
            dx = self.speed
        self.rect.x = max(self.bounds[0], min(self.bounds[1], self.rect.x + dx))
        return dx

    def draw(self, screen, cam_y):
        pygame.draw.rect(screen, self.color, self.rect.move(0, -cam_y), border_radius=4)


class Coin:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.taken = False

    def draw(self, screen, cam_y):
        pygame.draw.circle(screen, (250, 210, 60), (self.pos.x, self.pos.y - cam_y), COIN_R)


def generate_platforms(num, start_y, width):
    platforms = [Platform(0, num, 0, start_y, width, movable=False)]  # ground never moves
    y = start_y - 100
    for i in range(1, num + 1):
        x = random.randint(20, width - 140)
        w = random.randint(80, 160)
        platforms.append(Platform(i, num, x, y, w))
        y -= random.randint(70, 120)
    return platforms


def spawn_coins(platforms):
    coins = []
    for plat in platforms[1:]:
        if random.random() < 0.4:
            coins.append(Coin(plat.rect.centerx, plat.rect.top - 14))
    return coins


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PLAYER_W, PLAYER_H)
        self.vel_y = 0.0
        self.vel_x = 0
        self.on_ground = False
        self.standing_on = None
        self.color = (60, 120, 200)

    def move(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = MOVE_SPEED
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = JUMP_SPEED
            self.on_ground = False

    def update(self, platforms):
        self.vel_y = min(self.vel_y + GRAVITY, 12)
        previous_bottom = self.rect.bottom
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x + self.vel_x))
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        self.standing_on = None
        if self.vel_y >= 0:
            for plat in platforms:
                overlaps = self.rect.right > plat.rect.left and self.rect.left < plat.rect.right
                if overlaps and previous_bottom <= plat.rect.top + 1 and self.rect.bottom >= plat.rect.top:
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    self.standing_on = plat
                    break

    def draw(self, screen, cam_y):
        draw_rect = self.rect.move(0, -cam_y)
        pygame.draw.rect(screen, self.color, draw_rect, border_radius=6)
        pygame.draw.circle(screen, (255, 220, 180), (draw_rect.centerx, draw_rect.top + 10), 7)


class Game:
    def __init__(self):
        self.font = pygame.font.Font(None, 26)
        self.big_font = pygame.font.Font(None, 42)
        self.reset()

    def reset(self):
        self.platforms = generate_platforms(60, HEIGHT - 40, WIDTH)
        self.coins = spawn_coins(self.platforms)
        self.player = Player(WIDTH // 2 - PLAYER_W // 2, HEIGHT - 100)
        self.cam_y = 0
        self.height = 0
        self.coin_score = 0
        self.lives = LIVES_START
        self.last_safe = pygame.Vector2(self.player.rect.x, self.player.rect.y)
        self.state = "play"
        self.top_y = self.platforms[-1].rect.y
        reset_effects()

    def score(self):
        return int(self.height) + self.coin_score

    def update(self, keys):
        if self.state != "play":
            return
        self.player.move(keys)
        for plat in self.platforms:
            dx = plat.update()
            if dx and self.player.standing_on is plat:
                self.player.rect.x += dx
        self.player.update(self.platforms)
        update_effects()
        target_cam = self.player.rect.centery - HEIGHT // 2
        if target_cam < self.cam_y:
            self.cam_y = target_cam
        # Task 1 fix: height is the BEST height reached, so it only ever goes up.
        current_height = max(0, (HEIGHT - 40 - self.player.rect.y) // 10)
        self.height = max(self.height, current_height)
        if self.player.on_ground:
            self.last_safe = pygame.Vector2(self.player.rect.x, self.player.rect.y)
        for coin in self.coins:
            if not coin.taken and self.player.rect.collidepoint(coin.pos):
                coin.taken = True
                self.coin_score += 50
                on_coin_collected(coin, self.score())
        self.coins = [c for c in self.coins if not c.taken]
        if self.player.rect.top - self.cam_y > HEIGHT + 50:
            self.lives -= 1
            reset_combo()  # falling breaks the combo
            if self.lives <= 0:
                self.state = "lose"
            else:
                self.player.rect.x, self.player.rect.y = int(self.last_safe.x), int(self.last_safe.y)
                self.player.vel_y = 0
        if self.player.rect.y <= self.top_y:
            self.state = "win"

    def draw(self, screen):
        screen.fill(BG)
        for plat in self.platforms:
            plat.draw(screen, self.cam_y)
        for coin in self.coins:
            coin.draw(screen, self.cam_y)
        self.player.draw(screen, self.cam_y)
        draw_effects(screen, self.cam_y)
        hud = self.font.render(f"Height: {self.height}m Coins: {self.coin_score // 50} Lives: {self.lives}", True, (200, 200, 200))
        screen.blit(hud, (10, 10))
        if combo >= 2:
            combo_text = self.font.render(f"Combo x{combo}!", True, (255, 200, 80))
            screen.blit(combo_text, (10, 36))
        if self.state != "play":
            text = "YOU REACHED THE TOP!" if self.state == "win" else "YOU FELL!"
            color = (80, 220, 80) if self.state == "win" else (220, 60, 60)
            msg = self.big_font.render(text, True, color)
            sub = self.font.render("Press R to Restart", True, (180, 180, 180))
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Climber")
    clock = pygame.time.Clock()
    game = Game()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game.reset()
        game.update(pygame.key.get_pressed())
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
