#!/usr/bin/python

import os

from fpdf import FPDF
import sys,json,math,time,re
from PIL import Image, ImageOps
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['text.usetex'] = True
#import latextools
import numpy as np

import cairosvg
from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw.pagemerge import RectXObj
import shutil

layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']

page_width = 480
page_height = 270
page_margins = {'x0': 30, 'y0': 40, 'x1': 30, 'y1': 40}
internal_margin = 10
font_size_standard = 34
pixel_per_mm = .15 # magical numbers that make the text align with the equations. .15 corresponds to text size 34, .17 corresponds to text size 40
em = 18
em_title = 26
tiny_footer_em = 6
tiny_footer_margin = 4
tiny_footer_color = [128,128,128]

default_text_color = [0,0,0]

def dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images):
  print('--------------------------------------')
  pdf.add_page()
  #pdf.text(txt=content, markdown=True)
  # this seems to do nothing. checking also in render_text_line.
  with pdf.unbreakable():
    title = ''
    subtitle = ''
    lines = []
    images = []
    alt_texts = []
    l4_boxes = []
    l4_subtitle = None
    l4_lines = []
    for line in content:
      #print('line:', line)
      if l4_subtitle is not None and line.startswith('#'):
        if l4_subtitle != '':
          l4_lines = ['**'+l4_subtitle+'**']+strip_lines(l4_lines)
        else:
          l4_lines = strip_lines(l4_lines)
        l4_boxes.append(l4_lines)
        l4_subtitle = None
        l4_lines = []
      if line.startswith('#') and (len(line) <= 1 or line[1] != '#'):
        title = line[2:]
      elif line.startswith('##') and (len(line) <= 2 or line[2] != '#'):
        subtitle = line[3:]
        #l3 headlines will go as lines.
      elif line.startswith('####') and (len(line) <= 4 or line[4] != '#'):
        # l4 headlines will be put in boxes with following lines.
        # links and formulas are allowed but not images.
        #print('l4 headline:', line)
        l4_subtitle = line[5:]
      elif line.startswith('![') and line.endswith(')') and '](' in line[2:-1]:
        [alt_text,image] = line[2:-1].split('](')
        images.append(image)
        alt_texts.append(alt_text)
      elif l4_subtitle is not None:
        #print('l4 line:', line)
        if line.startswith('* '):
          line = '• '+line[2:]
        l4_lines.append(line)
      else:
      #elif line:
        if line.startswith('* '):
          line = '• '+line[2:]
        lines.append(line)
    if l4_subtitle is not None:
      if l4_subtitle != '':
        l4_lines = ['**'+l4_subtitle+'**']+strip_lines(l4_lines)
      else:
        l4_lines = strip_lines(l4_lines)
      l4_boxes.append(l4_lines)
      l4_subtitle = None
      l4_lines = []
  return render_page(pdf, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images)

def render_page(pdf, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images):
  print('rendering page',title)
  lines = strip_lines(lines)
  vector_images = []
  text_color = default_text_color
  if 'text_color' in formatting:
    print('text_color',formatting['text_color'])
    text_color = formatting['text_color']
  #if 'background_color' in formatting and not same_color(formatting['background_color'], [255,255,255]):
  if 'background_color' not in formatting:
    formatting['background_color'] = [255,255,255]

  pdf.set_fill_color(formatting['background_color'])
  pdf.rect(x=0, y=0, w=page_width, h=page_height, style='F')
  pdf.set_text_color(text_color)

  packed_images = True
  if 'background_image' in formatting:
    print('background_image', formatting['background_image'])
    vec_imgs = put_images_on_page([formatting['background_image']], [''], formatting['layout'], len(lines) > 0, packed_images, True, background=True, raster_images=raster_images)
    vector_images += vec_imgs

  if 'packed_images' in formatting and formatting['packed_images'] == False:
    packed_images = False
  print('crop_images', formatting['crop_images'])
  vec_imgs = put_images_on_page(images, alt_texts, formatting['layout'], len(lines) > 0, packed_images, formatting['crop_images'], background=False, raster_images=raster_images)
  vector_images += vec_imgs
  
  offsets = get_offsets(formatting['layout'])
  x = offsets['x0']
  y = offsets['y0']

  # if title is alone, put it in middle of page
  if no_text(lines) and formatting['layout'] not in ['center', 'image_center', 'image_left_small', 'image_right_small']: # and formatting['layout'] in ['image_full', 'image_left_half', 'image_left_small', 'image_right_half', 'image_right_full']:
    y = page_height//2-em_title//2
  pdf.set_font('CodePro', 'b', 72)
  pdf.set_xy(x,y)
  pdf.text(txt=title, x=x, y=y)#, w=offsets['w'])
  y += em_title

  if subtitle:
    x_subtitle = x+em
    y_subtitle = y-em_title//2
    pdf.set_font('CodePro', 'b', 40)
    pdf.set_xy(x_subtitle,y_subtitle)
    pdf.text(txt=subtitle, x=x_subtitle, y=y_subtitle)#, w=offsets['w'])

  offsets = get_offsets_for_text(formatting['layout'], images=(len(images) > 0))
  column_offsets = offsets
  if 'columns' in formatting and formatting['columns'] > 1:
    column_offsets = get_column_offsets(offsets, formatting['columns'], column=0)
  x = column_offsets['x0']
  y = column_offsets['y0']
  column = 0
  current_table = []
  for line in lines:
    column_offsets = offsets
    column_divider = False
    if 'columns' in formatting and formatting['columns'] > 1:
      if len(line) > 2 and all([c == '-' for c in line]) and column < formatting['columns']-1:
        column += 1
        column_offsets = get_column_offsets(offsets, formatting['columns'], column)
        column_divider = True
        x = column_offsets['x0']
        y = column_offsets['y0']
    #print('offsets:', column_offsets)
    #print('line:', line)
    if len(line) > 1 and line[0] == '|' and line[-1] == '|':
      print('detected table', line)
      current_table.append(line[1:-1].split('|'))
      continue
    elif(len(current_table)):
      print('rendering table')
      x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
      current_table = []
    x, y = render_text_line(line, x, y, column_offsets, headlines, text_color, column_divider=column_divider)
  if 'tiny_footer' in formatting:
    pdf.set_text_color(tiny_footer_color)
    pdf.set_font('RobotoMono', '', 12)
    #x = page_width//2-pdf.get_string_width(formatting['tiny_footer'])//2
    x = tiny_footer_margin
    pdf.text(txt=formatting['tiny_footer'], x=x, y=page_height-tiny_footer_margin) #, w=offsets['w'], align='L')
    pdf.set_text_color(text_color)
  elif(len(current_table)):
    print('rendering table')
    x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
    current_table = []

  if len(l4_boxes):
    print('l4_boxes', l4_boxes)
  box_offsets_list = []
  for i,lines in enumerate(l4_boxes):
    box_width = int(.5*page_width)
    box_x = page_width//2-box_width//2
    box_height = em*(len(lines))+internal_margin*2
    box_y = page_height-page_margins['y1']-box_height
    box_offsets_list.append({'x0': box_x, 'y0': box_y, 'w': box_width, 'h': box_height})
  for i in range(len(box_offsets_list)):
    i_box_offset = box_offsets_list[i]
    y_offset = 0
    for j in range(i+1, len(box_offsets_list)):
      j_box_offset = box_offsets_list[j]
      y_offset += j_box_offset['h']+internal_margin
    box_offsets_list[i]['y0'] = box_offsets_list[i]['y0']-y_offset

  for i,(lines,box_offsets) in enumerate(zip(l4_boxes,box_offsets_list)):
    pdf.set_draw_color(200)
    pdf.set_fill_color((230,240,255))
    with pdf.local_context(fill_opacity=0.75, stroke_opacity=0.75):
      pdf.rect(box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], round_corners=True, style="DF", corner_radius=10)
    #print('pdf.rect(',box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], 'round_corners=True', 'style="D"',')')
    x = box_offsets['x0']+internal_margin
    y = box_offsets['y0']+internal_margin
    for line in lines:
      x, y = render_text_line(line, x, y, box_offsets, headlines, text_color, column_divider=False)
  return vector_images

def no_text(lines):
  for l in lines:
    l = l.strip()
    print(l)
    if l[:2] == '![':
      continue
    elif len(l) == 0:
      continue
    else:
      return False
  return True

def strip_lines(lines):
  #print(lines)
  divisions = []
  divisors = []
  for i,line in enumerate(lines):
    if len(line) > 2 and all([c == '-' for c in line]):
      # new column/divider
      if len(divisors) > 0:
        divisions.append(lines[divisors[-1]+1:i])
      else:
        divisions.append(lines[:i])
      divisors.append(i)
  if len(divisors) > 0:
    divisions.append(lines[divisors[-1]+1:])
  else:
    divisions.append(lines)

  #print(divisions)
  #print(divisors)

  stripped_divisions = []
  for division in divisions:
    stripped_divisions.append(strip_lines_division(division))
  #print(stripped_divisions)
  return_lines = []
  #print(divisors)
  for i,division in enumerate(stripped_divisions):
    return_lines += division
    if i < len(divisors):
      return_lines.append(lines[divisors[i]])
  #print(return_lines)
  return return_lines

def strip_lines_division(lines):
  if len(lines) == 0:
    return lines
  for direction in ['forward', 'backward']:
    for i in range(len(lines)):
      if lines[i] == '':
        continue
      else:
        break
    lines = list(reversed(lines[i:]))
  # The above doesn't work for a size=1 list with only one empty string.
  if lines[0] == '':
    lines = lines[1:]
  return lines

def get_column_offsets(offsets, num_columns, column):
  #print('get_column_offsets',offsets, num_columns, column)
  column_offsets = offsets.copy()
  column_width_incl_margin = offsets['w']//num_columns
  column_width_excl_margin = column_width_incl_margin-internal_margin
  column_offsets['x0'] = offsets['x0']+ (column_width_incl_margin)*column
  column_offsets['x1'] = column_offsets['x0']+column_width_excl_margin
  column_offsets['w'] = column_width_excl_margin
  return column_offsets

def render_text_line(line, x, y, offsets, headlines, text_color, column_divider=False):
    #print('line:',line)
    origin_x = x
    origin_y = y
    pdf.set_xy(x,y)
    if pdf.will_page_break(em):
      print('line will overflow the page. not including in PDF!!!',line)
      return x,y
    if line.startswith('###') and (len(line) <= 3 or line[3] != '#'):
        line = '**'+line[4:]+'**'
    latex_sections = get_latex_sections(line)
    internal_links = get_internal_links(line)
    merged = latex_sections+internal_links
    merged = sorted(merged, key=lambda x: x[0])
    #print(latex_sections)
    heights = []
    #if len(line) > 0 and line[0] == '$' and line[-1] == '$':
    if len(line) == 0:
      #print('empty line!')
      y += int(0.5*em)
    elif len(line) > 2 and all([c == '-' for c in line]):
      pdf.set_line_width(0.5)
      pdf.set_draw_color(text_color)
      if column_divider:
        x = offsets['x0']-internal_margin//2
        pdf.line(x1=x, y1=offsets['y0'], x2=x, y2=offsets['y1'])
      else:
        pdf.line(x1=x, y1=y+int(0.5*em), x2=x+offsets['w'], y2=y+int(0.5*em))
      y += em
      if column_divider:
        y = origin_y
    else:
      pos = 0
      for tag in merged:
        if tag[0] > pos:
          pre_tag = line[pos:tag[0]-1]
          #print('rendering pre_tag', pre_tag)
          x, new_y = render_part_of_line(pre_tag, x, y)
          heights.append(em)
        if tag[2] == 'latex':
          formula = line[tag[0]:tag[1]]
          x, new_y = render_latex(formula, x, y, text_color)
          heights.append(new_y-origin_y)
        else: # internal link
          #print('line', line)
          #print('tag', tag)
          link = line[tag[0]:tag[1]+1]
          #print('link',link)
          x, new_y = render_internal_link(link, x, y, headlines)
          heights.append(new_y-origin_y)
        pos = tag[1]+1
      if pos < len(line):
        x, new_y = render_part_of_line(line[pos:], x, y)
        heights.append(em)
        heights.append(new_y-origin_y)
      y = origin_y + max(heights)
      #print('y', origin_y, y)
    return origin_x, y

def render_table(table, x, y, offsets, headlines, text_color, column_divider=False):
  print('table:',table)
  origin_x = x
  origin_y = y
  pdf.set_font('Lato', '', font_size_standard)
  # due to a bug (in my code or in pfpdf), the table is centered on the page. uncentering:
  uncentered_x = x-(page_width//2-offsets['w']//2)
  pdf.set_xy(uncentered_x,y)
  pdf.set_xy(0,y)
  pdf.set_left_margin(offsets['x0'])
  with pdf.table(width=offsets['w'], align='LEFT', markdown=True) as pdf_table:
    for tr in table:
      row = pdf_table.row()
      for td in tr:
        row.cell(td)
  y += int(em*len(table)*1.8)
  return origin_x, y

def render_part_of_line(part, x, y):
  #print('part', '"'+part+'"')
  pdf.set_font('Lato', '', font_size_standard)
  pdf.set_xy(x,y)
  part = part.replace('&nbsp;', ' ')
  if not part.strip():
      pdf.text(txt=part, x=x, y=y)#, w=offsets['w'], align=align)
  else:
    pdf.cell(txt=part, markdown=True)
  x = pdf.get_x()
  return x, y

def render_internal_link(link, x, y, headlines):
  #print(link)
  link = link.replace('&nbsp;', ' ')
  splitted = link.split(')[#')
  link_text = splitted[0][1:]
  target = splitted[1][:-1]
  #print('link', '"'+link_text+'","'+target+'"')
  pdf.set_font('Lato', 'u', font_size_standard)
  pdf.set_xy(x,y)
  page_number = headlines.index(target)+1
  #print('page_number', page_number, 'target', target)
  fpdf_link = pdf.add_link(page=page_number)
  pdf.cell(txt=link_text, link=fpdf_link, markdown=True)
  x = pdf.get_x()
  return x, y

def render_latex(formula, x, y, text_color):
  return render_latex_matplotlib(formula, x, y, text_color)

def render_latex_latextools(formula, x, y):
    # seems impossible to import svg or pdf!
    formula = '$'+formula+'$'
    #print('formula', formula)
    # Latex!
    latex_eq = latextools.render_snippet(formula, commands=[latextools.cmd.all_math])
    #svg_eq = latex_eq.as_svg()
    tmp_f = '/tmp/pymdslides_temp_file'
    latex_eq.save(tmp_f+'pdf')
    pdf.rasterize(tmp_f+'.png')
    #svg_eq.save(tmp_f)
    #lines = []
    #with open(tmp_f, 'r') as f:
    #  for line in f:
    #    lines.append(line.replace('0%', '0'))
    #with open(tmp_f, 'w') as f:
    #  f.write('\n'.join(lines))
    pdf.image(tmp_f+'.png', x=x, y=y)
    #pdf.template(tmp_f, x=x, y=y, w=60, h=em)
    x += width_mm
    y += height_mm-y_offset # TODO: also give the y_offset space above the line
    return x,y

def render_latex_matplotlib(formula, x, y, text_color):
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
    tmp_f = '/tmp/pymdslides_temp_file'
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
      #print('baseline_offset', baseline_offset, 'em', em)
    #pdf.image(logo_path, x=page_width-30, y=page_height-35, w=24, h=30)
    arbitrary_image_margin_mm = 1
    width_mm = int(im_width*pixel_per_mm)
    height_mm = int(im_height*pixel_per_mm)
    baseline_offset_mm = int(baseline_offset*pixel_per_mm)
    #y_offset = (height_mm-em)//2
    print('baseline_offset_mm', baseline_offset_mm)
    y_offset = baseline_offset_mm+arbitrary_image_margin_mm
    print('y_offset', y_offset)

    # adding alpha channel, so we can have background images in pdf.
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
      
    pdf.image(tmp_f, x=x, y=y-y_offset, w=width_mm, h=height_mm)
    print('remove(',tmp_f,')')
    os.remove(tmp_f)
    #print(tmp_f)
    x += width_mm
    y += height_mm-y_offset # TODO: also give the y_offset space above the line
    return x,y


def get_latex_sections(line):
  latex_formulas = []
  if '$' in line:
    splits = re.split(r'(?<!\\)\$', line)
    pos = 0
    for i,split in enumerate(splits):
      if i%2 == 1:
        latex_formulas.append((pos,pos+len(split), 'latex'))
      pos += len(split)+1 # one for the dollar sign
  return latex_formulas

def get_internal_links(line):
  internal_links = []
  if ')[#' in line:
    locations = find_all(line, ')[#')
    #print('line', line)
    #@locations = [l for l in locations] # I HAVE NO IDEA WHY THIS IS NEEDED!
    #print(locations)
    for l in locations:
      #print(l)
      beginning = line.rfind('(', 0, l)
      end = line.find(']', l)
      #print('beginning, end', beginning, end)
      if beginning != -1 and end != -1:
        internal_links.append((beginning,end,'link'))
  return internal_links 


def get_offsets_for_text(layout, images=True):
  # returns offsets for text area.
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']
  if layout in ['center', 'image_center']:
    y = page_margins['y0']+em_title
    drawable_height = page_height-page_margins['y0']-em_title-page_margins['y1']
    if images:
      drawable_height = drawable_height//2
      y += internal_margin//2
      y += drawable_height
    offsets = {'x0': page_margins['x0'], 'y0': y, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_left_half':
    offsets =  {'x0': (page_width//2)+page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_left_small':
    offsets =  {'x0': (page_width//2)+page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': (page_width//2)-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_right_small':
    offsets =  {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': (page_width//2)-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  else: #image_fill
    offsets = {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
    #offsets =  {'x0': 0, 'y0': 0, 'x1': page_width, 'y1': page_height}
  offsets['w'] = offsets['x1']-offsets['x0']
  offsets['h'] = offsets['y1']-offsets['y0']
  return offsets

def get_offsets(layout):
  # returns offsets for text area.
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center','image_fill']
  if layout in ['center', 'image_center']:
    offsets = {'x0': page_margins['x0'], 'y0': page_margins['y0'], 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_left_half':
    offsets =  {'x0': (page_width//2)+page_margins['x0'], 'y0': page_margins['y0'], 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_left_small':
    offsets = {'x0': page_margins['x0'], 'y0': page_margins['y0'], 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': page_margins['x0'], 'y0': page_margins['y0'], 'x1': (page_width//2)-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_right_small':
    offsets = {'x0': page_margins['x0'], 'y0': page_margins['y0'], 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  else: #image_fill
    offsets = {'x0': page_margins['x0'], 'y0': page_margins['y0'], 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
    #offsets =  {'x0': 0, 'y0': 0, 'x1': page_width, 'y1': page_height}
  offsets['w'] = offsets['x1']-offsets['x0']
  offsets['h'] = offsets['y1']-offsets['y0']
  return offsets

def put_images_on_page(images, alt_texts, layout, has_text, packed_images, crop_images, background=False, raster_images=False):
  vector_graphics = []
  #print('crop_images', crop_images)
  #print('put_images_on_page()', 'layout', layout)
  if len(images) == 0:
    return vector_graphics
  page_images_alts = [(im,alt) for (im, alt) in zip(images, alt_texts) if not alt.startswith('credits:')]
  page_images = [im for (im,alt) in page_images_alts]
  credit_images_alts = [(im,alt) for (im, alt) in zip(images, alt_texts) if alt.startswith('credits:')]
  credit_images = [im for (im,alt) in credit_images_alts]

  if len(page_images) > 0:
    # page images:
    if background:
      locations = [{'x0': 0, 'y0': 0, 'w': page_width, 'h': page_height}]
      #print('background location', locations)
    else:
      locations = get_images_locations(page_images, layout, has_text, packed_images, cred=False)
    for image,location in zip(page_images,locations):
      image_to_display = image
      if is_vector_format(image):
        if raster_images:
          tmp_f = '/tmp/pymdslides_temp_file'
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
          vector_graphics.append((pdf.pages_count-1, image, location))
      if not is_vector_format(image) or raster_images:
        if crop_images:
          #image_to_display_2 = get_cropped_image_file(image_to_display, location)
          #if image_to_display_2 != image_to_display and image_to_display != image:
          #  # remove first temp file:
          #  print('remove(',image_to_display,')')
          #  os.remove(image_to_display)
          #image_to_display = image_to_display_2
          viewpoint = location
          location = get_cropped_location(image_to_display, location)
          with pdf.rect_clip(x=viewpoint['x0'], y=viewpoint['y0'], w=viewpoint['w'], h=viewpoint['h']):
            pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
        else:
          #image_to_display = image
          location = get_uncropped_location(image_to_display, location)
          pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
        if image_to_display != image:
          # tempfile
          print('remove(',image_to_display,')')
          os.remove(image_to_display)

  # credit images:
  if len(credit_images):
    locations = get_images_locations(credit_images, layout, has_text, packed_images, cred=True)
    for image,location in zip(credit_images,locations):
      print('location', location)
      #if crop_images:
      image_to_display = get_cropped_image_file(image, location)
      #else:
      #  image_to_display = image
      #  location = get_uncropped_location(image, location)
      pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
      if image_to_display != image:
        print('remove(',image_to_display,')')
        os.remove(image_to_display)
  return vector_graphics

def is_vector_format(filename):
  return filename.split('#')[0][-3:] in ['pdf', '.ps', 'eps', 'svg']

def get_uncropped_location(image, location):
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

def get_cropped_image_file(image, location):
  # fix crop:
  tmp_f = '/tmp/pymdslides_temp_file'
  with Image.open(image) as img:
    if img.width < 10 or img.height < 10:
      img = img.resize((img.width*10, img.height*10))
    new_width = img.width
    new_height = img.height
    x_offset = 0
    y_offset = 0
    if location['w']/location['h'] == img.width/img.height:
      return image
    elif location['w']/location['h'] < img.width/img.height:
      # shrink width
      new_width = int(img.height*(location['w']/location['h']))
      x_offset = int((img.width-new_width)/2)
    else:
      # shrink height
      new_height = int(img.width*(location['h']/location['w']))
      y_offset = int((img.height-new_height)/2)
    box = (x_offset, y_offset, x_offset+new_width, y_offset+new_height)
    #print('width',img.width,'height',img.height)
    #print('box',box)
    crop = img.crop(box)
    image_format = 'PNG'
    tmp_f += '-'+str(time.time())+'.'+image_format.lower()
    crop.save(tmp_f, image_format)
    return tmp_f

def get_images_locations(images, layout, has_text, packed_images=False, cred=False):
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']
  #print('get_images_locations()', 'layout', layout)
  locations = []
  image_area = [0,0,page_width,page_height]
  #print('page_margins',page_margins)
  #print('layout',layout)
  image_area = get_image_area(layout, has_text)

  #print('num_images', len(images))
  #print('cred', cred)
  cred_aspect_ratio = 1.0/1.1
  cred_fraction = 0.8 # TODO: set reasonable constant somewhere, or let it be configurable.
  if cred:
    image_area = get_offsets_for_text(layout)
    image_area['y0'] = page_height-page_margins['y1']
    image_area['y1'] = page_height-page_margins['y1']+int(cred_fraction*page_margins['y1'])

  image_area['w'] = image_area['x1']-image_area['x0']
  image_area['h'] = image_area['y1']-image_area['y0']

  if cred:
    grid_width = len(images)
    grid_height = 1
  elif layout in ['center', 'image_center']:
    grid_width = len(images)
    grid_height = 1
  else:
    grid_height = math.sqrt(len(images))
    #print(grid_height)
    if grid_height - int(grid_height) > 0.0:
      grid_height = int(grid_height)+1
      grid_width = math.ceil(len(images)/grid_height)
    else:
      grid_height = int(grid_height)
      grid_width = grid_height

  if layout in ['image_fill'] and not cred:
    # prefer to put images side-by-side instead of on top of each other:
    g_w = grid_height
    grid_height = grid_width
    grid_width = g_w
  #print('grid',grid_width,grid_height)
  #print('images',len(images))

  if cred:
    tot_height = image_area['h']
    tot_width = image_area['h']*cred_aspect_ratio*len(images)
    image_area['x0'] = image_area['x0']+image_area['w']//2-tot_width//2
    image_area['x1'] = image_area['x0']+tot_width
    image_area['w'] = image_area['x1']-image_area['x0']
    image_area['h'] = image_area['y1']-image_area['y0']

  print(image_area['w'], grid_width, image_area['h'], grid_height)
  image_size = {'w': int(image_area['w']/grid_width), 'h': int(image_area['h']/grid_height)}
  
  #print('image_size', image_size)
  for i,image in enumerate(images):
    pos_x = i % grid_width
    pos_y = i // grid_width
    marg_x = 0
    if pos_x >= 1 and not packed_images and not cred:
      marg_x = internal_margin
    marg_y = 0
    if pos_y >= 1 and not packed_images and not cred:
      marg_y = internal_margin
    #print('image-grid:', pos_x, pos_y, marg_x, marg_y)
    #location  = {'x0': image_area['x0']+pos_x*image_size['w'], 'y0': image_area['y0']+pos_y*image_size['h'], 'w': image_size['w'], 'h': image_size['h']}
    location  = {'x0': image_area['x0']+pos_x*image_size['w']+marg_x, 'y0': image_area['y0']+pos_y*image_size['h']+marg_y, 'w': image_size['w']-marg_x, 'h': image_size['h']-marg_y}
    locations.append(location)
  return locations

def get_image_area(layout, has_text):
  if layout in ['center', 'image_center']:
    drawable_height = page_height-page_margins['y0']-em_title-page_margins['y1']
    if has_text:
      image_area = {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': drawable_height//2+page_margins['y0']+em_title-internal_margin//2}
    else:
      image_area = {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_left_half':
    image_area =  {'x0': 0, 'y0': 0, 'x1': page_width//2, 'y1': page_height}
  elif layout == 'image_left_small':
    image_area =  {'x0': page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': (page_width//2)-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  elif layout == 'image_right_half':
    image_area =  {'x0': page_width//2, 'y0': 0, 'x1': page_width, 'y1': page_height}
  elif layout == 'image_right_small':
    image_area =  {'x0': (page_width//2)+page_margins['x0'], 'y0': page_margins['y0']+em_title, 'x1': page_width-page_margins['x1'], 'y1': page_height-page_margins['y1']}
  else: #image_full
    image_area =  {'x0': 0, 'y0': 0, 'x1': page_width, 'y1': page_height}
  #print('image_area',image_area)
  return image_area

def draw_svg_image(pdf, svg_file):
  svg = pdf.svg.SVGObject.from_file(svg_file)

  # We pass align_viewbox=False because we want to perform positioning manually
  # after the size transform has been computed.
  width, height, paths = svg.transform_to_page_viewport(pdf, align_viewbox=False)
  # note: transformation order is important! This centers the svg drawing at the
  # origin, rotates it 90 degrees clockwise, and then repositions it to the
  # middle of the output page.
  paths.transform = paths.transform @ fpdf.drawing.Transform.translation(
      -width / 2, -height / 2
  ).rotate_d(90).translate(pdf.w / 2, pdf.h / 2)

  pdf.draw_path(paths)

def same_color(first, second):
  if len(first) != len(second):
    return False
  for f,s in zip(first,second):
    if f != s:
      return False
  return True

def find_all(a_str, sub):
    result = []
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: break
        result.append(start)
        start += len(sub) # use start += 1 to find overlapping matches
    return result

def put_vector_images_on_pdf_with_crop(pdf_file, vector_images, crop_images):
  reader = PdfReader(pdf_file)
  area = RectXObj(reader.pages[0])
  #print('reader area', area.w, area.h)
  points_per_mm = area.w/page_width
  #print('points_per_mm' , points_per_mm )
  writer = PdfWriter()
  writer.pagearray = reader.Root.Pages.Kids

  #print(vector_images)
  for i in range(len(writer.pagearray)):
    #print('i',i)
    if i in vector_images:
      #print('i (there is an image)',i)
      for pageno, image, image_area in vector_images[i]:
        splits = image.split('#')
        image_file = splits[0]
        image_pageno = 0
        if len(splits) > 1:
          image_pageno = int(splits[1])
        image_file_pdf = '/tmp/pymdslides_temp_file'
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
        viewrect = None
        if crop_images:
          if image_area['w']/image_area['h'] > image_width/image_height:
            # area wider than image:
            desired_height = int(desired_width*image_height/image_width)
            desired_y = desired_y+(image_area['h']-desired_height)//2
          else:
            desired_width = int(desired_height*image_width/image_height)
            desired_x = desired_x+(image_area['w']-desired_width)//2
          #viewrect = (margin, margin, x2 - x1 - 2 * margin, y2 - y1 - 2 * margin)
          viewrect = (desired_x*points_per_mm, desired_y*points_per_mm, desired_width*points_per_mm, desired_height*points_per_mm)
        else:
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
        #print(page_height,desired_y,points_per_mm,image_height)
        image_pdf_page_xobj.y = (page_height-desired_y-desired_height)*points_per_mm
        #image_pdf_page_xobj.y = 50
        #print('positioned area', image_pdf_page_xobj.x, image_pdf_page_xobj.y, image_pdf_page_xobj.w, image_pdf_page_xobj.h)
        if viewrect:
          print('viewrect', viewrect)
          PageMerge(writer.pagearray[i]).add(image_pdf_page_xobj, prepend=False, viewrect=viewrect).render()
        else:
          PageMerge(writer.pagearray[i]).add(image_pdf_page_xobj, prepend=False).render()
        if image_file_pdf != image_file:
          print('remove(',image_file_pdf,')')
          os.remove(image_file_pdf)
    else:  
      # workaround. needed to retain the page size for some reason.
      PageMerge(writer.pagearray[i]).render()

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)


def put_vector_images_on_pdf(pdf_file, vector_images, crop_images):
  reader = PdfReader(pdf_file)
  area = RectXObj(reader.pages[0])
  #print('reader area', area.w, area.h)
  points_per_mm = area.w/page_width
  #print('points_per_mm' , points_per_mm )
  writer = PdfWriter()
  writer.pagearray = reader.Root.Pages.Kids

  #print(vector_images)
  for i in range(len(writer.pagearray)):
    #print('i',i)
    if i in vector_images:
      #print('i (there is an image)',i)
      for pageno, image, image_area in vector_images[i]:
        splits = image.split('#')
        image_file = splits[0]
        image_pageno = 0
        if len(splits) > 1:
          image_pageno = int(splits[1])
        image_file_pdf = '/tmp/pymdslides_temp_file'
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
        #print(page_height,desired_y,points_per_mm,image_height)
        image_pdf_page_xobj.y = (page_height-desired_y-desired_height)*points_per_mm
        #image_pdf_page_xobj.y = 50
        #print('positioned area', image_pdf_page_xobj.x, image_pdf_page_xobj.y, image_pdf_page_xobj.w, image_pdf_page_xobj.h)
        PageMerge(writer.pagearray[i]).add(image_pdf_page_xobj, prepend=False).render()
        if image_file_pdf != image_file:
          print('remove(',image_file_pdf,')')
          os.remove(image_file_pdf)
    else:  
      # workaround. needed to retain the page size for some reason.
      PageMerge(writer.pagearray[i]).render()

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)

def logo_watermark(pdf_file, logo_path):
  reader = PdfReader(pdf_file)
  writer = PdfWriter()
  writer.pagearray = reader.Root.Pages.Kids

  pdf = FPDF(orientation = 'P', unit = 'mm', format = (page_width, page_height)) # 16:9
  pdf.add_page()
  logo_width=23
  logo_height=30
  pdf.image(logo_path, x=page_width-logo_width-tiny_footer_margin, y=page_height-logo_height-tiny_footer_margin , w=logo_width, h=logo_height)
  reader = PdfReader(fdata=bytes(pdf.output()))
  logo_page = reader.pages[0]

  for i in range(len(writer.pagearray)):
    #print('putting logo on ',i)
    PageMerge(writer.pagearray[i]).add(logo_page, prepend=False).render()

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)

if __name__ == "__main__":
  md_file = sys.argv[1]
  print('md_file:',md_file)
  pdf_file = '.'.join(md_file.split('.')[:-1])+'.pdf'

  raster_images = False
  if '--raster-images' in sys.argv:
    raster_images = True
  
  script_home = os.path.dirname(os.path.realpath(__file__))
  print('script_home', script_home)
  pdf = FPDF(orientation = 'P', unit = 'mm', format = (page_width, page_height)) # 16:9
  pdf.add_font('Lato', 'i', os.path.join(script_home, 'fonts/Lato-Italic.ttf'))
  pdf.add_font('Lato', 'bi', os.path.join(script_home, 'fonts/Lato-BolIta.ttf'))
  pdf.add_font('Lato', 'b', os.path.join(script_home, 'fonts/Lato-Bold.ttf'))
  pdf.add_font('Lato', '', os.path.join(script_home, 'fonts/Lato-Regular.ttf'))
  pdf.add_font('RobotoMono', '', os.path.join(script_home, 'fonts/RobotoMono-Regular.ttf'))
  pdf.add_font('CodePro', 'b', os.path.join(script_home, 'fonts/CodePro-Bold.ttf'))
  pdf.set_font('Lato', '', 60)
  pdf.set_text_color(0,0,0)

  pdf.oversized_images = "DOWNSCALE"

  layout = layouts[-1]

  vector_images = {}

  with open(md_file, 'r') as f:
    md_contents = f.read()
  content = []
  # default formatting:
  formatting = {'layout': 'center', 'crop_images': True}
  global_formatting = {}
  preamble=True
  headlines = []
  headlines_h2 = {}
  for line in md_contents.split('\n'):
    if line.startswith('#') and (len(line) <= 1 or line[1] != '#'):
      headlines.append(line[2:].strip())
    if line.startswith('##') and (len(line) <= 2 or line[2] != '#'):
      headlines_h2[len(headlines)-1] = line[3:].strip()
  for i in range(len(headlines)):
    if headlines[i] == '' and i in headlines_h2:
      headlines[i] = headlines_h2[i]
  for line in md_contents.split('\n'):
    #print(line)
    # supporting single asterixes for italics in markdown.
    line = re.sub(r'(?<!\*)\*(?![\*\s])', '__', line)
    if '$' in line:
      splits = line.split('$')
      corrected_splits = []
      for i,split in enumerate(splits):
        if i%2==1:
          #formula:
          if '__' in split:
            split = split.replace('__', '*')
        corrected_splits.append(split)
      line = '$'.join(corrected_splits)

    #$if line[:3] == '__ ':
    # line = '* '
    #print(line)
    #print(line)
    if line.startswith('# '):
      if preamble:
          # formatting from preamble is global for whole document:
        global_formatting = formatting.copy()
        content = []
        preamble = False
      else:
        print('generating page (#)')
        if 'visibility' in formatting and formatting['visibility'] == 'hidden':
          print('------------------------------------\n"visibility":"hidden" is deprecated. use "hidden": true instead.')
          print('------------------------------------\nThis page is hidden. Will not generate pdf page.')
          vector_images_page = []

        elif 'hidden' in formatting and formatting['hidden']:
          print('------------------------------------\nThis page is hidden. Will not generate pdf page.')
          vector_images_page = []
        else:
          vector_images_page = dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images)
          print('------------------------------------')
        if len(vector_images_page) > 0:
          vector_images[pdf.pages_count-1] = vector_images_page
        # reset page-specific formatting:
        formatting = global_formatting.copy()
      content = [line]
      #current_headline = line[2:]
    elif line.startswith('[//]: # ('):
      comment = line[9:-1]
      try:
        new_formatting = json.loads(comment)
        formatting.update(new_formatting)
        #layout = comment_json['layout']
        print('Setting formatting',formatting)
      except Exception as e:
        print('Ignoring markdown comment: ',comment)
        print(e)
    else:
      content.append(line)

  print('generating page (last)')
  if 'hidden' in formatting and formatting['hidden']:
    print('------------------------------------\nThis page is hidden. Will not generate pdf page.')
  else:
    vector_images_page = dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images)
    print('------------------------------------')
  if len(vector_images_page) > 0:
     vector_images[pdf.pages_count-1] = vector_images_page
  print('writing pdf file:',pdf_file)
  pdf.output(pdf_file)

  if len(vector_images) > 0:
    print('vector_images',len(vector_images))
    #modified_pdf_file = pdf_file+'-with-graphics.pdf'
    #shutil.copyfile(pdf_file, modified_pdf_file)
    #put_vector_images_on_pdf(modified_pdf_file, vector_images)
    put_vector_images_on_pdf(pdf_file, vector_images, formatting['crop_images'])

  logo_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'logo.png')
  if logo_path and os.path.exists(logo_path):
    logo_watermark(pdf_file, logo_path)

