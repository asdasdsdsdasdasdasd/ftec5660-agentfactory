import tkinter as tk
import random


class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Snake")
        self.root.resizable(False, False)

        self.cell = 20
        self.cols = 25
        self.rows = 25
        self.width = self.cols * self.cell
        self.height = self.rows * self.cell

        self.canvas = tk.Canvas(
            root, width=self.width, height=self.height, bg="#111111",
            highlightthickness=0
        )
        self.canvas.pack()

        self.high_score = 0
        self.tick_ms = 100
        self.after_id = None

        self.root.bind("<Key>", self.on_key)
        self.start_game()

    def start_game(self):
        center_x = self.cols // 2
        center_y = self.rows // 2
        self.snake = [(center_x, center_y), (center_x - 1, center_y), (center_x - 2, center_y)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.game_over_flag = False
        self.food = None
        self.spawn_food()

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.render()
        self.after_id = self.root.after(self.tick_ms, self.tick)

    def spawn_food(self):
        empty = [
            (x, y)
            for x in range(self.cols)
            for y in range(self.rows)
            if (x, y) not in self.snake
        ]
        self.food = random.choice(empty) if empty else None

    def on_key(self, event):
        key = event.keysym.lower() if event.keysym else ""
        if key in ("up", "w"):
            new_dir = (0, -1)
        elif key in ("down", "s"):
            new_dir = (0, 1)
        elif key in ("left", "a"):
            new_dir = (-1, 0)
        elif key in ("right", "d"):
            new_dir = (1, 0)
        elif key == "r":
            if self.game_over_flag:
                self.start_game()
            return
        else:
            return

        if self.game_over_flag:
            return

        if (new_dir[0] == -self.next_direction[0] and new_dir[1] == -self.next_direction[1]):
            return
        self.next_direction = new_dir

    def tick(self):
        self.after_id = None
        if self.game_over_flag:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if (
            new_head[0] < 0 or new_head[0] >= self.cols or
            new_head[1] < 0 or new_head[1] >= self.rows or
            new_head in self.snake[:-1]
        ):
            self.game_over()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            if self.score > self.high_score:
                self.high_score = self.score
            self.spawn_food()
        else:
            self.snake.pop()

        self.render()
        self.after_id = self.root.after(self.tick_ms, self.tick)

    def game_over(self):
        self.game_over_flag = True
        if self.score > self.high_score:
            self.high_score = self.score
        self.render()

    def render(self):
        self.canvas.delete("all")
        c = self.cell

        if self.food is not None:
            fx, fy = self.food
            self.canvas.create_oval(
                fx * c + 3, fy * c + 3, fx * c + c - 3, fy * c + c - 3,
                fill="#e74c3c", outline=""
            )

        for i, (x, y) in enumerate(self.snake):
            color = "#2ecc71" if i == 0 else "#27ae60"
            self.canvas.create_rectangle(
                x * c + 1, y * c + 1, x * c + c - 1, y * c + c - 1,
                fill=color, outline=""
            )

        self.canvas.create_text(
            60, 12, text=f"Score: {self.score}", fill="white",
            anchor="w", font=("Helvetica", 12, "bold")
        )
        self.canvas.create_text(
            self.width - 12, 12, text=f"High: {self.high_score}", fill="#f1c40f",
            anchor="e", font=("Helvetica", 12, "bold")
        )

        if self.game_over_flag:
            self.canvas.create_rectangle(
                0, 0, self.width, self.height, fill="#000000", stipple="gray50", outline=""
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2 - 20,
                text="GAME OVER", fill="#e74c3c",
                font=("Helvetica", 28, "bold")
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2 + 20,
                text=f"Score: {self.score}   High: {self.high_score}",
                fill="white", font=("Helvetica", 14)
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2 + 50,
                text="Press 'r' to restart",
                fill="#f1c40f", font=("Helvetica", 12)
            )


def main():
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()