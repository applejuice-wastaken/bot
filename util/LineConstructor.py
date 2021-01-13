class LineConstructor:
    def __init__(self, size, default=" "):
        self.ch = default * size

    def set(self, position, char):
        self.ch = self.ch[:position] + char + self.ch[position + 1:]

    def get(self):
        return self.ch
