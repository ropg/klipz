import argparse, pkg_resources, sys, time
import pyperclip
import curses
import signal
# import socket

def command_line_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", "-v", help="Print version number and exit.", action="store_true")
    return ap

def main():
    ap = command_line_arguments()
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("klipz").version)
        sys.exit(0)

    curses.wrapper(worker)

def worker(screen):

    doing_signals = False

    def handle_resize(signum, frame):
        nonlocal doing_signals
        curses.endwin()
        screen = curses.initscr()
        screen.clear()
        curses.resizeterm(*screen.getmaxyx())
        redraw()

    def redraw():
        screen.clear()
        index = 0
        while index < len(clips) and index < curses.LINES:
            display_string = clips[index] + " " * curses.COLS
            display_string = display_string.replace("\n", "\\n")[:curses.COLS - 1]
            screen.addstr(
                curses.LINES - 1 - index,
                0,
                display_string,
                curses.A_NORMAL if index != selected else curses.A_REVERSE
            )
            index += 1
        screen.move(curses.LINES - 1 - selected, 0)
        screen.refresh()

    def copy_to_clipboard(s):
        pyperclip.copy(s)
        nonlocal compare
        compare = s

    signal.signal(signal.SIGWINCH, handle_resize)
    curses.use_default_colors()
    screen.timeout(0)
    screen.leaveok(0)
    clips = []
    selected = 0
    compare = ""

    redraw()
    while True:
        while True:
            key = screen.getch()
            if key == curses.KEY_RESIZE and not doing_signals:
                handle_resize(None, None)
            if key == curses.KEY_UP and selected < len(clips) - 1:
                selected += 1
                copy_to_clipboard(clips[selected])
                redraw()
            if key == curses.KEY_DOWN and selected > 0:
                selected -= 1
                copy_to_clipboard(clips[selected])
                redraw()
            if key == -1:
                break
        time.sleep(0.1)
        p = pyperclip.paste()
        if p and p != compare:
            clips.insert(0, p)
            selected = 0
            compare = p
            redraw()

# For later
def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Received: {}".format(response))

if __name__ == "__main__":
    main()
