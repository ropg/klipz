# klipz - multi-platform clipboard manager using curses

[![PyPI version](https://img.shields.io/pypi/v/klipz.svg)](https://pypi.python.org/pypi/klipz/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/klipz.svg)](https://pypi.python.org/pypi/klipz/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/ropg/klipz/blob/master/LICENSE)

`klipz` is a simple tool to scroll back in your computer's clipboard. Every time you copy something to the clipboard it appears on the bottom line of the klipz main window, scrolling up the previous clippings. You can scroll back in that window to reload one of your older clippings to the clipboard. There's also a separate screen with saved clippings for things that you want to not scroll away. You can edit your clippings in your favorite editor and there's a config file that lets you configure custom actions.

## Installation

klipz is a python package on [PyPI](https://pypi.org/project/klipz), so if you have python 3 installing is easy: 

```bash
pip install klipz
```

Alternatively, you can clone the github repository and install from there:

```bash
git clone https://github.com/ropg/klipz
cd klipz
pip install .
```

## Using klipz

### Scrolling back in clipboard

On the command line, enter `klipz`. Your terminal window now goes blank except the bottom line shows the current contents of the clipboard on a line that shows as a bar with foreground and background colors swapped (so white on black if your terminal window is black on white). klipz uses one line per clipping so it may not show the whole clipboard. Use the left and right arrows to see the rest.

At this point you probably want to shrink the terminal window to something like 10 lines by 60 characters and set the font a little smaller (using *Ctrl - minus* or *⌘ - minus* in many cases). Simply put the window in the bottom corner of your screen and copy a few more text clippings from a webpage or somewhere else. As you can see the past clippings scroll up.

To reload a previous clipping, activate the window by clicking on it and scroll up using the up arrow key. If you go back to another application and paste, you'll see that the contents of the clipboard have been replaced to match the selection in klipz.

### Saved Clippings

By pressing the 's' key, you switch back and forth between the "Saved Clippings" screen and the scrolling clipboard screen you've seen before. The clip you had selected in the clipboard screen will appear on the bottom line of the "Saved Clippings" screen, but is not yet saved. Only the lines above the bottom one are actually saved. You can move your line up by pressing 'u', now the clipping is actually saved. If you keep pressing 'u' it will move further up, swapping with the line above it and pressing 'd' will move a line down the list. Pressing 'c' will clear (delete) a clipping from the list. Deleting clippings also works in the clipboard view mode, just in case you copied something embarrassing.

Saved clippings are saved to disk, so they will reappear when you start klipz again. (By default, this happens in a file called `saved_clippings` in the `.klipz` directory in your home directory that klipz creates.)

### Some things to know

* klipz does not deal with copied pictures or anything that is not text. Emoji work fine as they are unicode "text", but no pictures. You can copy and paste everything else just fine, it will just now show up in klipz.

* klipz will remove any beginning and ending carriage returns and linefeeds from all clippings. Because really, those are just annoying. If you don't want this, start with `klipz --leavecrlf`.

* If you have the `EDITOR` environment variable set to your favorite editor, you can press 'e' on a clipping.

* On MacOS, you can leave your cursor wherever you are typing, move the mouse pointer to the clips window and scroll with two fingers on the trackpad to move the cursor. No need to click to bring the klipz window in focus.

### Configuration

klipz has a few command line options

```
$ klipz -h
usage: klipz [-h] [--version] [--configdir CONFIGDIR] [--leavecrlf]
             [--buffersize BUFFERSIZE]

optional arguments:
  -h, --help            show this help message and exit
  --version, -v         Print version number and exit.
  --configdir CONFIGDIR, -c CONFIGDIR
                        By default, .klipz expects its config.py in ~/.klipz,
                        but this can be set with this option. This is also
                        where the saved_clips file is stored.
  --leavecrlf, -l       By default, klipz removes beginning and ending
                        carriage returns and line feeds from the all clips.
                        Use this option if you do not want that.
  --buffersize BUFFERSIZE, -b BUFFERSIZE
                        Number of clips in scrollback buffer. By default,
                        klipz will show up to 100 clippings.
```

klipz can be further configured with a file called `config.py` and placed in the config directory, (default `~/.klipz`). Here's what my `config.py` contains:

```py
def normalize(s):
    s = re.sub('[«»„“‟”❝❞〝〞〟＂]', '"', s)
    s = re.sub('[‹›’‚‘‛❛❜]', "'", s)
    s = re.sub('[—–]', '-', s)
    s = s \
      .replace('…', '...') \
      .replace('\n', '  ')
    return s

register_key("n", normalize)
register_key("S", pipe_through, "sort | uniq")
```

As you can see you can write regular python here. The function `normalize` does something that I need frequently: it removes all the funny unicode opening and closing quotes and replaces them by either a single or a double straight quote, while also removing any newlines and replacing them with two spaces, hyphens become minus signs and elipsis become three periods. The function takes a string and returns the modified version.

`register_key` takes as arguments the keystroke, the function that is called with the supplied arguments. The current clipping is inserted as the first argument before any of the ones supplied and the return value replaces the clipping. If you pass `None` as arguments, klipz will simply call the specified function without any arguments and the return value will be ignored. If you pass `None` as function, that mapping for the specified key is deleted.

Keystrokes can be specified a one character string such as 'x' (or 'X' for Shift-X) or special values starting with `curses.`, followed by one of the Key Constants listed [here](https://docs.python.org/3/library/curses.html#constants). So `curses.KEY_HOME` would be used to tie an action to the `Home` key.

As you can see the Shift-S combination uses a built-in function called `pipe_through` which will pipe the contents of the selected clipping through the commands specified and put the result back in the clipping. There is also a function called `pass_as_tempfile`. It is also used internally to start the editor when you press 'e', and will add the name of the temporary file as the last argument. 
