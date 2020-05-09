import argparse, pkg_resources, sys, time
import tempfile, subprocess, os, re
import pyperclip
import curses
import signal

# import socket

# global vars
screen = False
compare = ""
clips = []
selected = 0
bottom = 0
registered_keys = {}
SIGWINCH_works = False

# This has to be in a separate function for the automatic documentation to work.
def command_line_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", "-v", help="Print version number and exit.", action="store_true")
    ap.add_argument(
        "--configfile", "-c", help="Location of the klipz config file.", default="~/.klipz/config.py"
    )
    ap.add_argument("--scrollback", "-s", help="Number of clips in scrollback buffer.", type=int, default=100)
    return ap


def main():
    global cmdline
    ap = command_line_arguments()
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("klipz").version)
        sys.exit(0)

    register_default_keys()
    read_config_file()

    curses.wrapper(worker)

def register_default_keys():
    register_key("e", call_editor)
    register_key(curses.KEY_UP, up, None)
    register_key(curses.KEY_DOWN, down, None)

def read_config_file():
    try:
        exec(open(os.path.expanduser(cmdline.configfile)).read())
    except FileNotFoundError:
        pass

def worker(scr):
    global compare, clips, selected, screen
    screen = scr
    curses.use_default_colors()
    screen.timeout(0)
    screen.leaveok(0)
    redraw()
    signal.signal(signal.SIGWINCH, handle_resize)
    while True:
        while True:
            key = screen.getch()
            if key == curses.KEY_RESIZE and not SIGWINCH_works:
                handle_resize(None, None)
            for k, (func, args, clipcrlf) in registered_keys.items():
                if key == k:
                    execute_function(func, args, clipcrlf)
            if key == -1:
                break
        p = pyperclip.paste()
        if p and p != compare:
            clips.insert(0, p)
            if len(clips) >= cmdline.scrollback:
                clips.pop(-1)
            selected = 0
            compare = p
            redraw()
        else:
            time.sleep(0.1)

def execute_function(func, args, clipcrlf):
    global clips
    if args == None:
        func()
    else:
        if type(args) == str:
            args = [args]
        args.insert(0, clips[selected])
        clip = func(*args)
        if clipcrlf:
            clip = re.sub("\n$", "", clip)
        args.pop(0)
        clips[selected] = clip
        copy_to_clipboard(clip)
        redraw()

def handle_resize(signum, frame):
    global SIGWINCH_works, screen
    if signum or frame:
        SIGWINCH_works = True
    curses.endwin()
    screen = curses.initscr()
    screen.clear()
    curses.resizeterm(*screen.getmaxyx())
    bottom = max(0, selected - curses.LINES + 1)
    redraw()


def redraw():
    screen.clear()
    index = bottom
    while index < len(clips) and index < curses.LINES + bottom:
        display_string = clips[index] + " " * curses.COLS
        display_string = display_string.replace("\n", "↵")[: curses.COLS - 1]
        try:
            screen.addstr(
                curses.LINES - 1 - index + bottom,
                0,
                display_string,
                curses.A_REVERSE if index == selected else curses.A_NORMAL,
            )
        except:
            pass
#             screen.addstr(
#                 curses.LINES - 1 - index + bottom,
#                 0,
#                 "<problem displaying here>",
#                 curses.A_REVERSE if index == selected else curses.A_NORMAL,
#             )
        index += 1
    screen.move(curses.LINES - 1 - selected + bottom, 0)
    screen.refresh()


def up():
    global selected, bottom
    if selected < len(clips) - 1:
        selected += 1
        if selected >= bottom + curses.LINES:
            bottom += 1
        copy_to_clipboard(clips[selected])
        redraw()


def down():
    global selected, bottom
    if selected > 0:
        selected -= 1
        if selected < bottom:
            bottom = selected
        copy_to_clipboard(clips[selected])
        redraw()


def copy_to_clipboard(s):
    global compare
    pyperclip.copy(s)
    compare = s


def register_key(key, func=None, args=[], clipcrlf = True):
    global registered_keys
    if type(key) == str:
        key = ord(key)
    if not func:
        del registered_keys[key]
        return
    registered_keys[key] = (func, args, clipcrlf)


def pass_as_tempfile(clip, command_and_args):
    global screen
    curses.endwin()
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        command_and_args.append(tf.name)
        tf.write(clip.encode("utf-8"))
        tf.flush()
        subprocess.call(command_and_args)
        tf.seek(0)
        clip = tf.read().decode("utf-8")
    screen = curses.initscr()
    return clip

def pipe_through(clip, command_and_args):
    if type(command_and_args) == str:
        command_and_args = [command_and_args]
    p = subprocess.Popen(command_and_args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    return p.communicate(input=clip.encode("utf-8"))[0].decode("utf-8")

def call_editor(clip):
    editor = os.environ.get("EDITOR", None)
    if editor:
        clip = pass_as_tempfile(clip, [editor])
    return clip


# For later
def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, "ascii"))
        response = str(sock.recv(1024), "ascii")
        print("Received: {}".format(response))


if __name__ == "__main__":
    main()
