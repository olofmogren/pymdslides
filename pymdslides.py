#!/usr/bin/python
# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>. 

import os

import sys,math,time,re
from PIL import Image, ImageOps, ImageFont
from subprocess import Popen,PIPE
from datetime import datetime

import shutil
import yaml
import copy
from backend_html import backend_html
from backend_odp import backend_odp

import copy

layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'image_center', 'image_fill']

default_text_color= [0,0,0]
default_layout = 'image_center'
default_crop = True
default_footer_color= [100,100,100]
default_l4_box_border_color = 200
default_l4_box_fill_color = [230,240,255]
default_dimensions = {
        'page_width': 480,
        'page_height': 270,
        'page_margins': {'x0': 30, 'y0': 22, 'x1': 30, 'y1': 22},
        'internal_margin': 10,
        'font_size_standard': 34,
        'font_size_title': 72,
        'font_size_subtitle': 40,
        'font_size_footer': 14,
        'pixel_per_mm': .15, # magical numbers that make the text align with the equations. .15 corresponds to text size 34, .17 corresponds to text size 40
        'em': 16,
        'em_title': 24,
        'em_subtitle': 14,
        'em_footer': 6,
        'margin_footer': 4,
}

def dump_page_content(backend, content, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number, page_number):
  print('--------------------------------------')
  backend.add_page()
  #backend.text(txt=content, markdown=True)
  # this seems to do nothing. checking also in render_text_line.
  formatting = preprocess_formatting(formatting)
  with backend.unbreakable():
    title = ''
    subtitle = ''
    lines = []
    images = []
    alt_texts = []
    l4_boxes = []
    l4_subtitle = None
    l4_lines = []
    #print('content', content)
    for line in content:
      #print('line:', line)
      if l4_subtitle is not None and line.startswith('#'):
        if l4_subtitle != '':
          l4_lines = ['**'+l4_subtitle+'**\n\n']+strip_lines(l4_lines)
        else:
          l4_lines = strip_lines(l4_lines)
        l4_boxes.append(l4_lines)
        l4_subtitle = None
        l4_lines = []
      if line.startswith('#') and (len(line) <= 1 or line[1] != '#'):
        title = line[2:]
        #print('title', title, '"', line, '"')
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
        l4_lines.append(line)
      else:
      #elif line:
        if line == '__':
          print('{}:{}: ignoring empty line "{}"'.format(md_file_stripped, line_number, line))
        else:
          lines.append(line)
    if l4_subtitle is not None:
      if l4_subtitle != '':
        l4_lines = ['**'+l4_subtitle+'**']+strip_lines(l4_lines)
      else:
        l4_lines = strip_lines(l4_lines)
      l4_boxes.append(l4_lines)
      l4_subtitle = None
      l4_lines = []
  return render_page(backend, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number, page_number)

def render_page(backend, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number, page_number):
  print('{}:{}: rendering page "{}"'.format(md_file_stripped, line_number, title))
  lines = strip_lines(lines)
  text_color = default_text_color
  if 'text_color' in formatting:
    print('{}:{}: text_color {}'.format(md_file_stripped, line_number, formatting['text_color']))
    text_color = formatting['text_color']
  if 'background_color' not in formatting:
    formatting['background_color'] = [255,255,255]

  backend.set_background_color(formatting['background_color'])
  backend.set_text_color(text_color)
  if hasattr(backend, 'set_link_color'):
    backend.set_link_color(formatting.get('link_color', None))

  packed_images = True
  if 'background_image' in formatting:
    print('{}:{}: background_image {}'.format(md_file_stripped, line_number, formatting['background_image']))
    put_images_on_page(md_file_stripped, line_number, [formatting['background_image']], [''], formatting['layout'], len(lines) > 0, packed_images, True, formatting, background=True, raster_images=raster_images, treat_as_raster_images=treat_as_raster_images)

  if 'packed_images' in formatting and formatting['packed_images'] == False:
    packed_images = False
  print('{}:{}: crop_images {}'.format(md_file_stripped, line_number, formatting['crop_images']))
  put_images_on_page(md_file_stripped, line_number, images, alt_texts, formatting['layout'], len(lines) > 0, packed_images, formatting['crop_images'], formatting, background=False, raster_images=raster_images, treat_as_raster_images=treat_as_raster_images)
  
  offsets = get_offsets(formatting['layout'])
  offsets_title = offsets
  if 'title_full_width' in formatting and formatting['title_full_width']:
    offsets_title = get_offsets('image_center')
  x_title = offsets_title['x0']
  y_title = offsets_title['y0']

  # if title_vertical_center, put it in middle of page
  if 'title_vertical_center' in formatting and formatting['title_vertical_center']:
    y_title = formatting['dimensions']['page_height']//2-int(1.5*formatting['dimensions']['em_title'])

  title_font_size = fit_text_font_size(title, offsets_title['w'], formatting, category='title', script_home=script_home)

  if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
    print('{}:{}: Setting font title with size'.format(md_file_stripped, line_number), title_font_size)
    backend.set_font('title', '', title_font_size)
  else:
    print('{}:{}: Setting font size title'.format(md_file_stripped, line_number), title_font_size)
    backend.set_font_size('title', title_font_size)

  backend.set_xy(x_title, y_title)
  backend.textbox(lines=[title], x=x_title, y=y_title, w=offsets_title['w'], h=int(formatting['dimensions']['em_title']*1.3), h_level=1, headlines=headlines, text_color=text_color, align=get_alignment(formatting, 'title'), markdown_format=False)

  if subtitle:
    x_subtitle = x_title
    w_subtitle = offsets_title['w']
    if get_alignment(formatting, 'title') == 'left':
      x_subtitle = x_subtitle+formatting['dimensions']['em']
      w_subtitle = offsets_title['w'] - formatting['dimensions']['em']
    y_subtitle = y_title+formatting['dimensions']['em_title']*.8

    subtitle_font_size = fit_text_font_size(subtitle, w_subtitle, formatting, category='subtitle', script_home=script_home)
    if 'fonts' in formatting and 'font_file_subtitle' in formatting['fonts']:
      backend.set_font('subtitle', '', min(subtitle_font_size, title_font_size))
    else:
      backend.set_font_size('subtitle', min(subtitle_font_size, title_font_size))

    backend.set_xy(x_subtitle,y_subtitle)
    backend.textbox(lines=[subtitle], x=x_subtitle, y=y_subtitle, w=offsets_title['w'], h=int(formatting['dimensions']['em_subtitle']*1.5), h_level=2, headlines=headlines, text_color=text_color, align=get_alignment(formatting, 'title'), markdown_format=False)

  x = offsets['x0']
  y = y_title+formatting['dimensions']['em_title']

  has_page_images = any(not alt.startswith('credits:') for alt in alt_texts)
  print('render_page: images', len(images), 'has_page_images', has_page_images)
  offsets = get_offsets_for_text(formatting['layout'], images=has_page_images)

  column_offsets = offsets
  num_columns = 1
  if 'columns' in formatting and formatting['columns'] > 1:
    num_columns = formatting['columns']
    column_offsets = get_column_offsets(offsets, formatting['columns'], column=0)
  column_lines = split_lines_into_columns(lines, num_columns)
  #print('column_lines', column_lines)
  for c in range(num_columns):
    #print('column:', c)
    lines_this_column = column_lines[c]
    x = column_offsets['x0']
    y = column_offsets['y0']
    if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
      backend.set_font('standard', '', formatting['dimensions']['font_size_standard'])
    else:
      backend.set_font_size('standard', formatting['dimensions']['font_size_standard'])
    vertical_align = None
    if 'text_vertical_align' in formatting:
      vertical_align = formatting['text_vertical_align']
    backend.textbox(lines=lines_this_column, x=x, y=y, w=column_offsets['w'], h=column_offsets['h'], headlines=headlines, h_level=None, text_color=text_color, align=get_alignment(formatting), markdown_format=True, text_vertical_align=vertical_align)
    # for next column:
    column_offsets = get_column_offsets(offsets, num_columns, column=c+1)
  if 'footer' in formatting:
    backend.set_text_color(formatting.get('footer_color', default_footer_color))
    if 'fonts' in formatting and 'font_file_footer' in formatting['fonts']:
      backend.set_font('footer', '', formatting['dimensions']['font_size_footer'])
    else:
      backend.set_font_size('footer', formatting['dimensions']['font_size_footer'])
    #x = formatting['dimensions']['page_width']//2-backend.get_string_width(formatting['footer'])//2
    x = formatting['dimensions']['margin_footer']
    footer_text = formatting['footer']
    if 'page_numbering' in formatting and formatting['page_numbering']:
      footer_text = str(page_number)+('&nbsp;&nbsp;&nbsp;' if len(footer_text) > 0 else '')+footer_text
    backend.text(txt=footer_text, x=x, y=formatting['dimensions']['page_height']-formatting['dimensions']['margin_footer']-formatting['dimensions']['em_footer'], headlines=headlines, em=formatting['dimensions']['em_footer'], footer=True, markdown_format=True) #, w=offsets['w'], align='L')

  if len(l4_boxes):
    print('{}:{}: l4_boxes: \n  {}'.format(md_file_stripped, line_number, yaml.dump(l4_boxes).replace('\n', '\n  ')))
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    backend.set_font('standard', '', formatting['dimensions']['font_size_standard'])
  else:
    backend.set_font_size('standard', formatting['dimensions']['font_size_standard'])
  box_offsets_list = []
  for i,lines in enumerate(l4_boxes):
    box_width = int(.6*formatting['dimensions']['page_width'])
    box_x = formatting['dimensions']['page_width']//2-box_width//2
    box_height = formatting['dimensions']['em']*(len(lines))+formatting['dimensions']['internal_margin']*2
    #box_y = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']-box_height
    box_y = offsets['y0']
    box_offsets_list.append({'x0': box_x, 'y0': box_y, 'w': box_width, 'h': box_height})
  for i in range(len(box_offsets_list)):
    i_box_offset = box_offsets_list[i]
    y_offset = 0
    for j in range(i+1, len(box_offsets_list)):
      j_box_offset = box_offsets_list[j]
      y_offset += j_box_offset['h']+formatting['dimensions']['internal_margin']
    box_offsets_list[i]['y0'] = box_offsets_list[i]['y0']-y_offset
#
  vertical_align = None
  if 'text_vertical_align' in formatting:
    vertical_align = formatting['text_vertical_align']
  for i,(lines,box_offsets) in enumerate(zip(l4_boxes,box_offsets_list)):
    with backend.local_context(fill_opacity=0.75, stroke_opacity=0.75):
      backend.l4_box(lines, box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], headlines, align=get_alignment(formatting), border_color=default_l4_box_border_color, border_opacity=0.75, background_color=default_l4_box_fill_color, background_opacity=0.75, markdown_format=True, text_color=[0,0,0], text_vertical_align=vertical_align)

def split_lines_into_columns(lines, num_columns):
  if num_columns == 1:
    return [lines]
  column_lines = [[]]
  column = 0
  for line in lines:
    #column_offsets = offsets
    column_divider = False
    if len(line) > 3 and all([c == '-' for c in line]) and column < num_columns-1:
      column += 1
      column_lines.append([])
    else:
      column_lines[column].append(line)
  for i in range(len(column_lines), num_columns):
    column_lines.append([])
  return column_lines

def fit_text_font_size(text, max_width, formatting, category='title', script_home='', min_font_size=12, avg_char_em_ratio=0.58):
  base_size = formatting['dimensions'][f'font_size_{category}']
  if not text or max_width <= 0:
    return base_size

  # In backend_html: html_font_size(s) = (32*s/page_width) cqw = 0.32*s page units
  em_page_units = 0.32 * base_size
  text_width = None

  # 1. Measure with PIL.ImageFont (subtitle falls back to title font if not set)
  font_path = None
  if 'fonts' in formatting:
    font_path = formatting['fonts'].get(f'font_file_{category}')
    if not font_path and category == 'subtitle':
      font_path = formatting['fonts'].get('font_file_title')

  if font_path:
    if not os.path.isfile(font_path) and script_home:
      font_path = os.path.join(script_home, font_path)
    if os.path.isfile(font_path):
      try:
        ref_size = 200
        font = ImageFont.truetype(font_path, ref_size)
        text_width = (font.getlength(text) / ref_size) * em_page_units
      except Exception:
        text_width = None

  # 2. Fallback: estimate width from character count
  if text_width is None:
    text_width = len(text) * em_page_units * avg_char_em_ratio

  usable_width = max_width * 0.98
  if text_width > usable_width:
    scaled_size = int(base_size * (usable_width / text_width))
    return max(min_font_size, scaled_size)

  return base_size

def preprocess_formatting(formatting):
  for color in ['background_color', 'text_color', 'footer_color', 'l4_box_fill_color', 'link_color']:
    if color in formatting:
      #print('color',formatting[color])
      if formatting[color] == 'white':
        formatting[color] = [255,255,255]
      elif formatting[color] == 'grey':
        formatting[color] = [100,100,100]
      elif formatting[color] == 'black':
        formatting[color] = [0,0,0]
      elif formatting[color] == 'orange':
        formatting[color] = [255,180,0]
      elif formatting[color] == 'red':
        formatting[color] = [255,0,0]
      elif formatting[color] == 'green':
        formatting[color] = [0,255,0]
      elif formatting[color] == 'blue':
        formatting[color] = [0,0,255]
      elif formatting[color] == 'yellow':
        formatting[color] = [255,255,0]
      elif formatting[color] == 'purple':
        formatting[color] = [225,0,255]
      elif formatting[color] == 'pink':
        formatting[color] = [255,86,235]
      elif formatting[color] == 'darkorange':
        formatting[color] = [180,100,0]
      elif formatting[color] == 'darkred':
        formatting[color] = [100,0,0]
      elif formatting[color] == 'darkgreen':
        formatting[color] = [0,80,45]
      elif formatting[color] == 'darkblue':
        formatting[color] = [0,0,100]
      elif formatting[color] == 'darkpurple':
        formatting[color] = [120,0,140]
      elif formatting[color] == 'lightgrey':
        formatting[color] = [180,180,180]
      elif formatting[color] == 'lightpink':
        formatting[color] = [255,155,235]
      elif formatting[color] == 'lightgreen':
        formatting[color] = [120,255,180]
      elif formatting[color] == 'lightblue':
        formatting[color] = [160,180,255]
      elif formatting[color] is not None and formatting[color][0] == '#':
        # html:
        r_hex = formatting[color][1:3]
        r = int(r_hex, 16)
        g_hex = formatting[color][3:5]
        g = int(g_hex, 16)
        b_hex = formatting[color][5:7]
        b = int(b_hex, 16)
        #print('detected hex',formatting[color],'computed decimals',r,g,b)
        formatting[color] = [r,g,b]
  return formatting
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
    if len(line) > 3 and all([c == '-' for c in line]):
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
  column_width_excl_margin = column_width_incl_margin-formatting['dimensions']['internal_margin']
  column_offsets['x0'] = offsets['x0']+ (column_width_incl_margin)*column
  column_offsets['x1'] = column_offsets['x0']+column_width_excl_margin
  column_offsets['w'] = column_width_excl_margin
  return column_offsets

def get_offsets_for_text(layout, images=True):
  margin = formatting['dimensions']['internal_margin']
  y_top = formatting['dimensions']['page_margins']['y0'] + formatting['dimensions']['em_title'] + margin
  y_bottom = formatting['dimensions']['page_height'] - formatting['dimensions']['page_margins']['y1']
  drawable_height = y_bottom - y_top

  if layout in ['image_center']:
    if images:
      # Lower section: starts exactly (margin // 2) below the midpoint
      midpoint = y_top + (drawable_height // 2)
      text_y0 = midpoint + (margin // 2)
    else:
      text_y0 = y_top

    offsets = {
      'x0': formatting['dimensions']['page_margins']['x0'],
      'y0': text_y0,
      'x1': formatting['dimensions']['page_width'] - formatting['dimensions']['page_margins']['x1'],
      'y1': y_bottom
    }
  elif layout == 'image_left_half':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['internal_margin']//2, 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_small':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['internal_margin']//2, 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['internal_margin']//2, 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_small':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['internal_margin']//2, 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_fill
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
    #offsets =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  offsets['w'] = offsets['x1']-offsets['x0']
  offsets['h'] = offsets['y1']-offsets['y0']
  return offsets

def get_offsets(layout):
  # returns offsets for text area.
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'image_center','image_fill']
  if layout in ['image_center']:
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_half':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_small':
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_small':
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_fill
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
    #offsets =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  offsets['w'] = offsets['x1']-offsets['x0']
  offsets['h'] = offsets['y1']-offsets['y0']
  return offsets

def put_images_on_page(md_file_stripped, line_number, images, alt_texts, layout, has_text, packed_images, crop_images, formatting, background=False, raster_images=False, treat_as_raster_images=[]):
  #print('crop_images', crop_images)
  #print('put_images_on_page()', 'layout', layout)
  if len(images) == 0:
    return 
  # print("images", images,alt_texts)
  images_to_remove = []
  for i,(image,alt_text) in enumerate(zip(images,alt_texts)):
    if (image == "" or not os.path.isfile(image.split('#')[0])) and '://' not in image:
      #print("{}:{}: Warning: Empty image tag, or image file does not exist. '{}'. Ignoring.".format(md_file_stripped, line_number, image, alt_text))
      images_to_remove.append(i)
  images_to_remove.reverse()
  for index in images_to_remove:
    print("{}:{}: Warning: Empty image tag, or image file does not exist. '{}'. Ignoring.".format(md_file_stripped, line_number, images[index], alt_texts[index]))
    del images[index]
    del alt_texts[index]
  page_images_alts = [(im,alt) for (im, alt) in zip(images, alt_texts) if not alt.startswith('credits:')]
  page_images = [im for (im,alt) in page_images_alts]
  credit_images_alts = [(im,alt) for (im, alt) in zip(images, alt_texts) if alt.startswith('credits:')]
  credit_images = [im for (im,alt) in credit_images_alts]

  if len(page_images) > 0:
    # page images:
    if background:
      locations = [{'x0': 0, 'y0': 0, 'w': formatting['dimensions']['page_width'], 'h': formatting['dimensions']['page_height']}]
      #print('background location', locations)
    else:
      locations = get_images_locations(page_images, layout, has_text, formatting, packed_images, cred=False)
      #print('locations',locations)
    for image,location in zip(page_images,locations):
      image_to_display = image
      backend.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], link = '', crop_images=crop_images)

  # credit images:
  if len(credit_images):
    locations = get_images_locations(credit_images, layout, has_text, formatting, packed_images, cred=True)
    # print("credit_images", credit_images)
    for image, location in zip(page_images, locations):
      backend.image(
          image,
          x=location['x0'],
          y=location['y0'],
          w=location['w'],
          h=location['h'],
          link='',
          crop_images=crop_images
      )

  return 

# TODO: remove layout, as its included in "formatting".

def get_images_locations(images, layout, has_text, formatting, packed_images=False, cred=False):
    locations = []
    image_area = get_image_area(layout, has_text, formatting)

    cred_aspect_ratio = 1.05
    cred_fraction = 0.8
    if cred:
        image_area = get_offsets_for_text(layout)
        cred_image_height = int(cred_fraction * formatting['dimensions']['page_margins']['y1'])
        image_area['y0'] = formatting['dimensions']['page_height'] - formatting['dimensions']['page_margins']['y1'] + int((formatting['dimensions']['page_margins']['y1'] - cred_image_height) / 2)
        image_area['y1'] = image_area['y0'] + cred_image_height

    image_area['w'] = image_area['x1'] - image_area['x0']
    image_area['h'] = image_area['y1'] - image_area['y0']

    MAX_SINGLE_ROW = 3  # 1 to 3 images side-by-side

    # Check for manual override from slide YAML frontmatter
    if cred:
        grid_width = len(images)
        grid_height = 1
    elif 'images_per_row' in formatting:
        grid_width = int(formatting['images_per_row'])
        grid_height = math.ceil(len(images) / grid_width)
    elif layout in ['image_center'] and len(images) <= MAX_SINGLE_ROW:
        grid_width = len(images)
        grid_height = 1
    elif len(images) == 4:
        # Explicit 2x2 for 4 images
        grid_width = 2
        grid_height = 2
    else:
        # Check aspect ratio of the actual allocated image area
        area_aspect = image_area['w'] / max(1, image_area['h'])

        if area_aspect > 1.2:
            # Wide/landscape area: bias towards more columns
            grid_width = math.ceil(math.sqrt(len(images) * area_aspect))
        else:
            # Square or tall column area (e.g. image_right_half): standard square packing
            grid_width = math.ceil(math.sqrt(len(images)))

        grid_height = math.ceil(len(images) / grid_width)

    if cred:
        tot_height = image_area['h']
        tot_width = int(image_area['h'] * cred_aspect_ratio * len(images))
        credits_align = formatting.get('credits_align', 'center')
        margin_footer = formatting['dimensions']['margin_footer']
        page_width = formatting['dimensions']['page_width']

        print('credits_align', credits_align)

        # Check if a logo is active (default logo.png is used unless logo_path is explicitly empty '')
        has_logo = True
        if 'logo_path' in formatting and formatting['logo_path'] == '':
            has_logo = False
        logo_width = 18 if has_logo else 0

        if credits_align == 'left':
            image_area['x0'] = margin_footer
        elif credits_align == 'right':
            if has_logo:
                # Align just to the left of the logo, with margin_footer gap
                logo_x = page_width - logo_width - margin_footer
                image_area['x0'] = logo_x - margin_footer - tot_width
            else:
                image_area['x0'] = page_width - margin_footer - tot_width
        else:  # 'center' (default)
            image_area['x0'] = image_area['x0'] + image_area['w'] // 2 - tot_width // 2

        image_area['x1'] = image_area['x0'] + tot_width
        image_area['w'] = image_area['x1'] - image_area['x0']
        image_area['h'] = image_area['y1'] - image_area['y0']

    marg_y = formatting['dimensions']['internal_margin'] if (not packed_images and not cred) else 0
    row_height = int((image_area['h'] - (grid_height - 1) * marg_y) / grid_height)

    marg_x = formatting['dimensions']['internal_margin'] if (not packed_images and not cred) else 0

    for i, image in enumerate(images):
        row = i // grid_width
        col = i % grid_width

        # How many images are in this specific row:
        images_in_this_row = min(grid_width, len(images) - row * grid_width)

        # Dynamic width: stretches across the row based on item count:
        current_w = int((image_area['w'] - (images_in_this_row - 1) * marg_x) / images_in_this_row)

        location = {
            'x0': image_area['x0'] + col * (current_w + marg_x),
            'y0': image_area['y0'] + row * (row_height + marg_y),
            'w': current_w,
            'h': row_height
        }
        locations.append(location)

    return locations

def get_image_area(layout, has_text, formatting):
  margin = formatting['dimensions']['internal_margin']
  y_top = formatting['dimensions']['page_margins']['y0'] + formatting['dimensions']['em_title'] + margin
  y_bottom = formatting['dimensions']['page_height'] - formatting['dimensions']['page_margins']['y1']
  drawable_height = y_bottom - y_top

  if layout in ['image_center']:
    if has_text:
      # Upper section: stops exactly (margin // 2) above the midpoint
      midpoint = y_top + (drawable_height // 2)
      image_area = {
        'x0': formatting['dimensions']['page_margins']['x0'],
        'y0': y_top,
        'x1': formatting['dimensions']['page_width'] - formatting['dimensions']['page_margins']['x1'],
        'y1': midpoint - (margin // 2)
      }
    else:
      image_area = {
        'x0': formatting['dimensions']['page_margins']['x0'],
        'y0': y_top,
        'x1': formatting['dimensions']['page_width'] - formatting['dimensions']['page_margins']['x1'],
        'y1': y_bottom
      }
  elif layout == 'image_left_half':
    image_area =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width']//2, 'y1': formatting['dimensions']['page_height']}
  elif layout == 'image_left_small':
    image_area =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    image_area =  {'x0': formatting['dimensions']['page_width']//2, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  elif layout == 'image_right_small':
    image_area =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_full
    image_area =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  #print('image_area',image_area)
  return image_area


def get_git_commit(script_home):
  p = Popen(["/usr/bin/git","log","--pretty=format:\"%H\"","-1"], cwd=script_home, stdout=PIPE, stderr=PIPE)
  res_out,res_err = p.communicate()
  git_commit = res_out.decode()
  print("{}: git commit: {}".format(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), git_commit))
  return git_commit

#def markdown_to_text(md_data):
#  parser = MarkdownIt(renderer_cls=RendererPlain)
#  return parser.render(md_data)

def recursive_dict_update(d1, d2):
  for k in d2:
    if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
      #print('dict',k,d1[k], d2[k])
      d1[k] = recursive_dict_update(d1[k], d2[k])
    else:
      #print('key not in d1 or not dict. replacing.',k,d2[k])
      d1[k] = d2[k]
  return d1

def cleanup_md_line(line):
  #line = re.sub(r'(?<!\*)\*(?![\*\s])', '__', line)
  line = re.sub(r'(?<![\\*])\*(?![\*\s])', '__', line)
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
  return line

def preprocess_md_page(content, line_number, config):
  page = {'headline': '', 'headline_h2': '', 'content': [], 'line_numbers': [], 'images': [], 'config': copy.deepcopy(config)}
  for i,line in enumerate(content):
    content[i] = cleanup_md_line(line)
    if line.startswith('[//]: # (') and line.endswith(')'):
      print('{}:{}: Ignoring markdown comment: {}'.format(md_file_stripped, line_number, line[9:-1]))
      content[i] = '' # needed to not mess up line numbers.
    #print(content[i])
          
      
    stripped_line = line.strip()
    if stripped_line.startswith('#') and (len(stripped_line) <= 1 or stripped_line[1] != '#'):
      page['headline'] = stripped_line[2:]
    elif stripped_line.startswith('##') and (len(stripped_line) <= 2 or stripped_line[2] != '#'):
      page['headline_l2'] = stripped_line[3:]

  image_lines = []
  image_line_numbers = []
  content_lines = []
  content_line_numbers = []
  page_lengths = []

  # TODO: extract images, even if line does not start with image.

  for i,line in enumerate(content):
    stripped_line = line.strip()
    if stripped_line.startswith('!['):
      image_lines.append(line)
      image_line_numbers.append(line_number+i)
    else:
      content_lines.append(line)
      content_line_numbers.append(line_number+i)
  page['images'] = image_lines
  page['content'] = content_lines
  page['line_numbers'] = content_line_numbers

  #print('images', page['images'])
  #print('content', page['content'])
  #print('line_numbers', page['line_numbers'])

  if 'incremental_bullets' not in config or not config['incremental_bullets']:
    page_lengths = [len(content_lines)]
  else:
    for content_line_number, line in enumerate(content_lines):
      stripped_line = line.strip()
      if any([stripped_line.startswith(x) for x in ['*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']]):
        page_lengths.append(content_line_number + 1)
    if not page_lengths:
      page_lengths = [len(content_lines)]

  # Find indices of images whose alt text contains the word 'incremental'
  inc_image_indices = []
  for idx, line in enumerate(image_lines):
    stripped_line = line.strip()
    if stripped_line.startswith('![') and stripped_line.endswith(')') and '](' in stripped_line[2:-1]:
      alt_text = stripped_line[2:-1].split('](')[0]
      if re.search(r'\bincremental\b', alt_text, re.IGNORECASE):
        inc_image_indices.append(idx)

  use_incremental_images = len(inc_image_indices) > 1
  num_steps = max(len(page_lengths), len(inc_image_indices) if use_incremental_images else 1)

  pages = []
  for step in range(num_steps):
    p = copy.deepcopy(page)
    page_length = page_lengths[min(step, len(page_lengths) - 1)]
    p['content'] = p['content'][:page_length]
    p['line_numbers'] = p['line_numbers'][:page_length]
    p['is_subslide'] = (step > 0)

    if use_incremental_images:
      active_img = image_lines[inc_image_indices[min(step, len(inc_image_indices) - 1)]]
      first_inc_idx = inc_image_indices[0]
      p['images'] = []
      for idx, img in enumerate(image_lines):
        if idx == first_inc_idx:
          p['images'].append(active_img)
        elif idx not in inc_image_indices:
          p['images'].append(img)

    pages.append(p)
  return pages

def get_alignment(formatting, section='text'):
  # title_align, text_align
  key = '{}_align'.format(section)
  return formatting.get(key, 'left')  

if __name__ == "__main__":
  if "--help" in sys.argv:
    print('''pymdslides usage
pymdslides [options] inputfile.md

options:
  --help             - print this message and exit
  --pdf              - produce a pdf output file
  --raster-images    - generate raster images from vector images
  --overwrite-images - overwrite images in target directory
  --downloadable     - also generate an ODP file in the HTML output folder (press 'd' in browser to download)

  Input files are formatted using markdown. you can configure the processing
  using yaml snippets either in the beginning of the file (global scope) or
  in the beginning of a slide (scoping to current slide). See below for
  allowed configuration options and their defaults.

  Putting the word 'incremental' into the alt tags for two or more images in one slide
  turns that slide into an incremental slide (realised with subslides). Each of those images
  will take up the same location as the first of them, but each of them will generate a
  separate subslide. Page number will not increase. This works together with incremental_bullets
  (see below).

  ### Configuration allowed everywhere:

  * layout: **image_center**|image_left_half|image_left_small|image_right_half|image_right_small|image_fill
  * title_full_width: true|**false**
  * title_align: **left**|center
  * title_vertical_center: true|**false**
  * text_align: **left**|center
  * credits_align: left|**center**|right
  * text_vertical_align: **top**|center|bottom
  * page_numbering: true|**false**
  * crop_images: **true**|false
  * images_per_row: <number> -- forces the number of columns in image grid layout.
  * packed_images: **true**|false
  * text_color:
      - 0
      - 0
      - 0
      -- colors are coded with RGB, 0-255, or with names, or with html hex strings (but these require quotation marks).
  * background_color:
      - 255
      - 255
      - 255
      -- colors are coded with RGB, 0-255, or with names, or with html hex strings (but these require quotation marks).
  * link_color:
      - 0
      - 0
      - 255
      -- colors are coded with RGB, 0-255, or with names, or with html hex strings (but these require quotation marks).
  * background_image: path_to_background_image_file.png
  * footer: Made with PYMDSLIDES
  * footer_append: true|**false**
      -- Specifies wether the footer should be appended to the global footer, or replace it (default).
  * footer_color:
      - 128
      - 128
      - 128
      -- colors are coded with RGB, 0-255, or with names, or with html hex strings (but these require quotation marks).
  * logo_path: logo_path.png
  * columns: integer_value, the number of columns for content
  * incremental_bullets: true|**false**
  * l4_box_fill_color:
      - 230
      - 240
      - 255
      -- colors are coded with RGB, 0-255, or with names, or with html hex strings (but these require quotation marks).
  * fonts:
      - font_file_standard: Path to supported font file
      - font_name_standard: Name of standard font
      - font_file_title: Path to supported font file
      - font_name_title: Name of title font
      - font_file_footer: Path to supported font file
      - font_name_footer: Name of footer font
      -- pymdfiles will work without specifying fonts. If files are specified but not font names, names will be guessed from file names.

  ### Document-wide configuration

  * dimensions:
      - em: 18
      - em_title: 26
      - font_size_footer: 12
      - font_size_standard: 34
      - font_size_subtitle: 40
      - font_size_title: 72
      - internal_margin: 10
      - margin_footer: 4
      - page_height: 270
      - page_margins:
          x0: 30
          x1: 30
          y0: 40
          y1: 40
      - page_width: 480
      - pixel_per_mm: 0.15
      - footer_em: 6

Available colors: white, grey, black, orange, red, green, blue, yellow, purple, pink, darkorange, darkred, darkgreen, darkblue, darkpurple, lightgrey, lightpink, lightgreen, lightblue.

  ''');
    sys.exit()

  md_file = ''
  for i in range(len(sys.argv)-1, 0, -1):
    md_file = sys.argv[i]
    if md_file.startswith('--') or md_file == 'html' or md_file == 'odp':
      continue
    else:
      break
  print('md_file:',md_file)
  output_format = 'html'
  if '--odp' in sys.argv:
    print('Using the OpenDocument odp output format.')
    output_format = 'odp'
  if not md_file.endswith('.md'):
    md_file += '.md'
  output_file = os.path.join('.'.join(md_file.split('.')[:-1]),'index.'+output_format)
  md_file_stripped = md_file.split('/')[-1]

  raster_images = False
  if '--raster-images' in sys.argv or output_format == 'html':
    raster_images = True
  if output_format == 'html':
    treat_as_raster_images = ['svg']
  else:
    treat_as_raster_images = []
    
  overwrite_images = False
  if '--overwrite-images' in sys.argv or '-o' in sys.argv:
    overwrite_images = True

  downloadable = '--downloadable' in sys.argv
  
  script_home = os.path.dirname(os.path.realpath(__file__))
  print('script_home', script_home)

  document_title = ""

  with open(md_file, 'r') as f:
    md_contents = f.read()
  content = []
  # default formatting:
  formatting = {'layout': default_layout, 'crop_images': default_crop, 'dimensions': default_dimensions}
  #print('initial formatting', yaml.dump(formatting))
  config_file = os.path.join(script_home, 'config.yaml')
  if os.path.exists(config_file):
    print('Reading default config in {}.'.format(config_file))
    with open(config_file, 'r') as f:
      default_config = yaml.safe_load(f.read())
    formatting = recursive_dict_update(formatting, default_config)

  #print(yaml.dump(formatting))

  # PREPROCESSING LOOP. TAKE CARE OF CONFIGURATION AND INCREMENTAL BULLETS.
  # will produce a list preprocessed_md of one dict per page.
  # d = {headline: str, headline_h2: str, lines: [str], line_numbers: [int], config: str}
  #
  # will also produce one list headlines and one list headlines_h2
  

  global_formatting = {}
  md_contents_lines = md_contents.split('\n')

  preamble=True
  current_yaml = ''
  page_number = 0

  preprocessed_md = []

  yaml_start_line = -1

  for line_number, line in enumerate(md_contents_lines):
    is_h1 = line.startswith('#') and (len(line) <= 1 or line[1] != '#')

    if current_yaml:
      if is_h1:
        raise SyntaxError(
            f"Line {line_number + 1}: Encountered slide headline '{line}' inside an unclosed YAML block "
            f"(started on line {yaml_start_line + 1}). Did you forget a closing '---'?"
        )
      current_yaml += '\n' + line
    elif is_h1:
      if preamble:
        # Preamble before first '#' is global for the whole document:
        global_formatting = copy.deepcopy(formatting)
        content = [line]
        preamble = False
      else:
        preprocessed = preprocess_md_page(content, previous_headline, formatting)
        preprocessed_md += preprocessed
        # Strictly revert to global formatting for the new slide:
        formatting = copy.deepcopy(global_formatting)
        content = [line]
      print('headline', line)
      previous_headline = line_number
    elif line.strip() == '---':
      current_yaml = '---'
      yaml_start_line = line_number
    else:
      content.append(line)

    if len(current_yaml) > 3 and current_yaml.strip().endswith('---'):
      yaml_body = current_yaml.strip()[3:-3]
      try:
        new_formatting = yaml.safe_load(yaml_body)
        if new_formatting is not None:
          if not preamble and 'footer' in new_formatting:
            should_append = new_formatting.get('footer_append', formatting.get('footer_append', False))
            base_footer = formatting.get('footer', '')
            slide_footer = new_formatting['footer'] or ''
            if should_append and base_footer and slide_footer:
              new_formatting['footer'] = base_footer + '&nbsp;//&nbsp;' + slide_footer
          formatting = recursive_dict_update(formatting, new_formatting)
          print('{}:{}: Updating formatting from Yaml syntax: \n  {}'.format(
              md_file_stripped, line_number, yaml_body.replace('\n', '\n  ')))
      except Exception as e:
        raise SyntaxError(
            f"Line {line_number + 1}: Incorrect YAML formatting information: {yaml_body}\nMore information: {e}"
        )
      current_yaml = ''
      yaml_start_line = -1

  # Also catch an unclosed YAML block at the very end of the file:
  if current_yaml:
    raise SyntaxError(
        f"Line {yaml_start_line + 1}: Unclosed YAML block at end of file. Missing closing '---'."
    )

  # last page:
  preprocessed = preprocess_md_page(content, previous_headline, formatting)
  #print('preprocessed',preprocessed)
  preprocessed_md += preprocessed

  headlines = []
  headlines_h2 = []
  for page in preprocessed_md:
    if 'hidden' in page['config'] and page['config']['hidden']:
      continue
    headlines.append(page['headline'])
    headlines_h2.append(page['headline_h2'])
    if headlines[-1] == '':
      headlines[-1] = headlines_h2[-1]
  print('headlines',headlines)

  document_title = headlines[0]+' '+headlines_h2[0].strip()
  if document_title == '':
    document_title = 'PYMD HTML SLIDES'
  # INITIALIZE FPDF:

  if output_format == 'html':
    odp_download_name = os.path.splitext(md_file_stripped)[0] + '.odp' if (downloadable and output_format == 'html') else None

    print('backend_html('+md_file_stripped, formatting, script_home+', overwrite_images='+str(overwrite_images)+', downloadable_odp='+str(odp_download_name)+')')
    backend = backend_html(md_file_stripped, formatting, script_home, overwrite_images=overwrite_images, downloadable_odp=odp_download_name)
  elif output_format == 'odp':
    print('backend_odp('+md_file_stripped, formatting, script_home+', overwrite_images='+str(overwrite_images)+')')
    backend = backend_odp(md_file_stripped, formatting, script_home, overwrite_images=overwrite_images)
  else:
    raise Exception('Dude! Unknown output format: '+output_format)

  logo_path = os.path.join(script_home,'logo.png')
  if 'logo_path' in formatting:
    if formatting['logo_path'] == '':
      logo_path = None
    elif os.path.exists(os.path.join(script_home,formatting['logo_path'])):
      logo_path = os.path.join(script_home,formatting['logo_path'])
    else:
      logo_path = formatting['logo_path']
  
  logo_width=18
  logo_height=23
  if logo_path is not None:
    backend.set_logo(logo_path, x=formatting['dimensions']['page_width']-logo_width-formatting['dimensions']['margin_footer'], y=formatting['dimensions']['page_height']-logo_height-formatting['dimensions']['margin_footer'] , w=logo_width, h=logo_height)

  # MAIN PROCESSING LOOP.

  #print('\n'.join(preprocessed_md_contents))
  display_page_number = 0
  for page_number, page in enumerate(preprocessed_md):
    if 'hidden' in page['config'] and page['config']['hidden']:
      print('------------------------------------\n{}:{}: This page is hidden. Will not generate page.'.format(md_file_stripped, page['line_numbers'][0]))
      continue
    #print(page['headline'])
    #print(yaml.dump(page['config']))
    # supporting single asterixes for italics in markdown.

    if not page.get('is_subslide', False):
      display_page_number += 1

    print('{}:{}: generating page (#) {}'.format(md_file_stripped, page['line_numbers'][-1], page_number))
    dump_page_content(backend, page['images']+page['content'], page['config'], headlines, raster_images, treat_as_raster_images, md_file_stripped, page['line_numbers'][0], display_page_number)
    print('------------------------------------')


  # POST PROCESSING. LOGGING GIT COMMIT.

  git_commit = get_git_commit(script_home)

  backend.set_title(document_title)
  backend.set_producer('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  backend.set_creator('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  backend.set_creation_date(datetime.now(datetime.now().astimezone().tzinfo))

  backend.output()

  if downloadable and output_format == 'html':
    print('Generating downloadable ODP file...')
    odp_backend = backend_odp(md_file_stripped, copy.deepcopy(formatting), script_home, overwrite_images=overwrite_images)
    # put_images_on_page references the module-level `backend` variable
    backend = odp_backend

    if logo_path is not None:
      backend.set_logo(logo_path, x=formatting['dimensions']['page_width']-logo_width-formatting['dimensions']['margin_footer'], y=formatting['dimensions']['page_height']-logo_height-formatting['dimensions']['margin_footer'], w=logo_width, h=logo_height)

    display_page_number = 0
    for page_number, page in enumerate(preprocessed_md):
      if 'hidden' in page['config'] and page['config']['hidden']:
        continue
      if not page.get('is_subslide', False):
        display_page_number += 1

      dump_page_content(backend, page['images']+page['content'], copy.deepcopy(page['config']), headlines, False, [], md_file_stripped, page['line_numbers'][0], display_page_number)

    backend.set_title(document_title)
    backend.set_producer('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
    backend.set_creator('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
    backend.set_creation_date(datetime.now(datetime.now().astimezone().tzinfo))
    backend.output()

    # Ensure the generated .odp is placed in the HTML output directory with the expected filename
    html_output_dir = os.path.dirname(output_file)
    target_odp = os.path.join(html_output_dir, odp_download_name)
    for candidate in [
        getattr(backend, 'odp_output_filename', None),
        os.path.join(html_output_dir, 'index.odp'),
        odp_download_name,
    ]:
      if candidate and os.path.exists(candidate) and os.path.abspath(candidate) != os.path.abspath(target_odp):
        shutil.move(candidate, target_odp)
        print('Moved ODP to', target_odp)
        break

  if '--pdf' in sys.argv:
    pdf_file_final = '.'.join(md_file.split('.')[:-1])+'.pdf'
    pdf_file = '.'.join(md_file.split('.')[:-1])+'-pre-cropping.pdf'
    pdf_file_post_cropping = '.'.join(md_file.split('.')[:-1])+'-pre-cropping-fixed-margins.pdf'
    executables = ['chrome','chromium',None]
    for executable in executables:
      if executable is None:
        print('error: found no supported browser to generate pdf. supported: {}'.format(executables[:-1]))
        break
      if shutil.which(executable) is not None:
        print('{} exists on the system'.format(executable))
        break
    if executable is not None:
      command = '{} --headless --disable-gpu --print-to-pdf={} {}'.format(executable, pdf_file, output_file) # output_file is the html target.
      print(command)
      os.system(command)

      executables = ['pdfjam',None]
      for executable in executables:
        if executable is None:
          print('error: did not find pdfjam. will not be able to fix margins in generated pdf.')
          break
        if shutil.which(executable) is not None:
          print('{} exists on the system', executable)
          break
      if executable is not None:
        command = 'pdfjam --quiet --keepinfo --papersize \'{{159mm,89mm}}\' --trim \'2mm 1mm 1mm 1mm\' --clip true --suffix "fixed-margins" {}'.format(pdf_file)
        print(command)
        os.system(command)
        command = 'mv {} {}'.format(pdf_file_post_cropping, pdf_file_final)
        print(command)
        os.system(command)


