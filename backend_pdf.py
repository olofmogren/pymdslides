# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>. 


from fpdf import FPDF
from PIL import Image, ImageOps

import os, time, shutil, re
import numpy as np
from markdown_it import MarkdownIt
import cairosvg
from mdit_plain.renderer import RendererPlain
from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw.pagemerge import RectXObj
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import rcParams
rcParams['text.usetex'] = True

pixel_per_mm = .15
treat_as_raster_images = []

class backend_pdf:
  def __init__(self, input_file, formatting, script_home, output_file):
    self.pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height']))
    self.pdf.set_font('Helvetica', '', formatting['dimensions']['font_size_standard'])
    if 'fonts' in formatting:
      print(formatting['fonts'])
      if formatting['fonts']['font_file_standard']:
        fname = formatting['fonts']['font_file_standard']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(','font_standard', '', fname, ')')
        self.pdf.add_font('standard', '', fname)
        self.pdf.set_font('standard', '', formatting['dimensions']['font_size_standard'])
      if formatting['fonts']['font_file_standard_italic']:
        fname = formatting['fonts']['font_file_standard_italic']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(standard, i',fname,')')
        self.pdf.add_font('standard', 'i', fname)
      if formatting['fonts']['font_file_standard_bold']:
        fname = formatting['fonts']['font_file_standard_bold']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(standard, b',fname,')')
        self.pdf.add_font('standard', 'b', fname)
      if formatting['fonts']['font_file_standard_bolditalic']:
        fname = formatting['fonts']['font_file_standard_bolditalic']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(standard, bi',fname,')')
        self.pdf.add_font('standard', 'bi', fname)
      if formatting['fonts']['font_file_footer']:
        fname = formatting['fonts']['font_file_footer']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(footer',fname,')')
        self.pdf.add_font('footer', '', fname)
      if formatting['fonts']['font_file_title']:
        fname = formatting['fonts']['font_file_title']
        if os.path.exists(os.path.join(script_home, fname)):
          fname = os.path.join(script_home, fname)
        print('self.pdf.add_font(title',fname,')')
        self.pdf.add_font('title', '', fname)
        self.pdf.add_font('title', 'b', fname)
        self.pdf.add_font('title', 'i', fname)
        self.pdf.add_font('title', 'bi', fname)
    self.pdf.set_text_color(0,0,0)
    #self.pdf.set_image_filter("FlatDecode")
    self.pdf.oversized_images = "DOWNSCALE"
    print('{}: self.pdf.oversized_images_ratio {}'.format(input_file, self.pdf.oversized_images_ratio))

    self.input_file_name = input_file
    #self.x = formatting['dimensions']['page_margins']['x0']
    #self.y = formatting['dimensions']['page_margins']['y0']
    self.pages_count = 0
    self.formatting = formatting
    self.vector_graphics = {}
    self.logo_path = None
    self.page_width = formatting['dimensions']['page_width']
    self.page_height = formatting['dimensions']['page_height']

  def set_logo(self, logo):
    self.logo_path = logo

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

  def set_background_color(self, color):
    self.pdf.set_fill_color(color)
    return self.pdf.rect(x=0, y=0, w=self.formatting['dimensions']['page_width'], h=self.formatting['dimensions']['page_height'], style='F')

  def rect(self, *args, **kwargs):
    return self.pdf.rect(*args, **kwargs)

  def textbox(self, lines, x, y, w, h, headlines, text_color, h_level=None, align='left', markdown_format=True, *args, **kwargs):
    if len(lines) == 0:
      return x,y
    offsets = {'x0': x, 'y0': y, 'x1': x+w, 'y1': y+h, 'w': w, 'h': h}
    current_table = []

    if h_level is not None:
      # CENTERING:
      txt = lines[0]
      if align == 'center':
        width = self.pdf.get_string_width(txt)
        centering_offset = round((offsets['w']-width)/2)
        #print('subtitle','"{}"'.format(subtitle))
        #print('subtitle_width',width,'x',x,'centering_offset',centering_offset)
        #print('offsets', offsets)
        x = x+centering_offset
      self.pdf.set_xy(x,y)
      return self.pdf.text(txt=txt, x=x, y=y+h, *args, **kwargs)
    else:
      for line in lines:
        if len(line) > 1 and line[0] == '|' and line[-1] == '|':
          print('{}:{}:detected table {}'.format(md_file_stripped, line_number, line))
          current_table.append(line[1:-1].split('|'))
          continue
        elif(len(current_table)):
          print('{}:{}: rendering table'.format(md_file_stripped, line_number))
          x , y = self.render_table(current_table, x, y, offsets, headlines, text_color)
          current_table = []
        x, y = self.position_and_render_text_line(line, x, y, offsets, headlines, text_color, align, column_divider=False)
      if(len(current_table)):
        print('{}:{}: rendering table'.format(md_file_stripped, line_number))
        x , y = self.render_table(current_table, x, y, offsets, headlines, text_color)
        current_table = []
      #if 'footer' in formatting:
      #  self.pdf.set_text_color(formatting.get('footer_color', default_footer_color))
      #  if 'fonts' in formatting and 'font_file_footer' in formatting['fonts']:
      #    self.pdf.set_font('font_footer', '', formatting['dimensions']['font_size_footer'])
      #  else:
      #    self.pdf.set_font_size(formatting['dimensions']['font_size_footer'])
      #  #x = formatting['dimensions']['page_width']//2-self.pdf.get_string_width(formatting['footer'])//2
      #  x = formatting['dimensions']['margin_footer']
      #  self.pdf.text(txt=formatting['footer'], x=x, y=formatting['dimensions']['page_height']-formatting['dimensions']['margin_footer'], em=formatting['dimensions']['em_footer']) #, w=offsets['w'], align='L')
      #  self.pdf.set_text_color(text_color)
      if(len(current_table)):
        print('{}: {}: rendering table'.format(md_file_stripped, line_number))
        x, y = self.render_table(current_table, x, y, offsets, headlines, text_color)
        current_table = []
    return x, y+h

  def l4_box(self, lines, x, y, w, h, headlines, align='left', border_color=[0,0,0], border_opacity=0.75, background_color=[255,255,255], background_opacity=0.75, markdown_format=True, text_color=[0,0,0]):
    offsets = {'x0': x, 'y0': y, 'x1': x+w, 'y1': y+h, 'w': w, 'h': h}
    self.pdf.set_draw_color(border_color)
    self.pdf.set_fill_color(background_color)

    with self.pdf.local_context(fill_opacity=background_opacity, stroke_opacity=border_opacity):
      self.pdf.rect(x, y, w, h, round_corners=True, style="DF", corner_radius=10)
    #print('self.pdf.rect(',box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], 'round_corners=True', 'style="D"',')')
    x_line = x+10 # internal_margin.
    y_line = y+10 # internal_margin.
    for line in lines:
      x, y = self.position_and_render_text_line(line, x_line, y_line, offsets, headlines, text_color, align, column_divider=False)
    return x, y+h


  def render_part_of_line(self, part, x, y):
    #print('part', '"'+part+'"')
    #if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    #  self.pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
    #else:
    #  self.pdf.set_font_size(formatting['dimensions']['font_size_standard'])
    self.pdf.set_xy(x,y)
    part = part.replace('&nbsp;', ' ')
    if not part.strip():
      self.pdf.text(txt=part, x=x, y=y) #, em=formatting['dimensions']['em'])#, w=offsets['w'], align=align)
    else:
      #print(part)
      self.pdf.cell(txt=part, markdown=True)
    x = self.pdf.get_x()
    return x, y

  def position_and_render_text_line(self, line, x, y, offsets, headlines, text_color, align='left', column_divider=False):
    origin_x = x
    if align == 'center':
      # CENTERING LINE:
      width = self.get_text_line_width(line, x, y, offsets, headlines, text_color, column_divider)
      #print('centering',offsets)
      centering_offset = round((offsets['w']-width)/2)
      print('line','"{}"'.format(line))
      print('line width',width,'x',x,'centering_offset',centering_offset)
      print('offsets', offsets)
      x = x+centering_offset
    x, y, width = self.render_text_line(line, x, y, offsets, headlines, text_color, align, column_divider)
    x = origin_x
    return x, y

  def render_text_line(self, line, x, y, offsets, headlines, text_color, align='left', column_divider=False):
    #print('line:',line)
    origin_x = x
    origin_y = y
    #print(offsets)
    width = offsets['w']
    self.pdf.set_xy(x,y)
    em = 10
    if self.pdf.will_page_break(em):
      print('line will overflow the page. not including in PDF!!!',line)
      return x,y,0
    if line.startswith('###') and (len(line) <= 3 or line[3] != '#'):
        line = '**'+line[4:]+'**'
    latex_sections = self.get_latex_sections(line)
    internal_links = self.get_internal_links(line)
    merged = latex_sections+internal_links
    merged = sorted(merged, key=lambda x: x[0])
    #print(latex_sections)
    heights = []
    #if len(line) > 0 and line[0] == '$' and line[-1] == '$':
    if len(line) == 0:
      #print('empty line!')
      y += int(0.5*em)
    elif len(line) > 3 and all([c == '-' for c in line]):
      self.pdf.set_line_width(0.5)
      # TODO: configuration of column divider line color
      self.pdf.set_draw_color([160,160,160])
      if column_divider:
        x = offsets['x0']-10//2 # internal_margin TODO!!!
        self.pdf.line(x1=x, y1=offsets['y0'], x2=x, y2=offsets['y1'])
      else:
        self.pdf.line(x1=x, y1=y+int(0.5*em), x2=x+offsets['w'], y2=y+int(0.5*em))
      y +=em 
      if column_divider:
        y = origin_y
      self.pdf.set_draw_color(text_color)
    else:
      pos = 0
      for tag in merged:
        if tag[0] > pos:
          pre_tag = line[pos:tag[0]-1]
          #print('rendering pre_tag', pre_tag)
          x, new_y = self.render_part_of_line(pre_tag, x, y)
          heights.append(em)
        if tag[2] == 'latex':
          formula = line[tag[0]:tag[1]]
          x, new_y, latex_width = self.render_latex(formula, x, y, text_color)
          heights.append(new_y-origin_y)
        else: # internal link
          #print('line', line)
          #print('tag', tag)
          link = line[tag[0]:tag[1]+1]
          #print('link',link)
          x, new_y = self.render_internal_link(link, x, y, headlines)
          heights.append(new_y-origin_y)
        pos = tag[1]+1
      if pos < len(line):
        x, new_y = self.render_part_of_line(line[pos:], x, y)
        heights.append(em)
        heights.append(new_y-origin_y)
      y = origin_y + max(heights)
      width = x-origin_x
      #print('y', origin_y, y)
    return origin_x, y, width

  def render_table(self, table, x, y, offsets, headlines, text_color, column_divider=False):
    print('table:',table)
    origin_x = x
    origin_y = y
    #if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    #  self.pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
    #else:
    #  self.pdf.set_font_size(formatting['dimensions']['font_size_standard'])
    # due to a bug (in my code or in pfpdf), the table is centered on the page. uncentering:
    uncentered_x = x-(formatting['dimensions']['page_width']//2-offsets['w']//2)
    self.pdf.set_xy(uncentered_x,y)
    self.pdf.set_xy(0,y)
    self.pdf.set_left_margin(offsets['x0'])
    with self.pdf.table(width=offsets['w'], align='LEFT', markdown=True) as pdf_table:
      for tr in table:
        row = pdf_table.row()
        for td in tr:
          row.cell(td)
    y += int(formatting['dimensions']['em']*len(table)*1.8)
    return origin_x, y

  def get_text_line_width(self, line, x, y, offsets, headlines, text_color, column_divider=False):
    #print(offsets)
    #print('line', line, len(line))
    width = offsets['w']
    #if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    #  self.pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
    #else:
    #  self.pdf.set_font_size(formatting['dimensions']['font_size_standard'])
    em = 10
    if self.pdf.will_page_break(em):
      print('line will overflow the page. not including in PDF!!!',line)
      return width
    if line.startswith('###') and (len(line) <= 3 or line[3] != '#'):
        line = '**'+line[4:]+'**'
    latex_sections = self.get_latex_sections(line)
    internal_links = self.get_internal_links(line)
    merged = latex_sections+internal_links
    merged = sorted(merged, key=lambda x: x[0])
    if len(line) == 0:
      return width
    elif len(line) > 3 and all([c == '-' for c in line]):
      return width
    else:
      new_widths = []
      pos = 0
      for tag in merged:
        if tag[0] > pos:
          pre_tag = line[pos:tag[0]-1]
          new_widths.append(self.pdf.get_string_width(markdown_to_text(pre_tag)))
          #print('pretag width',new_widths[-1],'('+pre_tag+')')
        if tag[2] == 'latex':
          formula = line[tag[0]:tag[1]]
          x, new_y, latex_width = self.render_latex(formula, x, y, text_color, dry_run=True)
          new_widths.append(latex_width)
          #print('latex width',new_widths[-1],'('+formula+')')
        else: # internal link
          link = line[tag[0]:tag[1]+1]
          splitted = link.split('](#')
          link_text = splitted[0][1:]
          new_widths.append(self.pdf.get_string_width(link_text))
          #print('link width',new_widths[-1],'('+link_text+')')
        pos = tag[1]+1
      if pos < len(line):
        new_widths.append(self.pdf.get_string_width(markdown_to_text(line[pos:])))
        #print('last part width',new_widths[-1],'('+line[pos:]+')')
    #print('sum',sum(new_widths))
    return sum(new_widths)

  def get_latex_sections(self, line):
    latex_formulas = []
    if '$' in line:
      splits = re.split(r'(?<!\\)\$', line)
      pos = 0
      for i,split in enumerate(splits):
        if i%2 == 1:
          latex_formulas.append((pos,pos+len(split), 'latex'))
        pos += len(split)+1 # one for the dollar sign
    return latex_formulas

  def get_internal_links(self, line):
    internal_links = []
    if '](#' in line:
      locations = find_all(line, '](#')
      #print('line', line)
      #@locations = [l for l in locations] # I HAVE NO IDEA WHY THIS IS NEEDED!
      #print(locations)
      for l in locations:
        #print(l)
        beginning = line.rfind('[', 0, l)
        end = line.find(')', l)
        #print('beginning, end', beginning, end)
        if beginning != -1 and end != -1:
          internal_links.append((beginning,end,'link'))
    return internal_links

  def render_latex(self, formula, x, y, text_color, dry_run=False):
    return self.render_latex_matplotlib(formula, x, y, text_color, dry_run=dry_run)

  def render_latex_matplotlib(self, formula, x, y, text_color, dry_run=False):
    formula = '$base~'+formula+'$'
    #print('formula', formula)
    # Latex!
    fig = plt.figure(frameon=False)
    #fig.text(0.0, 0.0, line, fontsize=14)
    fig.text(0.5, 0.5, formula, fontsize=14)
    #ax = plt.gca()
    #ax.axes.get_xaxis().set_visible(False)
    #ax.axes.get_yaxis().set_visible(False)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    #plt.xlim([-1.0, 1.0])
    #plt.ylim([-1.0, 1.0])
    image_format = 'PNG'
    tmp_f = '/tmp/pymdslides_tmp_file'
    tmp_f += '-'+str(time.time())+'.'+image_format.lower()
    fig.savefig(tmp_f, dpi=560)
    with Image.open(tmp_f) as img:
      #print(img.mode)
      if img.mode == 'RGBA':
        # need to get rid of alpha channel to do the getbbox below.
        background = Image.new('RGBA', img.size, (255,255,255))
        alpha_composite = Image.alpha_composite(background, img)
        img = alpha_composite.convert('RGB')
      img_invert = ImageOps.invert(img)
      box = img_invert.getbbox() # (left, upper, right, lower)
      print('box', box)
      formula_box = list(box)
      baseline_width = 220
      formula_box[0] = box[0]+baseline_width # cropping away the 'base' inserted in first line of this function.
      cropped_img = img.crop(formula_box)
      cropped_img.save(tmp_f)
      im_width,im_height = cropped_img.size

      baseline_box = list(box)
      baseline_box[2] = baseline_box[0]+baseline_width
      baseline_img = img.crop(baseline_box)
      #baseline_offset = get_baseline_offset(baseline_img) 
      img_invert = ImageOps.invert(baseline_img)
      box = img_invert.getbbox() # (left, upper, right, lower)
      baseline_offset = box[1] # distance from upper edge to top of b character in the 'base' test above.
      #baseline_f = tmp_f+'baseline.png'
      #baseline_img.save(baseline_f)
      #print('baseline_offset', baseline_offset, 'formatting['dimensions']['em']', formatting['dimensions']['em'])
    #self.pdf.image(logo_path, x=formatting['dimensions']['page_width']-30, y=formatting['dimensions']['page_height']-35, w=24, h=30)
    arbitrary_image_margin_mm = 1
    width_mm = int(im_width*pixel_per_mm)
    height_mm = int(im_height*pixel_per_mm)
    baseline_offset_mm = int(baseline_offset*pixel_per_mm)
    #y_offset = (height_mm-formatting['dimensions']['em'])//2
    print('baseline_offset_mm', baseline_offset_mm)
    y_offset = baseline_offset_mm+arbitrary_image_margin_mm
    print('y_offset', y_offset)

    if not dry_run:
      # adding alpha channel, so we can have background images in self.pdf.
      with Image.open(tmp_f) as img:
        img_alpha = ImageOps.invert(ImageOps.grayscale(img))
        #print(img_alpha)
        # making it all black behind the alpha map, white elsewhere. Then it should be readable without alpha map if neccessary anytime, and we don't get any white or gray pixels mixed in.
        white_area = np.array(img)==255
        white_area = white_area.astype(np.uint8)*255
        #print(white_area)
        img = Image.fromarray(white_area)
        img.putalpha(img_alpha)
      img.save(tmp_f)

      if text_color[0] != 0 or text_color[1] != 0 or text_color[2] != 0:
        with Image.open(tmp_f) as img:
          img = img.convert("L")
          img = ImageOps.colorize(img, black=text_color, white=[255,255,255])
          img.putalpha(img_alpha)
        img.save(tmp_f)

      self.pdf.image(tmp_f, x=x, y=y-y_offset, w=width_mm, h=height_mm)
      print('remove(',tmp_f,')')
      os.remove(tmp_f)
    #print(tmp_f)
    x += width_mm
    y += height_mm-y_offset # TODO: also give the y_offset space above the line
    return x,y,width_mm

  def text(self, txt, x, y, h_level=None, em=10, footer=False):
    #self.pdf.set_font() set footer font?
    return self.pdf.text(txt=txt, x=x, y=y+em)

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

  def image(self, image, x, y, w, h, crop_images=False, *args, **kwargs):
    raster_images = False
    ret_val = False
    image_to_display = image
    location = {'x0': x, 'y0': y, 'w': w, 'h': h}
    if is_vector_format(image) and not os.path.splitext(image)[1] in treat_as_raster_images:
      if raster_images:
        tmp_f = '/tmp/pymdslides_tmp_file'
        tmp_f += '-'+str(time.time())+'.png'
        input_file = image.split('#')[0]
        page_no = '0'
        if '#' in image:
          page_no = image.split('#')[1]
        command = 'convert -density 150 '+input_file+'['+page_no+'] '+tmp_f
        print(command)
        os.system(command)
        image_to_display = tmp_f
      else:
        # this will be postponed as we need a workaround using pdfrw and cairosvg.
        self.vector_graphics.setdefault(self.pages_count-1, [])
        self.vector_graphics[self.pages_count-1].append((image, location))
    if is_vector_format(image):
      return ret_val

    if crop_images:
      viewpoint = location
      location = get_cropped_location(image_to_display, location)
      with self.pdf.rect_clip(x=viewpoint['x0'], y=viewpoint['y0'], w=viewpoint['w'], h=viewpoint['h']):
        #print('putting cropped image',image_to_display)
        ret_val = self.pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], link = '')
    else:
      #image_to_display = image
      location = get_uncropped_location(image_to_display, location)
      if image_to_display[-4:] == '.jpg' or image_to_display[-5:] == '.jpeg':
        tmp_f = '/tmp/pymdslides_tmp_file'
        tmp_f += '-'+str(time.time())+'.jpg'
        while os.path.exists(tmp_f):
          tmp_f = '/tmp/pymdslides_tmp_file'
          tmp_f += '-'+str(time.time())+'.jpg'
        #print('workaround jpg image',image_to_display,'copied to',tmp_f)
        shutil.copyfile(image_to_display, tmp_f)
        image_to_display = tmp_f

      #print('putting uncropped image',image_to_display)
      ret_val = self.pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
    if image_to_display != image:
      # tmpfile
      print('remove(',image_to_display,')')
      os.remove(image_to_display)
    return ret_val

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
    ).rotate_d(90).translate(pdf.w / 2, pdf.h / 2)

    self.draw_path(paths)

  def set_xy(self, x, y):
    #self.x = x
    #self.y = y
    return self.pdf.set_xy(x,y)

  def get_format(self):
    return 'pdf'

  def put_vector_images_on_pdf(self, output_file, vector_images):
    reader = PdfReader(output_file)
    area = RectXObj(reader.pages[0])
    #print('reader area', area.w, area.h)
    points_per_mm = area.w/self.page_width
    #print('points_per_mm' , points_per_mm )
    writer = PdfWriter()
    writer.pagearray = reader.Root.Pages.Kids

    #print(vector_images)
    for page_no in range(len(writer.pagearray)):
      #print('i',i)
      if page_no in vector_images:
        #print('i (there is an image)',i)
        for image, image_area in vector_images[page_no]:
          splits = image.split('#')
          image_file = splits[0]
          image_pageno = 0
          if len(splits) > 1:
            image_pageno = int(splits[1])
          image_file_pdf = '/tmp/pymdslides_tmp_file'
          image_file_pdf += '-'+str(time.time())+'.pdf'
          if image_file[-3:] == 'svg':
            cairosvg.svg2pdf(url=image_file, write_to=image_file_pdf)
          if image_file[-3:] == 'eps':
            os.system('epstopdf '+image_file+' -o '+image_file_pdf)
          elif image_file[-3:] == 'pdf':
            image_file_pdf = image_file
          image_pdf = PdfReader(image_file_pdf)
          image_pdf_page = image_pdf.pages[image_pageno]
          image_pdf_page_xobj = RectXObj(image_pdf_page)
          image_width = image_pdf_page_xobj.w
          image_height = image_pdf_page_xobj.h
          #print(image_area)
          desired_width = image_area['w']
          desired_height = image_area['h']
          desired_x = image_area['x0']
          desired_y = image_area['y0']
          if image_area['w']/image_area['h'] > image_width/image_height:
            # area wider than image:
            desired_width = int(desired_height*image_width/image_height)
            desired_x = desired_x+(image_area['w']-desired_width)//2
          else:
            desired_height = int(desired_width*image_height/image_width)
            desired_y = desired_y+(image_area['h']-desired_height)//2
          #print(image_pdf_page)
          scale_w = desired_width*points_per_mm/image_width
          scale_h = desired_height*points_per_mm/image_height
          #area = RectXObj(image_pdf_page)
          #print('area', image_pdf_page_xobj.x, image_pdf_page_xobj.y, image_pdf_page_xobj.w, image_pdf_page_xobj.h, scale_w, scale_h)
          image_pdf_page_xobj.scale(scale_w, scale_h)
          image_pdf_page_xobj.x = desired_x*points_per_mm
          #image_pdf_page_xobj.x = 50
          #print(formatting['dimensions']['page_height'],desired_y,points_per_mm,image_height)
          image_pdf_page_xobj.y = (self.page_height-desired_y-desired_height)*points_per_mm
          #image_pdf_page_xobj.y = 50
          #print('positioned area', image_pdf_page_xobj.x, image_pdf_page_xobj.y, image_pdf_page_xobj.w, image_pdf_page_xobj.h)
          PageMerge(writer.pagearray[page_no]).add(image_pdf_page_xobj, prepend=False).render()
          if image_file_pdf != image_file:
            print('remove(',image_file_pdf,')')
            os.remove(image_file_pdf)
      else:
        # workaround. needed to retain the page size for some reason.
        PageMerge(writer.pagearray[page_no]).render()

    print('pdfrw writing', output_file)
    writer.write(output_file)

  def logo_watermark(self, output_file, logo_path):
    if output_file[-4:] == 'html':
      pass
      #backend.logo_watermark(logo_path)
    else:
      reader = PdfReader(output_file)
      writer = PdfWriter()
      writer.pagearray = reader.Root.Pages.Kids

      backend = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height'])) # 16:9
      backend.add_page()
      logo_width=23
      logo_height=30
      backend.image(logo_path, x=formatting['dimensions']['page_width']-logo_width-formatting['dimensions']['margin_footer'], y=formatting['dimensions']['page_height']-logo_height-formatting['dimensions']['margin_footer'] , w=logo_width, h=logo_height)
      reader = PdfReader(fdata=bytes(backend.output()))
      logo_page = reader.pages[0]

      for i in range(len(writer.pagearray)):
        #print('putting logo on ',i)
        PageMerge(writer.pagearray[i]).add(logo_page, prepend=False).render()

      print('pdfrw writing', output_file)
      writer.write(output_file)



  def output(self, output_file):
    ret_val = self.pdf.output(output_file)
    if len(self.vector_graphics):
      self.put_vector_images_on_pdf(output_file, self.vector_graphics)
    if self.logo_path and os.path.exists(self.logo_path) and os.path.isfile(self.logo_path):
      self.logo_watermark(output_file, self.logo_path)
    return ret_val

  def render_internal_link(self, link, x, y, headlines):
    #print(link)
    x_origin = x
    link = link.replace('&nbsp;', ' ')
    splitted = link.split('](#')
    link_text = splitted[0][1:]
    target = splitted[1][:-1]
    print('link', '"'+link_text+'","'+target+'"')
    self.pdf.set_font('', 'u')
    #if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    #  self.pdf.set_font('standard', 'u', formatting['dimensions']['font_size_standard'])
    #else:
    #  self.pdf.set_font('helvetica', 'u', formatting['dimensions']['font_size_standard'])
    #  #backend.set_font_size(formatting['dimensions']['font_size_standard'])
    self.pdf.set_xy(x,y)
    page_number = headlines.index(target)+1
    #print(headlines)
    print('page_number', page_number, 'target', target)
    link_ref = self.pdf.add_link(page=page_number)
    self.pdf.cell(txt=link_text, link=link_ref, markdown=True)
    x = self.pdf.get_x()
    # workaround. x has a distance, similar to a space after the link.
    space_width = self.pdf.get_string_width(' ')
    x = round(x-0.7*space_width)
    return x, y

def get_cropped_location(image, location):
  # get location around the actual location. will then be cropped to location.
  new_location = {}
  with Image.open(image) as img:
    if location['w']/location['h'] == img.width/img.height:
      new_location = location
    elif location['w']/location['h'] < img.width/img.height:
      # image wider than box
      #print('image wider than box')
      new_width = int(location['h']*(img.width/img.height))
      x_offset = (location['w']-new_width)//2
      new_location = {'x0':  location['x0']+x_offset, 'y0': location['y0'], 'w': new_width, 'h': location['h']}
    else:
      # image higher than box
      #print('image higher than box')
      new_height = int(location['w']*(img.height/img.width))
      #print('new_height', new_height)
      y_offset = (location['h']-new_height)//2
      #print('y_offset', y_offset)
      new_location = {'x0':  location['x0'], 'y0': location['y0']+y_offset, 'w': location['w'], 'h': new_height}
    return new_location

def markdown_to_text(md_data):
  parser = MarkdownIt(renderer_cls=RendererPlain)
  return parser.render(md_data)


def get_uncropped_location(image, location):
  # get location inside the actual location. image will be as wide or as tall as the location box.
  # fix location:
  new_location = {}
  with Image.open(image) as img:
    if location['w']/location['h'] == img.width/img.height:
      new_location = location
    elif location['w']/location['h'] < img.width/img.height:
      # image wider than box
      #print('image wider than box')

      new_height = int(location['w']*(img.height/img.width))
      #print('new_height', new_height)
      y_offset = (location['h']-new_height)//2
      #print('y_offset', y_offset)
      new_location = {'x0':  location['x0'], 'y0': location['y0']+y_offset, 'w': location['w'], 'h': new_height}
    else:
      # image higher than box
      #print('image higher than box')
      new_width = int(location['h']*(img.width/img.height))
      x_offset = (location['w']-new_width)//2
      new_location = {'x0':  location['x0']+x_offset, 'y0': location['y0'], 'w': new_width, 'h': location['h']}
    return new_location


def find_all(a_str, sub):
    result = []
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: break
        result.append(start)
        start += len(sub) # use start += 1 to find overlapping matches
    return result

def is_vector_format(filename):
  return filename.split('#')[0][-3:] in ['pdf', '.ps', 'eps', 'svg']

