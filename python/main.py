import pygame
import ctypes
import os
import sys
import time


# 1. DLL

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

current_dir = application_path

dll_path = os.path.join(current_dir, "..", "bin", "RacetrackEngine.dll")
assets_dir = os.path.join(current_dir, "..", "assets")
maps_dir = os.path.join(current_dir, "..", "maps") 

# Перевірка наявності DLL
if not os.path.exists(dll_path):
    if getattr(sys, 'frozen', False):
        print(f"CRITICAL ERROR: DLL not found at: {dll_path}")
        print(f"Make sure 'bin' folder is next to the 'python' folder.")
        input("Press ENTER to exit...")
    else:
        print(f"DLL not found: {dll_path}")
    sys.exit()

try:
    lib = ctypes.CDLL(dll_path)
except OSError as e:
    print(f"Error loading DLL: {e}")
    if getattr(sys, 'frozen', False): input("Press ENTER to exit...")
    sys.exit()

class CarExportData(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int),
                ("vx", ctypes.c_int), ("vy", ctypes.c_int),
                ("state", ctypes.c_int), ("color", ctypes.c_int)]

lib.Game_new.restype = ctypes.c_void_p
lib.Game_get_car_data.restype = CarExportData
lib.Game_get_car_count.restype = ctypes.c_int

lib.Game_new.argtypes = [ctypes.c_int, ctypes.c_int]
lib.Game_delete.argtypes = [ctypes.c_void_p]
lib.Game_add_wall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lib.Game_add_car.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lib.Game_update_car.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lib.Game_get_car_data.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.Game_get_car_count.argtypes = [ctypes.c_void_p]
lib.Game_reset_car.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]


# 2. Налаштування

GRID_SIZE = 25
WIDTH, HEIGHT = 800, 600

CAR_PALETTE = [
    (220, 20, 60),   
    (240, 240, 240), 
    (30, 144, 255),  
    (50, 50, 50),    
    (0, 206, 209),   
    (255, 215, 0),   
    (138, 43, 226),  
    (255, 140, 0)   
]

COLORS = {
    'BG': (30, 30, 30), 'GRID': (200, 200, 255), 'UI_BG': (50, 50, 60),
    'BTN_NORMAL': (70, 70, 90), 'BTN_HOVER': (100, 100, 120),
    'TEXT': (255, 255, 255), 'OVERLAY': (0, 0, 0, 230)
}

menu_settings = {
    'map_id': 1, 'player_count': 2, 'player_colors': [0, 2, 1, 3]
}

RULES_TEXT = [
    "--- HOW TO PLAY ---",
    "",
    "1. MOVEMENT: You control the ACCELERATION.",
    "   Your car has inertia. If you speed up,",
    "   you will keep moving until you brake.",
    "",
    "2. CONTROLS:",
    "   [Arrows] or [NumPad] to change velocity.",
    "   [Space] or [5] to maintain speed.",
    "",
    "3. CRASHING:",
    "   Don't hit walls or map borders!",
    "   Penalty: 3 seconds respawn time.",
    "",
    "4. WINNING:",
    "   First player to reach the YELLOW zone wins.",
    "", 
    "5. PVP:",
    "   Don't hit other cars or you both crash!"
]


# 3. GUI елементи

class Button:
    def __init__(self, x, y, w, h, text, action=None, color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.is_hovered = False
        self.custom_color = color

    def draw(self, screen, font):
        base_col = self.custom_color if self.custom_color else COLORS['BTN_NORMAL']
        color = COLORS['BTN_HOVER'] if self.is_hovered else base_col
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200,200,200), self.rect, 2, border_radius=8)
        if self.text:
            txt_surf = font.render(self.text, True, COLORS['TEXT'])
            txt_rect = txt_surf.get_rect(center=self.rect.center)
            screen.blit(txt_surf, txt_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def check_click(self, mouse_pos):
        if self.is_hovered:
            if self.action: self.action()
            return True
        return False

class GameMap:
    def __init__(self):
        self.start_rect = None
        self.finish_rect = None
        self.walls = [] 
        self.background_image = None

    def load_from_file(self, filename, game_ptr=None):
        if not os.path.exists(filename): return False
        self.walls = []
        base_path = os.path.dirname(filename)
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if not parts or parts[0].startswith('#'): continue
                cmd = parts[0]
                
                if cmd == 'IMAGE':
                    img_path = os.path.join(base_path, parts[1])
                    if os.path.exists(img_path):
                        self.background_image = pygame.image.load(img_path)
                        self.background_image = pygame.transform.scale(self.background_image, (WIDTH, HEIGHT))
                    continue

                try: args = [int(x) for x in parts[1:]]
                except ValueError: continue

                if cmd == 'START':
                    self.start_rect = pygame.Rect(args[0]*GRID_SIZE, args[1]*GRID_SIZE, args[2]*GRID_SIZE, args[3]*GRID_SIZE)
                elif cmd == 'FINISH':
                    self.finish_rect = pygame.Rect(args[0]*GRID_SIZE, args[1]*GRID_SIZE, args[2]*GRID_SIZE, args[3]*GRID_SIZE)
                elif cmd == 'WALL' and game_ptr:
                    lib.Game_add_wall(game_ptr, args[0], args[1], args[2], args[3])
                    self.walls.append(args)
        return True

    def draw(self, screen, show_walls):
        if self.background_image: screen.blit(self.background_image, (0, 0))
        else: screen.fill((255, 255, 255))
        
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self.start_rect: pygame.draw.rect(s, (0, 255, 0, 50), self.start_rect)
        if self.finish_rect: pygame.draw.rect(s, (255, 255, 0, 50), self.finish_rect)
        screen.blit(s, (0,0))

        if show_walls:
            for w in self.walls:
                pygame.draw.line(screen, (255, 0, 0), (w[0]*GRID_SIZE, w[1]*GRID_SIZE), (w[2]*GRID_SIZE, w[3]*GRID_SIZE), 2)


# 4. Меню

map_thumbnails = {} 
def get_map_thumbnail(map_id):
    if map_id in map_thumbnails: return map_thumbnails[map_id]
    temp_map = GameMap()
    path = os.path.join(maps_dir, f"track{map_id}.txt")
    temp_map.load_from_file(path)
    if temp_map.background_image:
        thumb = pygame.transform.scale(temp_map.background_image, (200, 150))
        pygame.draw.rect(thumb, (255,255,255), (0,0,200,150), 4)
    else:
        thumb = pygame.Surface((200, 150))
        thumb.fill((100, 100, 100))
    map_thumbnails[map_id] = thumb
    return thumb

def run_menu(screen, font):
    clock = pygame.time.Clock()
    menu_state = 'MAIN'
    
    def open_map_select(): nonlocal menu_state; menu_state = 'MAP_SELECT'
    def open_rules(): nonlocal menu_state; menu_state = 'RULES'
    def back_to_main(): nonlocal menu_state; menu_state = 'MAIN'
    def add_player(delta):
        menu_settings['player_count'] = max(1, min(4, menu_settings['player_count'] + delta))
    
    btn_start = Button(300, 500, 200, 60, "START RACE", action=lambda: None, color=(0, 150, 0))
    btn_maps = Button(300, 200, 200, 40, "CHANGE MAP", open_map_select)
    btn_rules = Button(300, 260, 200, 40, "RULES", open_rules)
    btn_minus = Button(280, 350, 50, 50, "-", lambda: add_player(-1))
    btn_plus  = Button(470, 350, 50, 50, "+", lambda: add_player(1))
    main_buttons = [btn_start, btn_maps, btn_rules, btn_minus, btn_plus]
    
    btn_back = Button(300, 540, 200, 40, "BACK", back_to_main)

    available_maps = []
    i = 1
    while os.path.exists(os.path.join(maps_dir, f"track{i}.txt")):
        available_maps.append(i)
        i += 1

    title_font = pygame.font.SysFont("Segoe UI", 40, bold=True)
    rules_font = pygame.font.SysFont("Consolas", 18)

    while True:
        screen.fill(COLORS['UI_BG'])
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: return False

        if menu_state == 'MAIN':
            title = title_font.render("RACETRACK", True, (255, 215, 0))
            screen.blit(title, (400 - title.get_width()//2, 30))
            thumb = get_map_thumbnail(menu_settings['map_id'])
            screen.blit(thumb, (300, 70))
            pygame.draw.rect(screen, (255,255,255), (300, 70, 200, 150), 2)
            
            for btn in main_buttons:
                btn.check_hover(mouse_pos)
                btn.draw(screen, font)

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_start.check_click(mouse_pos): return True 
                    for btn in main_buttons:
                        if btn != btn_start: btn.check_click(mouse_pos)
                    pc = menu_settings['player_count']
                    start_x = 400 - (pc * 70) // 2
                    for i in range(pc):
                        rect = pygame.Rect(start_x + i*70, 420, 50, 50)
                        if rect.collidepoint(mouse_pos):
                             menu_settings['player_colors'][i] = (menu_settings['player_colors'][i] + 1) % len(CAR_PALETTE)

            lbl_pl = font.render(f"Players: {menu_settings['player_count']}", True, COLORS['TEXT'])
            screen.blit(lbl_pl, (400 - lbl_pl.get_width()//2, 320))
            pc = menu_settings['player_count']
            start_x = 400 - (pc * 70) // 2
            for i in range(pc):
                col_idx = menu_settings['player_colors'][i]
                rect = pygame.Rect(start_x + i*70, 420, 50, 50)
                safe_col_idx = col_idx if col_idx < len(CAR_PALETTE) else 0
                pygame.draw.rect(screen, CAR_PALETTE[safe_col_idx], rect, border_radius=8)
                pygame.draw.rect(screen, (255,255,255), rect, 2, border_radius=8)

        elif menu_state == 'MAP_SELECT':
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLORS['OVERLAY'])
            screen.blit(overlay, (0,0))
            title = font.render("SELECT A MAP", True, (255, 255, 255))
            screen.blit(title, (400 - title.get_width()//2, 50))
            start_x, start_y = 50, 100
            padding = 20
            clicked = False
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN: clicked = True
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: menu_state = 'MAIN'

            for idx, map_id in enumerate(available_maps):
                col = idx % 3
                row = idx // 3
                x = start_x + col * (220 + padding)
                y = start_y + row * (170 + padding)
                thumb = get_map_thumbnail(map_id)
                rect = pygame.Rect(x, y, 220, 170)
                if rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (255, 215, 0), (x-5, y-5, 230, 180), border_radius=10)
                    if clicked:
                        menu_settings['map_id'] = map_id
                        menu_state = 'MAIN'
                screen.blit(thumb, (x+10, y+10))
                name = font.render(f"Map {map_id}", True, (255,255,255))
                screen.blit(name, (x + 110 - name.get_width()//2, y + 175))

            btn_back.check_hover(mouse_pos)
            btn_back.draw(screen, font)
            if clicked and btn_back.check_click(mouse_pos): pass

        elif menu_state == 'RULES':
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLORS['OVERLAY'])
            screen.blit(overlay, (0,0))
            pygame.draw.rect(screen, (40, 40, 40), (100, 30, 600, 500), border_radius=15)
            pygame.draw.rect(screen, (255, 215, 0), (100, 30, 600, 500), 2, border_radius=15)

            y_offset = 50
            for line in RULES_TEXT:
                color = (255, 215, 0) if line.startswith("---") or (len(line)>0 and line[0].isdigit()) else (220, 220, 220)
                txt_surf = rules_font.render(line, True, color)
                screen.blit(txt_surf, (140, y_offset))
                y_offset += 25

            btn_back.check_hover(mouse_pos)
            btn_back.draw(screen, font)
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btn_back.check_click(mouse_pos): pass
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: menu_state = 'MAIN'

        pygame.display.flip()
        clock.tick(60)


# 5. Гра(звуки)

def run_game(screen, font):
    try:
        snd_crash = pygame.mixer.Sound(os.path.join(assets_dir, "crash.wav"))
        snd_win = pygame.mixer.Sound(os.path.join(assets_dir, "win.wav"))
        snd_move = pygame.mixer.Sound(os.path.join(assets_dir, "move.wav"))
        snd_move.set_volume(0.3)
    except:
        snd_crash = None
        snd_win = None
        snd_move = None

    game_ptr = lib.Game_new(WIDTH // GRID_SIZE, HEIGHT // GRID_SIZE)
    current_map = GameMap()
    map_file = f"track{menu_settings['map_id']}.txt"
    map_path = os.path.join(maps_dir, map_file)
    current_map.load_from_file(map_path, game_ptr)

    # Визначення стартових позицій
    center_x, center_y = 2, 2
    rect_w, rect_h = 4, 4
    if current_map.start_rect:
        center_x = (current_map.start_rect.x + current_map.start_rect.w/2) / GRID_SIZE
        center_y = (current_map.start_rect.y + current_map.start_rect.h/2) / GRID_SIZE
        rect_w = current_map.start_rect.w / GRID_SIZE
        rect_h = current_map.start_rect.h / GRID_SIZE

    count = menu_settings['player_count']
    start_positions = []
    
    # Розташування машин
    is_horizontal_start = rect_w >= rect_h 
    spacing = 2.0 

    for i in range(count):
        offset = (i - (count - 1) / 2.0) * spacing
        if is_horizontal_start:
            start_x = int(center_x + offset)
            start_y = int(center_y)
        else:
            start_x = int(center_x)
            start_y = int(center_y + offset)
        lib.Game_add_car(game_ptr, start_x, start_y, menu_settings['player_colors'][i])
        start_positions.append((start_x, start_y))

    total_players = lib.Game_get_car_count(game_ptr)
    current_player = 0
    car_trails = [ [] for _ in range(total_players) ]
    crash_timers = {} 
    
    for i in range(total_players):
        d = lib.Game_get_car_data(game_ptr, i)
        car_trails[i].append((d.x, d.y))

    show_debug_walls = False
    running = True
    winner_id = -1
    clock = pygame.time.Clock()

    while running:
        move = None
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: 
                lib.Game_delete(game_ptr)
                return "QUIT"
            if event.type == pygame.KEYDOWN:
                if winner_id != -1: running = False
                if event.key == pygame.K_ESCAPE: running = False 
                if event.key == pygame.K_h: show_debug_walls = not show_debug_walls
                
                if winner_id == -1:
                    if event.key in [pygame.K_UP, pygame.K_KP8]: move = (0, -1)
                    elif event.key in [pygame.K_DOWN, pygame.K_KP2]: move = (0, 1)
                    elif event.key in [pygame.K_LEFT, pygame.K_KP4]: move = (-1, 0)
                    elif event.key in [pygame.K_RIGHT, pygame.K_KP6]: move = (1, 0)
                    elif event.key in [pygame.K_SPACE, pygame.K_KP5]: move = (0, 0)
                    elif event.key == pygame.K_KP7: move = (-1, -1)
                    elif event.key == pygame.K_KP9: move = (1, -1)
                    elif event.key == pygame.K_KP1: move = (-1, 1)
                    elif event.key == pygame.K_KP3: move = (1, 1)

        if winner_id == -1:
            p_data = lib.Game_get_car_data(game_ptr, current_player)
            if move and p_data.state == 0:
                lib.Game_update_car(game_ptr, current_player, move[0], move[1])
                new_d = lib.Game_get_car_data(game_ptr, current_player)
                
                if new_d.state == 1:
                    if snd_crash: snd_crash.play()
                else:
                    if snd_move: snd_move.play()

                car_pixel_x = new_d.x * GRID_SIZE
                car_pixel_y = new_d.y * GRID_SIZE
                car_point = (car_pixel_x, car_pixel_y)
                
                if current_map.finish_rect and current_map.finish_rect.collidepoint(car_point):
                    winner_id = current_player
                    if snd_win: snd_win.play()
                
                car_trails[current_player].append((new_d.x, new_d.y))
                if winner_id == -1:
                    current_player = (current_player + 1) % total_players
            
            elif p_data.state == 1: 
                 current_player = (current_player + 1) % total_players

        screen.fill(COLORS['GRID'])
        current_map.draw(screen, show_debug_walls)

        for x in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(screen, COLORS['GRID'], (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(screen, COLORS['GRID'], (0, y), (WIDTH, y), 1)

        trail_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i, path in enumerate(car_trails):
            if len(path) > 1:
                d = lib.Game_get_car_data(game_ptr, i)
                safe_col_idx = d.color if d.color < len(CAR_PALETTE) else 0
                base_col = CAR_PALETTE[safe_col_idx]
                trail_col = (base_col[0], base_col[1], base_col[2], 100)
                pixel_points = [(p[0]*GRID_SIZE, p[1]*GRID_SIZE) for p in path]
                pygame.draw.lines(trail_surf, trail_col, False, pixel_points, 4)
                for p in pixel_points: pygame.draw.circle(trail_surf, trail_col, p, 3)
        screen.blit(trail_surf, (0,0))

        current_time = time.time()
        for i in range(total_players):
            d = lib.Game_get_car_data(game_ptr, i)
            sx, sy = d.x * GRID_SIZE, d.y * GRID_SIZE
            safe_col_idx = d.color if d.color < len(CAR_PALETTE) else 0
            col = CAR_PALETTE[safe_col_idx]
            
            if d.state == 1: 
                pygame.draw.line(screen, (100,100,100), (sx-8, sy-8), (sx+8, sy+8), 3)
                pygame.draw.line(screen, (100,100,100), (sx-8, sy+8), (sx+8, sy-8), 3)
                
                if winner_id == -1:
                    if i not in crash_timers: crash_timers[i] = current_time
                    elapsed = current_time - crash_timers[i]
                    remaining = 3.0 - elapsed
                    if remaining <= 0:
                        try:
                            rx, ry = start_positions[i]
                            lib.Game_reset_car(game_ptr, i, rx, ry)
                            del crash_timers[i]
                            car_trails[i] = [(rx, ry)] 
                        except AttributeError: pass
                    else:
                        t_surf = font.render(f"{remaining:.1f}", True, (255, 0, 0))
                        screen.blit(t_surf, (sx - 10, sy - 30))
            else:
                if i in crash_timers: del crash_timers[i]
                pygame.draw.circle(screen, col, (sx, sy), 7)
                pygame.draw.line(screen, col, (sx, sy), (sx + d.vx*GRID_SIZE, sy + d.vy*GRID_SIZE), 2)
                pygame.draw.circle(screen, col, (sx + d.vx*GRID_SIZE, sy + d.vy*GRID_SIZE), 3)

        if winner_id == -1:
            txt = font.render(f"Player {current_player+1}'s Turn | [ESC]-Menu", True, (0,0,0))
            pygame.draw.rect(screen, (255,255,255), (5,5, txt.get_width()+10, 30))
            screen.blit(txt, (10, 10))
        else:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0,0))
            
            win_d = lib.Game_get_car_data(game_ptr, winner_id)
            safe_col_idx = win_d.color if win_d.color < len(CAR_PALETTE) else 0
            win_col = CAR_PALETTE[safe_col_idx]
            
            win_font = pygame.font.SysFont("Segoe UI", 60, bold=True)
            win_txt = win_font.render(f"PLAYER {winner_id+1} WINS!", True, win_col)
            screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, HEIGHT//2 - 50))
            
            hint_font = pygame.font.SysFont("Segoe UI", 30)
            hint_txt = hint_font.render("Press any key to Menu", True, (255, 255, 255))
            screen.blit(hint_txt, (WIDTH//2 - hint_txt.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()
        clock.tick(60)
    
    lib.Game_delete(game_ptr)
    return "MENU"

def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Racetrack Deluxe")
    font = pygame.font.SysFont("Segoe UI", 24, bold=True)

    while True:
        start = run_menu(screen, font)
        if not start: break 
        res = run_game(screen, font)
        if res == "QUIT": break

    pygame.quit()

if __name__ == "__main__":
    main()