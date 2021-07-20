import socket
import ssl
import tkinter
import tkinter.font

def request(url):
  scheme, url = url.split("://", 1)
  assert scheme in ["http", "https"], \
    "Unknown scheme {}".format(scheme)

  port = 80 if scheme == "http" else 443
  host, path = url.split("/", 1)
  path = "/" + path

  s = socket.socket(
      family=socket.AF_INET,
      type=socket.SOCK_STREAM,
      proto=socket.IPPROTO_TCP,
  )

  if scheme == "https":
    ctx = ssl._create_unverified_context()
    s = ctx.wrap_socket(s, server_hostname=host)

  if ":" in host:
    host, port = host.split(":", 1)
    port = int(port)


  s.connect((host, port))


  s.send(bytes("GET {} HTTP/1.0\r\n".format(path), encoding = "utf-8") +
        bytes("Host: {}\r\n\r\n".format(host), encoding="utf-8"))

  response = s.makefile("r", encoding="utf8", newline="\r\n")
  statusline = response.readline()

  version, status, explanation = statusline.split(" ", 2)
  assert status == "200", "{}: {}".format(status, explanation)

  headers = {}
  while True:
      line = response.readline()
      if line == "\r\n": break
      header, value = line.split(":", 1)
      headers[header.lower()] = value.strip()

  body = response.read()
  s.close()
  return headers, body

class Text:
  def __init__(self, text, parent):
    self.text = text
    self.children = []
    self.parent = parent
  def __repr__(self):
    return repr(self.text)

class Element:
  def __init__(self, tag, parent):
    self.tag = tag
    self.children = []
    self.parent = parent
  def __repr__(self):
    return "<" + self.tag + ">"


class HTMLParser:
  def __init__(self, body):
    self.body = body
    self.unfinished = []
    self.SELF_CLOSING_TAGS = [
      "area", "base", "br", "col", "embed", "hr", "img", "input",
      "link", "meta", "param", "source", "track", "wbr",
    ]
    self.HEAD_TAGS = [
      "base", "basefont", "bgsound", "noscript",
      "link", "meta", "title", "style", "script",
    ]

  def get_attributes(self, text):
    parts = text.split()
    tag = parts[0].lower()
    attributes = {}
    for attrpair in parts[1:]:
        if "=" in attrpair:
          key, value = attrpair.split("=", 1)
          if len(value) > 2 and value[0] in ["'", "\""]:
            value = value[1:-1]
          attributes[key.lower()] = value
        else:
          attributes[attrpair.lower()] = ""
    return tag, attributes
  def parse(self):
    text = ""
    in_tag = False
    for c in self.body:
        if c == "<":
            in_tag = True
            if text: self.add_text(text)
            text = ""
        elif c == ">":
            in_tag = False
            self.add_tag(text)
            text = ""
        else:
            text += c
    if not in_tag and text:
        self.add_text(text)
    return self.finish()

  def implicit_tags(self, tag):
        while True:
          open_tags = [node.tag for node in self.unfinished]
          if open_tags == [] and tag != 'html':
            self.add_tag("html")
          elif open_tags == ["html"] \
            and tag not in ["head", "body", "/html"]:
            if tag in self.HEAD_TAGS:
              self.add_tag("head")
            else:
              self.add_tag("body")
          elif open_tags == ["html", "head"] and \
              tag not in ["/head"] + self.HEAD_TAGS:
            self.add_tag("/head")
          else:
            break
  def add_text(self, text):
    if text.isspace(): return
    self.implicit_tags(None)
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  def add_tag(self, tag):
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"): return
    self.implicit_tags(tag)
    if tag.startswith("/"):
      if len(self.unfinished) == 1: return
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    elif tag in self.SELF_CLOSING_TAGS:
      parent = self.unfinished[-1]
      node = Element(tag, parent)
      parent.children.append(node)
    else:
      parent = self.unfinished[-1] if self.unfinished else None
      node = Element(tag, parent)
      self.unfinished.append(node)

  def finish(self):
    while len(self.unfinished) > 1:
      node = self.unfinished.pop();
      parent = self.unfinished[-1]
      parent.children.append(node)
    return self.unfinished.pop()

def print_tree(node, indent=0):
  print(" " * indent, node)
  for child in node.children:
    print_tree(child, indent + 2)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100



class Layout:
  def __init__(self, tree):
    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 16
    self.line = []
    self.recurse(tree)

  def open_tag(self, tag):
    if tag == 'i':
      self.style = "italic"
    if tag == 'b':
      self.weight = "bold"
    if tag == 'small':
      self.size -= 2
    if tag == 'big':
      self.size += 4

  def close_tag(self, tag):
    if tag == 'i':
      self.style = "roman"
    if tag =='b':
      self.weight = 'normal'
    if tag == 'small':
      self.size += 2
    if tag == 'big':
      self.size -= 4

  def recurse(self, tree):
    if isinstance(tree, Text):
      self.text(tree)
    else:
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)
  def text(self, tok):
    font = tkinter.font.Font(
        size=self.size,
        weight=self.weight,
        slant=self.style,
    )
    for word in tok.text.split():
      w = font.measure(word)
      if self.cursor_x + w >= WIDTH - HSTEP:
          self.flush()
      self.line.append((self.cursor_x, word, font))
      self.cursor_x += w + font.measure(" ")

  def flush(self):
    if not self.line: return
    metrics = [font.metrics() for x, word, font in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + 1.2 * max_ascent
    for x, word, font in self.line:
      y = baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font))
    self.cursor_x = HSTEP
    self.line = []
    max_descent = max([metric["descent"] for metric in metrics])
    self.cursor_y = baseline + 1.2 * max_descent

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.font = tkinter.font.Font(
            family="Times",
            size=16,
            weight="bold",
            slant="italic",
        )

    def scrolldown(self, e):
       self.scroll += SCROLL_STEP
       self.draw()

    def scrollup(self, e):
       self.scroll -= SCROLL_STEP
       if self.scroll <= 0:
         self.scroll = 0
       self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
          if y > self.scroll + HEIGHT: continue
          if y + VSTEP < self.scroll: continue
          self.canvas.create_text(x, y - self.scroll, text=c, font=f)
    def load(self, url):
        headers, body = request(url)
        tree = HTMLParser(body).parse()
        self.display_list = Layout(tree).display_list
        self.draw()

if __name__ == "__main__":
  import sys
  Browser().load(sys.argv[1])
  tkinter.mainloop()