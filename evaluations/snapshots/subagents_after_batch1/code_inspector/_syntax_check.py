import tkinter as tk
import random
import sys

# Constants
COLS = 10
ROWS = 20
CELL_SIZE = 30
SIDEBAR_WIDTH = 200

COLORS = {
    'I': '#00CED1',
    'O': '#FFD700',
    'T': '#9932CC',
    'S': '#32CD32',
    'Z': '#FF4500',
    'J': '#4169E1',
    'L': '#FF8C00',
}

EMPTY = '#1a1a2e'
GRID_COLOR = '#16213e'

# Tetromino definitions: list of 4 rotation states, each a list of (row, col) offsets
TETROMINOES = {
    'I': [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    'O': [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    'T': [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    'S': [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 1), (1, 2), (2, 0), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    'Z': [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 2), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(0, 0), (1, 0), (1, 1), (2, 0)],
    ],
    'J': [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    'L': [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
    ],
}

SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}


class Tetromino:
    def __init__(self, kind):
        self.kind = kind
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = 0

    def cells(self):
        shape = TETROMINOES[self.kind][self.rotation]
        return [(self.y + dr, self.x + dc) for dr, dc in shape]

    def rotate(self, direction=1):
        self.rotation = (self.rotation + direction) % 4


class Board:
    def __init__(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]

    def is_valid_position(self, piece):
        for r, c in piece.cells():
            if r < 0 or r >= ROWS or c < 0 or c >= COLS:
                return False
            if r >= 0 and self.grid[r][c] is not None:
                return False
        return True

    def merge(self, piece):
        color = COLORS[piece.kind]
        for r, c in piece.cells():
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.grid[r][c] = color

    def full_rows(self):
        return [r for r in range(ROWS) if all(self.grid[r][c] is not None for c in range(COLS))]

    def remove_rows(self, rows):
        for r in sorted(rows, reverse=True):
            del self.grid[r]
            self.grid.insert(0, [None] * COLS)


class Game:
    def __init__(self):
        self.board = Board()
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.paused = False
        self.game_over = False
        self.bag = []
        self.current = self._next_piece()
        self.next = self._next_piece()
        self.tick_interval = self._get_tick_interval()
        self._last_tick = 0
        self._animating = False

    def _get_tick_interval(self):
        return max(100, 500 - (self.level - 1) * 40)

    def _next_piece(self):
        if not self.bag:
            self.bag = list(TETROMINOES.keys())
            random.shuffle(self.bag)
        kind = self.bag.pop()
        return Tetromino(kind)

    def spawn(self):
        self.current = self.next
        self.next = self._next_piece()
        if not self.board.is_valid_position(self.current):
            self.game_over = True

    def move(self, dx):
        if self.game_over or self.paused:
            return
        old_x = self.current.x
        self.current.x += dx
        if not self.board.is_valid_position(self.current):
            self.current.x = old_x

    def rotate(self, direction=1):
        if self.game_over or self.paused:
            return
        old_rot = self.current.rotation
        self.current.rotate(direction)
        if not self.board.is_valid_position(self.current):
            # Try wall kick
            for kick in [-1, 1, -2, 2]:
                self.current.x += kick
                if self.board.is_valid_position(self.current):
                    return
                self.current.x -= kick
            self.current.rotation = old_rot

    def soft_drop(self):
        if self.game_over or self.paused:
            return
        old_y = self.current.y
        self.current.y += 1
        if not self.board.is_valid_position(self.current):
            self.current.y = old_y
            self._lock_piece()
        else:
            self.score += 1

    def hard_drop(self):
        if self.game_over or self.paused:
            return
        distance = 0
        while self.board.is_valid_position(self._moved_piece(1)):
            self.current.y += 1
            distance += 1
        self.score += distance * 2
        self._lock_piece()

    def _moved_piece(self, dy):
        piece = Tetromino(self.current.kind)
        piece.rotation = self.current.rotation
        piece.x = self.current.x
        piece.y = self.current.y + dy
        return piece

    def _lock_piece(self):
        self.board.merge(self.current)
        rows = self.board.full_rows()
        if rows:
            n = len(rows)
            self.board.remove_rows(rows)
            self.score += SCORE_TABLE[n] * self.level
            self.lines_cleared += n
            self.level = self.lines_cleared // 10 + 1
            self.tick_interval = self._get_tick_interval()
        self.spawn()

    def gravity_tick(self):
        if self.game_over or self.paused:
            return
        self.current.y += 1
        if not self.board.is_valid_position(self.current):
            self.current.y -= 1
            self._lock_piece()

    def toggle_pause(self):
        if not self.game_over:
            self.paused = not self.paused


class TetrisApp:
    def __init__(self, root):
        self.root = root
        root.title("Tetris")
        root.resizable(False, False)

        self.game = Game()

        board_width = COLS * CELL_SIZE
        board_height = ROWS * CELL_SIZE
        total_width = board_width + SIDEBAR_WIDTH
        total_height = board_height

        root.geometry(f"{total_width}x{total_height}")
        root.configure(bg='#0f0f23')

        # Canvas for board
        self.canvas = tk.Canvas(root, width=board_width, height=board_height,
                                bg=GRID_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(10, 5), pady=10)

        # Sidebar
        sidebar = tk.Frame(root, width=SIDEBAR_WIDTH, bg='#0f0f23')
        sidebar.pack(side=tk.LEFT, padx=(5, 10), pady=10, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="TETRIS", font=('Courier', 18, 'bold'),
                 fg='#00CED1', bg='#0f0f23').pack(pady=(10, 5))

        tk.Label(sidebar, text="Score", font=('Courier', 11),
                 fg='white', bg='#0f0f23').pack()
        self.score_label = tk.Label(sidebar, text="0", font=('Courier', 14, 'bold'),
                                    fg='#FFD700', bg='#0f0f23')
        self.score_label.pack()

        tk.Label(sidebar, text="Level", font=('Courier', 11),
                 fg='white', bg='#0f0f23').pack(pady=(10, 0))
        self.level_label = tk.Label(sidebar, text="1", font=('Courier', 14, 'bold'),
                                    fg='#FF4500', bg='#0f0f23')
        self.level_label.pack()

        tk.Label(sidebar, text="Lines", font=('Courier', 11),
                 fg='white', bg='#0f0f23').pack(pady=(10, 0))
        self.lines_label = tk.Label(sidebar, text="0", font=('Courier', 14, 'bold'),
                                    fg='#32CD32', bg='#0f0f23')
        self.lines_label.pack()

        tk.Label(sidebar, text="Next", font=('Courier', 11),
                 fg='white', bg='#0f0f23').pack(pady=(20, 5))
        self.next_canvas = tk.Canvas(sidebar, width=4 * CELL_SIZE, height=4 * CELL_SIZE,
                                     bg='#1a1a2e', highlightthickness=1,
                                     highlightbackground='#333')
        self.next_canvas.pack()

        tk.Label(sidebar, text="Controls:", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack(pady=(20, 2))
        tk.Label(sidebar, text="← → : Move", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()
        tk.Label(sidebar, text="↑ : Rotate", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()
        tk.Label(sidebar, text="↓ : Soft Drop", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()
        tk.Label(sidebar, text="Space : Hard Drop", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()
        tk.Label(sidebar, text="P : Pause", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()
        tk.Label(sidebar, text="R : Restart", font=('Courier', 9),
                 fg='#888', bg='#0f0f23').pack()

        # Key bindings
        root.bind('<Left>', lambda e: self.game.move(-1))
        root.bind('<Right>', lambda e: self.game.move(1))
        root.bind('<Up>', lambda e: self.game.rotate(1))
        root.bind('<Down>', lambda e: self.game.soft_drop())
        root.bind('<space>', lambda e: self.game.hard_drop())
        root.bind('p', lambda e: self.game.toggle_pause())
        root.bind('P', lambda e: self.game.toggle_pause())
        root.bind('r', lambda e: self.restart())
        root.bind('R', lambda e: self.restart())
        root.bind('<Escape>', lambda e: root.destroy())

        # Start game loop
        self._game_loop()

    def restart(self):
        self.game = Game()
        self._draw()

    def _game_loop(self):
        if not self.game.game_over:
            self.game.gravity_tick()
            self._draw()
        else:
            self._draw_game_over()
        self.root.after(self.game.tick_interval, self._game_loop)

    def _draw(self):
        self.canvas.delete('all')
        g = self.game.board.grid

        # Draw board
        for r in range(ROWS):
            for c in range(COLS):
                x = c * CELL_SIZE
                y = r * CELL_SIZE
                color = g[r][c] if g[r][c] else EMPTY
                self.canvas.create_rectangle(x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1,
                                             fill=color, outline='#0a0a1a', width=1)

        # Draw current piece
        if self.game.current:
            color = COLORS[self.game.current.kind]
            for r, c in self.game.current.cells():
                if 0 <= r < ROWS and 0 <= c < COLS:
                    x = c * CELL_SIZE
                    y = r * CELL_SIZE
                    self.canvas.create_rectangle(x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1,
                                                 fill=color, outline='#0a0a1a', width=1)
                    # Inner highlight
                    self.canvas.create_rectangle(x + 3, y + 3, x + CELL_SIZE - 4, y + CELL_SIZE - 4,
                                                 outline='#ffffff', width=1)

        # Draw ghost piece
        if self.game.current:
            ghost = Tetromino(self.game.current.kind)
            ghost.rotation = self.game.current.rotation
            ghost.x = self.game.current.x
            ghost.y = self.game.current.y
            while True:
                ghost.y += 1
                if not self.game.board.is_valid_position(ghost):
                    ghost.y -= 1
                    break
            color = COLORS[self.game.current.kind]
            for r, c in ghost.cells():
                if 0 <= r < ROWS and 0 <= c < COLS:
                    x = c * CELL_SIZE
                    y = r * CELL_SIZE
                    if self.game.board.grid[r][c] is None:
                        self.canvas.create_rectangle(x + 2, y + 2, x + CELL_SIZE - 3, y + CELL_SIZE - 3,
                                                     outline=color, width=2)

        # Draw next piece
        self.next_canvas.delete('all')
        if self.game.next:
            next_piece = self.game.next
            color = COLORS[next_piece.kind]
            shape = TETROMINOES[next_piece.kind][0]
            min_r = min(dr for dr, dc in shape)
            max_r = max(dr for dr, dc in shape)
            min_c = min(dc for dr, dc in shape)
            max_c = max(dc for dr, dc in shape)
            piece_w = (max_c - min_c + 1) * CELL_SIZE
            piece_h = (max_r - min_r + 1) * CELL_SIZE
            offset_x = (4 * CELL_SIZE - piece_w) // 2
            offset_y = (4 * CELL_SIZE - piece_h) // 2
            for dr, dc in shape:
                x = offset_x + (dc - min_c) * CELL_SIZE
                y = offset_y + (dr - min_r) * CELL_SIZE
                self.next_canvas.create_rectangle(x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1,
                                                  fill=color, outline='#0a0a1a', width=1)

        # Update labels
        self.score_label.config(text=str(self.game.score))
        self.level_label.config(text=str(self.game.level))
        self.lines_label.config(text=str(self.game.lines_cleared))

        # Pause overlay
        if self.game.paused:
            self.canvas.create_rectangle(0, 0, COLS * CELL_SIZE, ROWS * CELL_SIZE,
                                         fill='#00000080')
            self.canvas.create_text(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2,
                                    text="PAUSED", font=('Courier', 24, 'bold'),
                                    fill='white')

    def _draw_game_over(self):
        self._draw()
        self.canvas.create_rectangle(0, 0, COLS * CELL_SIZE, ROWS * CELL_SIZE,
                                     fill='#00000090')
        self.canvas.create_text(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2 - 20,
                                text="GAME OVER", font=('Courier', 24, 'bold'),
                                fill='#FF4500')
        self.canvas.create_text(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2 + 20,
                                text=f"Score: {self.game.score}", font=('Courier', 14),
                                fill='white')
        self.canvas.create_text(COLS * CELL_SIZE // 2, ROWS * CELL_SIZE // 2 + 50,
                                text="Press R to Restart", font=('Courier', 12),
                                fill='#888')


def main():
    root = tk.Tk()
    app = TetrisApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()