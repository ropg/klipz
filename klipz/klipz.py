import argparse, pkg_resources, sys, time
import tempfile, subprocess, os, re
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
    global cmdline
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("klipz").version)
        sys.exit(0)

    curses.wrapper(worker)

def worker(screen):

    doing_signals = False
    curses.use_default_colors()
    screen.timeout(0)
    screen.leaveok(0)
    clips = []
    selected = 0
    compare = ""

    def handle_resize(signum, frame):
        nonlocal doing_signals
        if signum or frame:
            doing_signals = True
        curses.endwin()
        screen = curses.initscr()
        screen.clear()
        curses.resizeterm(*screen.getmaxyx())
        redraw()

    signal.signal(signal.SIGWINCH, handle_resize)

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
                curses.A_REVERSE if index == selected else curses.A_NORMAL
            )
            index += 1
        screen.move(curses.LINES - 1 - selected, 0)
        screen.refresh()

    def copy_to_clipboard(s):
        pyperclip.copy(s)
        nonlocal compare
        compare = s

    def up():
        nonlocal selected, clips
        if selected < len(clips) - 1:
            selected += 1
            copy_to_clipboard(clips[selected])
            redraw()

    def down():
        nonlocal selected, clips
        if selected > 0:
            selected -= 1
            copy_to_clipboard(clips[selected])
            redraw()

    redraw()
    while True:
        while True:
            key = screen.getch()
            if key == curses.KEY_RESIZE and not doing_signals:
                handle_resize(None, None)
            if key == curses.KEY_UP:
                up()
            if key == curses.KEY_DOWN:
                down()
            if key == ord("e"):
                editor = os.environ.get('EDITOR', None)
                if editor:
                    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
                        tf.write(clips[selected].encode("utf-8"))
                        tf.flush()
                        subprocess.call([editor, tf.name])
                        tf.seek(0)
                        clips[selected] = tf.read().decode("utf-8")
                        copy_to_clipboard(clips[selected])
                        handle_resize(None, None)
            if key == ord("n"):
                s = clips[selected]
                s = re.sub('[«»„“‟”❝❞⹂〝〞〟＂]', '"', s)
                s = re.sub('[‹›’‚‘‛❛❜❟]', "'", s)
                s = s.replace('—', '-')
                s = s.replace('\n', '  ')
                clips[selected] = s
                copy_to_clipboard(s)
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
