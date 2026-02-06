import sys

if sys.platform == 'win32':
    import msvcrt

    class InputContext:  # pyright: ignore[reportRedeclaration]
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

    def kbhit():
        return msvcrt.kbhit()

    def getwch():
        return msvcrt.getwch()


else:
    import select, tty, termios

    class InputContext:
        def __init__(self):
            self.fd = sys.stdin.fileno()
            self.old_settings = None

        def __enter__(self):
            self.old_settings = termios.tcgetattr(self.fd)
            new_settings = termios.tcgetattr(self.fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
            termios.tcsetattr(self.fd, termios.TCSADRAIN, new_settings)
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if self.old_settings:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    class UnixInput:
        def __init__(self):
            self.buffer = []

        def kbhit(self) -> bool:
            if self.buffer:
                return True
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            return len(dr) > 0

        def getwch(self) -> str:
            if self.buffer:
                return self.buffer.pop(0)
            ch = sys.stdin.read(1)

            if ch == '\x1b':
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if not dr:
                    return ch
                
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        self.buffer.append('H')
                        return '\xe0'
                    elif ch3 == 'B':
                        self.buffer.append('P')
                        return '\xe0'
                    elif ch3 == 'C':
                        self.buffer.append('M')
                        return '\xe0'
                    elif ch3 == 'D':
                        self.buffer.append('K')
                        return '\xe0'
                    else:
                        return ch 
                else:
                    return ch

            if ch == '\n':
                return '\r'
            
            if ch == '\x7f':
                return '\x08'
                
            return ch

    _unix_input = UnixInput()

    def kbhit():
        return _unix_input.kbhit()

    def getwch():
        return _unix_input.getwch()