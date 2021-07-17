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
  def __init__(self, text):
    self.text = text

class Tag:
  def __init__(self, tag):
    self.tag = tag

def lex(body):
    out = []
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_tag and text:
        out.append(Text(text))
    return out

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100



class Layout:
  def __init__(self, tokens):
    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 16
    self.line = []
    for tok in tokens:
        self.token(tok)

  def token(self, tok):
    if isinstance(tok, Text):
      self.text(tok)
    elif tok.tag == "i":
      self.style = "italic"
    elif tok.tag == "/i":
      self.style = "roman"
    elif tok.tag == "b":
      self.weight = "bold"
    elif tok.tag == "/b":
      self.weight = "normal"
    elif tok.tag == "small":
      self.size -= 2
    elif tok.tag == "/small":
      self.size += 2
    elif tok.tag == "big":
      self.size += 4
    elif tok.tag == "/big":
      self.size -= 4

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
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

if __name__ == "__main__":
  import sys
  Browser().load(sys.argv[1])
  tkinter.mainloop()