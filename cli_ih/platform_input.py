import sys, os


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
            self.using_raw_mode = False


        def __enter__(self):
            try:
                if os.environ.get('P_SERVER_UUID') or os.environ.get('CLI_IH_FORCE_FALLBACK'):
                    raise Exception("Forced fallback mode")

                self.old_settings = termios.tcgetattr(self.fd)
                new_settings = termios.tcgetattr(self.fd)
                new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
                termios.tcsetattr(self.fd, termios.TCSANOW, new_settings)
                self.using_raw_mode = True
            except Exception:
                self.old_settings = None
                self.using_raw_mode = False
                sys.stderr.write("[WARN] Terminal input optimization failed (non-TTY detected). Using fallback mode.\n")
                sys.stderr.flush()
                try:
                    sys.stdout.reconfigure(line_buffering=True) # type: ignore
                except AttributeError:
                    pass

            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if self.old_settings and self.using_raw_mode:
                try:
                    termios.tcsetattr(self.fd, termios.TCSANOW, self.old_settings)
                except Exception:
                    pass

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