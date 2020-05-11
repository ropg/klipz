import argparse, pkg_resources, sys, time
import tempfile, subprocess, os, re, ast
import pyperclip
import curses
import signal

# import socket

# consts
SAVED_HEADER = "Saved Clippings"

# global vars
screen = False
width = 0
compare = ""
pastes = []
saved_clips = [ "" ]
clips = pastes
selected = 0
bottom = 0
has_upped = False
offset_in_clip = 0
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
    saved_from_disk()
    curses.wrapper(worker)

def register_default_keys():
    register_key("e", call_editor)
    register_key("s", toggle_saved, None)
    register_key("u", move_up, None)
    register_key("d", move_down, None)
    register_key(curses.KEY_UP, up, None)
    register_key(curses.KEY_DOWN, down, None)
    register_key(curses.KEY_LEFT, scroll_left, None)
    register_key(curses.KEY_RIGHT, scroll_right, None)

def read_config_file():
    try:
        exec(open(os.path.expanduser(cmdline.configfile)).read())
    except FileNotFoundError:
        pass

def saved_to_disk():
    try:
        os.mkdir (os.path.expanduser('~/.klipz'))
    except FileExistsError:
        pass
    try:
        with open(os.path.expanduser('~/.klipz/saved_clips'), 'wb') as f:
            f.write(repr(saved_clips).encode("utf-8"))
    except:
        pass

def saved_from_disk():
    global saved_clips
    try:
        with open(os.path.expanduser('~/.klipz/saved_clips'), 'rb') as f:
            del saved_clips[:]
            saved_clips.extend(ast.literal_eval(f.read().decode("utf-8")))
    except:
        pass

def worker(scr):
    global compare, clips, selected, screen
    screen = scr
    curses.use_default_colors()
    screen.timeout(0)
    redraw()
    signal.signal(signal.SIGWINCH, handle_resize)
    while True:
        while True:
            key = screen.getch()
            if key == curses.KEY_RESIZE and not SIGWINCH_works:
                handle_resize(None, None)
            if key == -1:
                break
            execute_function(registered_keys.get(key))
        p = pyperclip.paste()
        if p and p != compare:
            if clips is saved_clips:
                toggle_saved()
            pastes.insert(0, p)
            if len(pastes) >= cmdline.scrollback:
                pastes.pop(-1)
            selected = 0
            compare = p
            redraw()
        else:
            time.sleep(0.1)

def execute_function(tuple):
    global clips
    if not tuple:
        return
    (func, args, cutcrlf) = tuple
    if args == None:
        func()
    else:
        if type(args) == str:
            args = [args]
        args.insert(0, clips[selected])
        clip = func(*args)
        clip = re.sub("\n$", "", clip) if cutcrlf else clip
        args.pop(0)
        clips[selected] = clip
        copy_to_clipboard(clip)
        offset_in_clip = 0
        redraw()

def handle_resize(signum, frame):
    global SIGWINCH_works, screen, bottom
    if signum or frame:
        SIGWINCH_works = True
    curses.endwin()
    screen = curses.initscr()
    screen.clear()
    curses.resizeterm(*screen.getmaxyx())
    bottom = max(0, selected - curses.LINES + 1)
    offset_in_clip = 0
    redraw()

def redraw():
    global width
    screen.clear()
    width = curses.COLS - 1
    index = curses.LINES + bottom
    if clips is saved_clips:
        screen.addstr(0, 0, " " * width, curses.A_REVERSE)
        screen.addstr(0, int((width / 2) - (len(SAVED_HEADER) / 2)), SAVED_HEADER, curses.A_REVERSE)
        index -= 1
    while index > bottom:
        index -= 1
        if index >= len(clips):
            continue
        disp = clips[index].replace("\n", "↵")
        current_line = curses.LINES - 1 - index + bottom
        cursor_state = curses.A_NORMAL
        if index == selected:
            disp = disp[offset_in_clip:]
            cursor_state = curses.A_REVERSE
            screen.addnstr(current_line, 0, " " * width, width, cursor_state)
        try:
            # May throw exception and even wrap ugly on non-fixed-width chars (e.g. emoticons).
            # Since we do not control terminal or font there is simply nothing we can do about it.
            screen.addnstr(current_line, 0, disp, width, cursor_state)
        except:
            raise
    screen.move(curses.LINES - 1 - selected + bottom, 0)
    screen.refresh()

def up():
    global selected, bottom, offset_in_clip
    if selected < len(clips) - 1:
        selected += 1
        top = bottom + curses.LINES
        if clips is saved_clips:
            top -= 1
        if selected >= top:
            bottom += 1
        copy_to_clipboard(clips[selected])
        offset_in_clip = 0
        redraw()

def down():
    global selected, bottom, offset_in_clip
    if selected > 0:
        selected -= 1
        if selected < bottom:
            bottom = selected
        copy_to_clipboard(clips[selected])
        offset_in_clip = 0
        redraw()

def scroll_left():
    global offset_in_clip
    offset_in_clip -= width
    offset_in_clip = max(0, offset_in_clip)
    redraw()

def scroll_right():
    global offset_in_clip
    offset_in_clip += width
    offset_in_clip = min(len(clips[selected]) - width, offset_in_clip)
    offset_in_clip = max(0, offset_in_clip)
    redraw()

def move_down():
    global selected
    if clips is pastes:
        return
    if selected > 0:
        saved_clips[selected - 1], saved_clips[selected] = saved_clips[selected], saved_clips[selected - 1]
        selected -= 1
        redraw()

def move_up():
    global has_upped, selected
    if clips is pastes:
        return
    if selected == 0 and not has_upped:
        has_upped = True
        saved_clips.insert(0, "")
        selected = 1
        redraw()
    elif selected < len(saved_clips) - 1:
        saved_clips[selected + 1], saved_clips[selected] = saved_clips[selected], saved_clips[selected + 1]
        selected += 1
        redraw()

def toggle_saved():
    global selected, bottom, has_upped, offset_in_clip, clips
    if clips is saved_clips:
        saved_to_disk()
        clips = pastes
    else:
        clips = saved_clips
        has_upped = False
        saved_clips[0] = pastes[selected]
    selected = 0
    offset_in_clip = 0
    bottom = 0
    redraw()

def copy_to_clipboard(s):
    global compare
    pyperclip.copy(s)
    compare = s

def register_key(key, func=None, args=[], cutcrlf = True):
    global registered_keys
    if type(key) == str:
        key = ord(key)
    if not func:
        del registered_keys[key]
        return
    registered_keys[key] = (func, args, cutcrlf)

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
