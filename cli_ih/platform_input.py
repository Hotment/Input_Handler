import sys

if sys.platform == 'win32':
    import msvcrt

    kbhit = msvcrt.kbhit
    getwch = msvcrt.getwch

else:
    import select, tty, termios

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

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            if ch == '\x1b':
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if not dr:
                    return ch
                
                try:
                    tty.setraw(sys.stdin.fileno())
                    ch2 = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                if ch2 == '[':
                    try:
                        tty.setraw(sys.stdin.fileno())
                        ch3 = sys.stdin.read(1)
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    
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
            
            if ch == '\x7f':
                return '\x08'
                
            return ch

    _unix_input = UnixInput()

    kbhit = _unix_input.kbhit
    getwch = _unix_input.getwch