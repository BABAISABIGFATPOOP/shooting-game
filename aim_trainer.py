import pygame
import random
import time
import math
import sys

pygame.init()

# --- Constants ---
INFO = pygame.display.Info()
WIDTH, HEIGHT = INFO.current_w, INFO.current_h
FPS = 60
FONT_NAME = None  # default system font

# Colors
BG_COLOR = (20, 20, 30)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 200, 80)
YELLOW = (240, 200, 40)
ORANGE = (240, 140, 40)
LIGHT_GRAY = (180, 180, 190)
DARK_GRAY = (40, 40, 55)
PANEL_COLOR = (30, 30, 45)
ACCENT = (80, 140, 255)
TARGET_COLORS = [
    (255, 80, 80),
    (255, 160, 60),
    (255, 220, 50),
    (100, 220, 100),
    (60, 180, 255),
    (180, 100, 255),
]

# Game settings
HUD_HEIGHT = 60
PLAY_AREA_TOP = HUD_HEIGHT
PLAY_AREA = pygame.Rect(0, PLAY_AREA_TOP, WIDTH, HEIGHT - HUD_HEIGHT)
COMBO_DECAY_TIME = 1.5  # seconds to maintain combo

# Difficulty presets: (min_radius, max_radius, shrink_speed, spawn_start, spawn_min, spawn_speedup, lives)
DIFFICULTIES = {
    "Easy": {
        "min_radius": 30,
        "max_radius": 55,
        "shrink_speed": 18,
        "spawn_start": 1.8,
        "spawn_min": 0.7,
        "spawn_speedup": 0.01,
        "lives": 7,
        "color": GREEN,
        "desc": "Large targets, slow shrink",
    },
    "Medium": {
        "min_radius": 18,
        "max_radius": 42,
        "shrink_speed": 30,
        "spawn_start": 1.2,
        "spawn_min": 0.4,
        "spawn_speedup": 0.015,
        "lives": 5,
        "color": YELLOW,
        "desc": "Standard targets and speed",
    },
    "Hard": {
        "min_radius": 10,
        "max_radius": 28,
        "shrink_speed": 45,
        "spawn_start": 0.8,
        "spawn_min": 0.25,
        "spawn_speedup": 0.02,
        "lives": 3,
        "color": RED,
        "desc": "Tiny targets, fast shrink",
    },
    "Impossible": {
        "min_radius": 6,
        "max_radius": 18,
        "shrink_speed": 60,
        "spawn_start": 0.5,
        "spawn_min": 0.15,
        "spawn_speedup": 0.025,
        "lives": 1,
        "color": ORANGE,
        "desc": "Good luck...",
    },
}
DIFFICULTY_NAMES = list(DIFFICULTIES.keys())


# --- Helper ---
def clamp(val, lo, hi):
    return max(lo, min(hi, val))


# --- Target ---
class Target:
    def __init__(self, diff):
        self.max_radius = random.randint(diff["min_radius"], diff["max_radius"])
        self.radius = self.max_radius
        self.shrink_speed = diff["shrink_speed"]
        self.x = random.randint(
            PLAY_AREA.left + self.max_radius,
            PLAY_AREA.right - self.max_radius,
        )
        self.y = random.randint(
            PLAY_AREA.top + self.max_radius,
            PLAY_AREA.bottom - self.max_radius,
        )
        self.color = random.choice(TARGET_COLORS)
        self.spawn_time = time.time()
        self.alive = True

    def update(self, dt):
        self.radius -= self.shrink_speed * dt
        if self.radius <= 0:
            self.alive = False

    def draw(self, surface):
        r = max(int(self.radius), 1)
        # outer ring
        pygame.draw.circle(surface, self.color, (self.x, self.y), r, 3)
        # inner filled
        inner = max(r - 6, 2)
        pygame.draw.circle(surface, self.color, (self.x, self.y), inner)
        # bullseye
        bull = max(r // 3, 2)
        pygame.draw.circle(surface, WHITE, (self.x, self.y), bull)

    def contains(self, pos):
        dx = pos[0] - self.x
        dy = pos[1] - self.y
        return dx * dx + dy * dy <= self.radius * self.radius


# --- Hit effect ---
class HitEffect:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.timer = 0.6

    def update(self, dt):
        self.timer -= dt
        self.y -= 40 * dt

    def draw(self, surface, font):
        if self.timer > 0:
            alpha = clamp(int(255 * (self.timer / 0.6)), 0, 255)
            txt = font.render(self.text, True, self.color)
            txt.set_alpha(alpha)
            surface.blit(txt, (self.x - txt.get_width() // 2, int(self.y)))


# --- Game ---
class AimTrainer:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Aim Trainer")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(FONT_NAME, 48)
        self.font_med = pygame.font.Font(FONT_NAME, 28)
        self.font_sm = pygame.font.Font(FONT_NAME, 20)
        self.font_xs = pygame.font.Font(FONT_NAME, 16)
        self.state = "menu"  # menu, playing, gameover
        self.selected_difficulty = 1  # default to Medium
        self.difficulty = DIFFICULTIES[DIFFICULTY_NAMES[self.selected_difficulty]]
        self.crosshair = self._make_crosshair()
        pygame.mouse.set_visible(False)
        self.reset()

    def _make_crosshair(self):
        size = 28
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        # cross lines
        pygame.draw.line(surf, WHITE, (c, 0), (c, size), 2)
        pygame.draw.line(surf, WHITE, (0, c), (size, c), 2)
        # circle
        pygame.draw.circle(surf, WHITE, (c, c), 10, 1)
        # center dot
        pygame.draw.circle(surf, RED, (c, c), 2)
        return surf

    def reset(self):
        self.targets = []
        self.effects = []
        self.score = 0
        self.hits = 0
        self.shots = 0
        self.lives = self.difficulty["lives"]
        self.combo = 0
        self.best_combo = 0
        self.last_hit_time = 0
        self.spawn_timer = 0
        self.spawn_interval = self.difficulty["spawn_start"]
        self.targets_spawned = 0
        self.start_time = 0
        self.elapsed = 0
        self.reaction_times = []

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "menu"
                        else:
                            running = False
                    if self.state == "menu":
                        if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            self.selected_difficulty = (self.selected_difficulty - 1) % len(DIFFICULTY_NAMES)
                            self.difficulty = DIFFICULTIES[DIFFICULTY_NAMES[self.selected_difficulty]]
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            self.selected_difficulty = (self.selected_difficulty + 1) % len(DIFFICULTY_NAMES)
                            self.difficulty = DIFFICULTIES[DIFFICULTY_NAMES[self.selected_difficulty]]
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.state == "menu":
                            self.reset()
                            self.state = "playing"
                            self.start_time = time.time()
                        elif self.state == "gameover":
                            self.state = "menu"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "menu":
                        # Check if clicking a difficulty button
                        clicked_diff = False
                        if hasattr(self, "diff_rects"):
                            for i, rect in enumerate(self.diff_rects):
                                if rect.collidepoint(event.pos):
                                    self.selected_difficulty = i
                                    self.difficulty = DIFFICULTIES[DIFFICULTY_NAMES[i]]
                                    clicked_diff = True
                                    break
                        if not clicked_diff:
                            self.reset()
                            self.state = "playing"
                            self.start_time = time.time()
                    elif self.state == "playing":
                        self._handle_shot(event.pos)
                    elif self.state == "gameover":
                        self.state = "menu"

            if self.state == "playing":
                self._update(dt)

            self._draw()
        pygame.quit()
        sys.exit()

    # --- Game logic ---
    def _handle_shot(self, pos):
        self.shots += 1
        hit = False
        # check targets in reverse (top-most first)
        for t in reversed(self.targets):
            if t.alive and t.contains(pos):
                t.alive = False
                hit = True
                self.hits += 1
                react = time.time() - t.spawn_time
                self.reaction_times.append(react)

                # combo
                now = time.time()
                if now - self.last_hit_time < COMBO_DECAY_TIME:
                    self.combo += 1
                else:
                    self.combo = 1
                self.last_hit_time = now
                self.best_combo = max(self.best_combo, self.combo)

                # score: smaller target + faster reaction + combo
                size_bonus = max(1, (self.difficulty["max_radius"] - t.max_radius) // 4)
                speed_bonus = max(1, int(10 / max(react, 0.1)))
                combo_mult = min(self.combo, 10)
                points = (10 + size_bonus + speed_bonus) * combo_mult
                self.score += points

                color = GREEN if react < 0.5 else YELLOW if react < 1.0 else ORANGE
                self.effects.append(HitEffect(t.x, t.y, f"+{points}", color))
                if self.combo >= 3:
                    self.effects.append(
                        HitEffect(t.x, t.y + 20, f"x{self.combo} combo!", ACCENT)
                    )
                break

        if not hit:
            self.combo = 0
            self.effects.append(HitEffect(pos[0], pos[1], "miss", RED))

    def _update(self, dt):
        self.elapsed = time.time() - self.start_time

        # spawn targets
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.targets.append(Target(self.difficulty))
            self.targets_spawned += 1
            self.spawn_interval = max(
                self.difficulty["spawn_min"],
                self.difficulty["spawn_start"] - self.targets_spawned * self.difficulty["spawn_speedup"],
            )
            self.spawn_timer = self.spawn_interval

        # update targets
        for t in self.targets:
            t.update(dt)

        # remove expired targets (lose a life)
        expired = [t for t in self.targets if not t.alive and t.radius <= 0]
        for t in expired:
            self.lives -= 1
            self.effects.append(HitEffect(t.x, t.y, "-1 life", RED))
        self.targets = [t for t in self.targets if t.alive]

        # update effects
        for e in self.effects:
            e.update(dt)
        self.effects = [e for e in self.effects if e.timer > 0]

        # check game over
        if self.lives <= 0:
            self.state = "gameover"

    # --- Drawing ---
    def _draw(self):
        self.screen.fill(BG_COLOR)

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "playing":
            self._draw_game()
        elif self.state == "gameover":
            self._draw_gameover()

        # crosshair
        mx, my = pygame.mouse.get_pos()
        self.screen.blit(
            self.crosshair,
            (mx - self.crosshair.get_width() // 2, my - self.crosshair.get_height() // 2),
        )

        pygame.display.flip()

    def _draw_menu(self):
        title = self.font_big.render("AIM TRAINER", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))

        # Difficulty selector
        diff_label = self.font_sm.render("Difficulty:", True, LIGHT_GRAY)
        self.screen.blit(diff_label, (WIDTH // 2 - diff_label.get_width() // 2, 200))

        # Draw difficulty options
        total_width = 0
        option_widths = []
        for name in DIFFICULTY_NAMES:
            w = self.font_med.size(name)[0] + 40
            option_widths.append(w)
            total_width += w + 20
        total_width -= 20
        start_x = WIDTH // 2 - total_width // 2
        x = start_x
        y = 235
        self.diff_rects = []
        for i, name in enumerate(DIFFICULTY_NAMES):
            diff = DIFFICULTIES[name]
            w = option_widths[i]
            rect = pygame.Rect(x, y, w, 40)
            self.diff_rects.append(rect)
            selected = i == self.selected_difficulty
            if selected:
                pygame.draw.rect(self.screen, diff["color"], rect, border_radius=6)
                txt = self.font_med.render(name, True, BG_COLOR)
            else:
                pygame.draw.rect(self.screen, DARK_GRAY, rect, border_radius=6)
                pygame.draw.rect(self.screen, diff["color"], rect, 2, border_radius=6)
                txt = self.font_med.render(name, True, diff["color"])
            self.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
            x += w + 20

        # Difficulty description
        diff = self.difficulty
        desc = self.font_sm.render(diff["desc"], True, diff["color"])
        self.screen.blit(desc, (WIDTH // 2 - desc.get_width() // 2, 290))

        details = self.font_xs.render(
            f"Lives: {diff['lives']}  |  Target size: {diff['min_radius']}-{diff['max_radius']}  |  Shrink speed: {diff['shrink_speed']}",
            True, LIGHT_GRAY,
        )
        self.screen.blit(details, (WIDTH // 2 - details.get_width() // 2, 318))

        # Arrow hints
        arrows = self.font_sm.render("<  A/D or Arrow Keys to change  >", True, ACCENT)
        self.screen.blit(arrows, (WIDTH // 2 - arrows.get_width() // 2, 355))

        sub = self.font_med.render("Click or press SPACE to start", True, LIGHT_GRAY)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 400))

        instructions = [
            "Shoot targets before they shrink away",
            "Smaller & faster hits = more points",
            "Build combos for score multipliers",
            f"You have {diff['lives']} lives - don't let targets expire!",
            "Press ESC to return to menu",
        ]
        for i, line in enumerate(instructions):
            txt = self.font_xs.render(line, True, LIGHT_GRAY)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 450 + i * 28))

    def _draw_game(self):
        # play area border
        pygame.draw.rect(self.screen, DARK_GRAY, PLAY_AREA, 1)

        # targets
        for t in self.targets:
            t.draw(self.screen)

        # effects
        for e in self.effects:
            e.draw(self.screen, self.font_sm)

        # HUD
        pygame.draw.rect(self.screen, PANEL_COLOR, (0, 0, WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.screen, DARK_GRAY, (0, HUD_HEIGHT), (WIDTH, HUD_HEIGHT), 2)

        # score
        score_txt = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_txt, (20, 14))

        # accuracy
        acc = (self.hits / self.shots * 100) if self.shots > 0 else 0
        acc_color = GREEN if acc >= 70 else YELLOW if acc >= 40 else RED
        acc_txt = self.font_sm.render(f"Acc: {acc:.0f}%", True, acc_color)
        self.screen.blit(acc_txt, (240, 18))

        # combo
        if self.combo >= 2:
            combo_txt = self.font_sm.render(f"Combo: x{self.combo}", True, ACCENT)
            self.screen.blit(combo_txt, (380, 18))

        # lives
        lives_txt = self.font_sm.render(f"Lives: ", True, WHITE)
        self.screen.blit(lives_txt, (WIDTH - 200, 18))
        for i in range(self.lives):
            pygame.draw.circle(self.screen, RED, (WIDTH - 135 + i * 22, 28), 8)

        # difficulty label
        diff_name = DIFFICULTY_NAMES[self.selected_difficulty]
        diff_txt = self.font_xs.render(diff_name, True, self.difficulty["color"])
        self.screen.blit(diff_txt, (WIDTH // 2 - diff_txt.get_width() // 2, 20))

        # timer
        timer_txt = self.font_sm.render(f"{self.elapsed:.1f}s", True, LIGHT_GRAY)
        self.screen.blit(timer_txt, (WIDTH - 60, 18))

    def _draw_gameover(self):
        title = self.font_big.render("GAME OVER", True, RED)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        acc = (self.hits / self.shots * 100) if self.shots > 0 else 0
        avg_react = (
            sum(self.reaction_times) / len(self.reaction_times)
            if self.reaction_times
            else 0
        )

        diff_name = DIFFICULTY_NAMES[self.selected_difficulty]
        diff_label = self.font_med.render(f"[ {diff_name} ]", True, self.difficulty["color"])
        self.screen.blit(diff_label, (WIDTH // 2 - diff_label.get_width() // 2, 155))

        stats = [
            (f"Final Score: {self.score}", WHITE),
            (f"Accuracy: {acc:.1f}%  ({self.hits}/{self.shots})", GREEN if acc >= 60 else YELLOW),
            (f"Avg Reaction: {avg_react*1000:.0f}ms", ACCENT),
            (f"Best Combo: x{self.best_combo}", ACCENT),
            (f"Time Survived: {self.elapsed:.1f}s", LIGHT_GRAY),
            (f"Targets Spawned: {self.targets_spawned}", LIGHT_GRAY),
        ]
        for i, (text, color) in enumerate(stats):
            txt = self.font_med.render(text, True, color)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 200 + i * 45))

        prompt = self.font_sm.render("Click or press SPACE to continue", True, LIGHT_GRAY)
        self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 500))


if __name__ == "__main__":
    AimTrainer().run()
