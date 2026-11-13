import tkinter as tk
import random
import sys

class SnakeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Snake Game")
        self.root.resizable(False, False)
        
        # Constants
        self.WIDTH = 20
        self.HEIGHT = 20
        self.CELL_SIZE = 25
        self.WIN_PIXELS = self.WIDTH * self.CELL_SIZE
        self.HEIGHT_PIXELS = self.HEIGHT * self.CELL_SIZE
        
        # Canvas setup
        self.canvas = tk.Canvas(root, width=self.WIN_PIXELS, height=self.HEIGHT_PIXELS,
                                bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Score label
        self.score_label = tk.Label(root, text="Score: 0", font=("Arial", 16), fg="white", bg="black")
        self.score_label.pack()
        
        # Message label for game over/restart
        self.msg_label = tk.Label(root, text="", font=("Arial", 14), fg="yellow", bg="black")
        self.msg_label.pack()
        
        # Initialize game state
        self.reset_game()
        
        # Bind keys
        self.root.bind("<Up>", self.change_direction)
        self.root.bind("<Down>", self.change_direction)
        self.root.bind("<Left>", self.change_direction)
        self.root.bind("<Right>", self.change_direction)
        self.root.bind("<w>", self.change_direction)
        self.root.bind("<s>", self.change_direction)
        self.root.bind("<a>", self.change_direction)
        self.root.bind("<d>", self.change_direction)
        self.root.bind("<q>", self.quit_game)
        self.root.bind("<r>", self.restart_game)
        self.root.bind("<space>", self.restart_game)
        self.root.bind("<Escape>", self.quit_game)
        
        # Start game loop
        self.running = True
        self.game_speed = 150  # milliseconds per frame
        self.last_move = 0
        self.update_game()

    def reset_game(self):
        # Snake starts in the middle
        mid_x = self.WIDTH // 2
        mid_y = self.HEIGHT // 2
        self.snake = [(mid_x, mid_y)]
        self.direction = "right"
        self.next_direction = "right"
        self.score = 0
        self.game_over = False
        
        # Place food
        self.place_food()
        
        # Update score display
        self.score_label.config(text=f"Score: {self.score}")
        self.msg_label.config(text="Press arrow keys or WASD to move")
        
        # Clear canvas
        self.canvas.delete("all")
        self.draw_grid()
        self.draw_snake()
        self.draw_food()

    def draw_grid(self):
        # Draw grid lines (optional, subtle)
        for i in range(1, self.WIDTH):
            self.canvas.create_line(i * self.CELL_SIZE, 0, i * self.CELL_SIZE, self.HEIGHT_PIXELS,
                                    fill="#222222", width=1)
        for j in range(1, self.HEIGHT):
            self.canvas.create_line(0, j * self.CELL_SIZE, self.WIN_PIXELS, j * self.CELL_SIZE,
                                    fill="#222222", width=1)

    def draw_snake(self):
        for i, (x, y) in enumerate(self.snake):
            # Head is brighter
            color = "lime" if i == 0 else "green"
            self.canvas.create_rectangle(
                x * self.CELL_SIZE + 1, y * self.CELL_SIZE + 1,
                (x + 1) * self.CELL_SIZE - 1, (y + 1) * self.CELL_SIZE - 1,
                fill=color, outline="darkgreen"
            )

    def draw_food(self):
        fx, fy = self.food
        self.canvas.create_oval(
            fx * self.CELL_SIZE + 5, fy * self.CELL_SIZE + 5,
            (fx + 1) * self.CELL_SIZE - 5, (fy + 1) * self.CELL_SIZE - 5,
            fill="red", outline="darkred"
        )

    def place_food(self):
        # Get all empty cells
        snake_set = set(self.snake)
        empty_cells = [(x, y) for x in range(self.WIDTH) for y in range(self.HEIGHT) 
                       if (x, y) not in snake_set]
        if empty_cells:
            self.food = random.choice(empty_cells)
        else:
            # Snake has won (filled the board)
            self.food = (-1, -1)
            self.game_over = True
            self.msg_label.config(text="You Win! Press R to restart")

    def change_direction(self, event):
        key = event.char.lower() if event.char else event.keysym.lower()
        
        # Map keys to directions
        if key in ["up", "w"]:
            new_dir = "up"
        elif key in ["down", "s"]:
            new_dir = "down"
        elif key in ["left", "a"]:
            new_dir = "left"
        elif key in ["right", "d"]:
            new_dir = "right"
        else:
            return
        
        # Prevent reversing direction
        opposite = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left"
        }
        if new_dir != opposite[self.direction]:
            self.next_direction = new_dir

    def update_game(self):
        if not self.running:
            return
        
        if not self.game_over:
            # Move snake
            self.move_snake()
            # Check collisions
            if self.check_collision():
                self.game_over = True
                self.msg_label.config(text=f"Game Over! Score: {self.score}. Press R to restart")
            else:
                # Draw
                self.canvas.delete("snake", "food")
                self.draw_snake()
                self.draw_food()
                self.score_label.config(text=f"Score: {self.score}")
        
        # Schedule next update
        self.root.after(self.game_speed, self.update_game)

    def move_snake(self):
        self.direction = self.next_direction
        
        head_x, head_y = self.snake[0]
        
        if self.direction == "up":
            new_head = (head_x, head_y - 1)
        elif self.direction == "down":
            new_head = (head_x, head_y + 1)
        elif self.direction == "left":
            new_head = (head_x - 1, head_y)
        elif self.direction == "right":
            new_head = (head_x + 1, head_y)
        
        self.snake.insert(0, new_head)
        
        # Check if food eaten
        if new_head == self.food:
            self.score += 10
            self.place_food()
            # Remove last segment only if not eating (already inserted new head)
            # If eating, we don't remove tail
        else:
            self.snake.pop()

    def check_collision(self):
        head = self.snake[0]
        x, y = head
        
        # Wall collision
        if x < 0 or x >= self.WIDTH or y < 0 or y >= self.HEIGHT:
            return True
        
        # Self collision (check against body excluding head)
        if head in self.snake[1:]:
            return True
        
        return False

    def restart_game(self, event=None):
        self.reset_game()
        self.msg_label.config(text="Press arrow keys or WASD to move")

    def quit_game(self, event=None):
        self.running = False
        self.root.quit()
        self.root.destroy()

def main():
    root = tk.Tk()
    game = SnakeGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()