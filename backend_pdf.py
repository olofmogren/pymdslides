from fpdf import FPDF
import os

class backend_pdf:
  def __init__(self, input_file, formatting, script_home):
    self.pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height']))
    self.pdf.set_font('Helvetica', '', formatting['dimensions']['font_size_standard'])
    if 'fonts' in formatting:
      print(formatting['fonts'])
      if formatting['fonts']['font_file_standard']:
        fname = formatting['fonts']['font_file_standard']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_standard', '', fname)
        self.pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
      if formatting['fonts']['font_file_standard_italic']:
        fname = formatting['fonts']['font_file_standard_italic']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_standard', 'i', fname)
      if formatting['fonts']['font_file_standard_bold']:
        fname = formatting['fonts']['font_file_standard_bold']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_standard', 'b', fname)
      if formatting['fonts']['font_file_standard_bolditalic']:
        fname = formatting['fonts']['font_file_standard_bolditalic']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_standard', 'bi', fname)
      if formatting['fonts']['font_file_footer']:
        fname = formatting['fonts']['font_file_footer']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_footer', '', fname)
      if formatting['fonts']['font_file_title']:
        fname = formatting['fonts']['font_file_title']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        self.pdf.add_font('font_title', '', fname)
    self.pdf.set_text_color(0,0,0)
    #self.pdf.set_image_filter("FlatDecode")
    self.pdf.oversized_images = "DOWNSCALE"
    print('{}: self.pdf.oversized_images_ratio {}'.format(input_file, self.pdf.oversized_images_ratio))

    self.input_file_name = input_file
    #self.x = formatting['dimensions']['page_margins']['x0']
    #self.y = formatting['dimensions']['page_margins']['y0']
    self.pages_count = 0

  def unbreakable(self):
    return self.pdf.unbreakable()

  def local_context(self, *args, **kwargs):
    return self.pdf.local_context(*args, **kwargs)

  def add_page(self):
    self.pages_count += 1
    return self.pdf.add_page()

  def set_title(self, *args, **kwargs):
    return self.pdf.set_title(*args, **kwargs)

  def set_producer(self, *args, **kwargs):
    return self.pdf.set_producer(*args, **kwargs)

  def set_creator(self, *args, **kwargs):
    return self.pdf.set_creator(*args, **kwargs)

  def set_creation_date(self, *args, **kwargs):
    return self.pdf.set_creation_date(*args, **kwargs)

  def set_text_color(self, color):
    return self.pdf.set_text_color(color)

  def set_draw_color(self, color):
    return self.pdf.set_draw_color(color)

  def set_fill_color(self, color):
    return self.pdf.set_fill_color(color)

  def set_font(self, *args, **kwargs):
    return self.pdf.set_font(*args, **kwargs)

  def set_font_size(self, size):
    return self.pdf.set_font(size)

  def get_string_width(self, text):
    return self.pdf.get_string_width(text)

  def rect(self, *args, **kwargs):
    return self.pdf.rect(*args, **kwargs)

  def text(self, *args, **kwargs):
    return self.pdf.text(*args, **kwargs)

  def add_link(self, *args, **kwargs):
    return self.pdf.add_link(*args, **kwargs)

  def cell(self, *args, **kwargs):
    return self.pdf.cell(*args, **kwargs)

  def line(self, *args, **kwargs):
    return self.pdf.line(*args, **kwargs)

  def table(self, *args, **kwargs):
    return self.pdf.table(*args, **kwargs)

  def set_line_width(self, *args, **kwargs):
    return self.pdf.set_line_width(*args, **kwargs)

  def will_page_break(self, *args, **kwargs):
    return self.pdf.will_page_break(*args, **kwargs)

  def image(self, *args, **kwargs):
    return self.pdf.image(*args, **kwargs)

  def rasterize(self, *args, **kwargs):
    return self.pdf.rasterize(*args, **kwargs)

  def rect_clip(self, *args, **kwargs):
    return self.pdf.rect_clip(*args, **kwargs)

  def get_x(self):
    return self.pdf.get_x()

  def get_y(self):
    return self.pdf.get_y()

  def draw_svg_image(self, svg_file):
    svg = self.svg.SVGObject.from_file(svg_file)

    # We pass align_viewbox=False because we want to perform positioning manually
    # after the size transform has been computed.
    width, height, paths = svg.transform_to_page_viewport(pdf, align_viewbox=False)
    # note: transformation order is important! This centers the svg drawing at the
    # origin, rotates it 90 degrees clockwise, and then repositions it to the
    # middle of the output page.
    paths.transform = paths.transform @ fpdf.drawing.Transform.translation(
        -width / 2, -height / 2
    ).rotate_d(90).translate(backend.w / 2, backend.h / 2)

    self.draw_path(paths)

  def set_xy(self, x, y):
    #self.x = x
    #self.y = y
    return self.pdf.set_xy(x,y)

  def output(self, *args, **kwargs):
    return self.pdf.output(*args, **kwargs)

