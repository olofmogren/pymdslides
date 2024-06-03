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
from PIL import Image, ImageOps
#import matplotlib
#import matplotlib.pyplot as plt
#from matplotlib import rcParams
#rcParams['text.usetex'] = True
#import numpy as np
from subprocess import Popen,PIPE
from datetime import datetime

import cairosvg
from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw.pagemerge import RectXObj
import shutil
import yaml
import copy
#from markdown_it import MarkdownIt
#from mdit_plain.renderer import RendererPlain
from backend_pdf import backend_pdf
from backend_html import backend_html
from fpdf import FPDF # still required for vector images on pdf backend.

import copy

layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']

default_text_color= [0,0,0]
default_layout = 'center'
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

def dump_page_content(backend, content, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number):
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
        if backend.get_format() == 'pdf':
          if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
	    # a hack. assumes that if we have selected a font, it is a unicode enabled font, with the bullet symbol.
            if line.startswith('* '):
              # pretty bullet symbols
              line = '• '+line[2:]
        l4_lines.append(line)
      else:
      #elif line:
        if backend.get_format() == 'pdf':
          if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
          # a hack. assumes that if we have selected a font, it is a unicode enabled font, with the bullet symbol.
            if line.startswith('* '):
              # pretty bullet symbols
              line = '• '+line[2:]
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
  return render_page(backend, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number)

def render_page(backend, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, treat_as_raster_images, md_file_stripped, line_number):
  print('{}:{}: rendering page "{}"'.format(md_file_stripped, line_number, title))
  lines = strip_lines(lines)
  vector_images = []
  text_color = default_text_color
  if 'text_color' in formatting:
    print('{}:{}: text_color {}'.format(md_file_stripped, line_number, formatting['text_color']))
    text_color = formatting['text_color']
  #if 'background_color' in formatting and not same_color(formatting['background_color'], [255,255,255]):
  if 'background_color' not in formatting:
    formatting['background_color'] = [255,255,255]

  backend.set_background_color(formatting['background_color'])
  backend.set_text_color(text_color)

  packed_images = True
  if 'background_image' in formatting:
    print('{}:{}: background_image {}'.format(md_file_stripped, line_number, formatting['background_image']))
    vec_imgs = put_images_on_page(md_file_stripped, line_number, [formatting['background_image']], [''], formatting['layout'], len(lines) > 0, packed_images, True, background=True, raster_images=raster_images, treat_as_raster_images=treat_as_raster_images)
    vector_images += vec_imgs

  if 'packed_images' in formatting and formatting['packed_images'] == False:
    packed_images = False
  print('{}:{}: crop_images {}'.format(md_file_stripped, line_number, formatting['crop_images']))
  vec_imgs = put_images_on_page(md_file_stripped, line_number, images, alt_texts, formatting['layout'], len(lines) > 0, packed_images, formatting['crop_images'], background=False, raster_images=raster_images, treat_as_raster_images=treat_as_raster_images)
  # vector images are saved to put on the page using pdf_rw afterwards.
  vector_images += vec_imgs
  
  offsets = get_offsets(formatting['layout'])
  x = offsets['x0']
  y = offsets['y0']

  # if title_vertical_center, put it in middle of page
  if 'title_vertical_center' in formatting and formatting['title_vertical_center']: # and formatting['layout'] in ['image_full', 'image_left_half', 'image_left_small', 'image_right_half', 'image_right_full']:
    y = formatting['dimensions']['page_height']//2-int(1.5*formatting['dimensions']['em_title'])
  if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
    print('Setting font title with size',formatting['dimensions']['font_size_title'])
    backend.set_font('font_title', '', formatting['dimensions']['font_size_title'])
  else:
    print('Setting font size title',formatting['dimensions']['font_size_title'])
    backend.set_font_size(formatting['dimensions']['font_size_title'])
  # CENTERING TITLE:
  #if formatting['layout'] == 'center':
  #  width = backend.get_string_width(title)
  #  centering_offset = round((offsets['w']-width)/2)
  #  print('title','"{}"'.format(title))
  #  print('title width',width,'x',x,'centering_offset',centering_offset)
  #  print('offsets', offsets)
  #  x = x+centering_offset
  # MOVED TO BACKEND

  backend.set_xy(x,y)
  backend.textbox(lines=[title], x=x, y=y, w=offsets['w'], h=int(formatting['dimensions']['em_title']*1.2), h_level=1, headlines=headlines, text_color=text_color, align=get_alignment(formatting), markdown_format=False)
  x = offsets['x0']
  y += formatting['dimensions']['em_title']

  if subtitle:
    x_subtitle = x
    if get_alignment(formatting) == 'left':
      x_subtitle = x+formatting['dimensions']['em']
    y_subtitle = y-formatting['dimensions']['em_title']//5
    if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
      print('set_font, subtitle, 198')
      backend.set_font('font_title', '', formatting['dimensions']['font_size_subtitle'])
    else:
      backend.set_font_size(formatting['dimensions']['font_size_subtitle'])

    # CENTERING SUBTITLE:
    #if formatting['layout'] == 'center':
    #  x_subtitle = x
    #  width = backend.get_string_width(subtitle)
    #  centering_offset = round((offsets['w']-width)/2)
    #  print('subtitle','"{}"'.format(subtitle))
    #  print('subtitle_width',width,'x',x,'centering_offset',centering_offset)
    #  print('offsets', offsets)
    #  x_subtitle = x_subtitle+centering_offset
    # MOVED TO BACKEND

    backend.set_xy(x_subtitle,y_subtitle)
    backend.textbox(lines=[subtitle], x=x_subtitle, y=y_subtitle, w=offsets['w'], h=int(formatting['dimensions']['em_subtitle']*1.5), h_level=2, headlines=headlines, text_color=text_color, align=get_alignment(formatting), markdown_format=False)
  x = offsets['x0']
  y += formatting['dimensions']['em_title']

  print('images', len(images))
  offsets = get_offsets_for_text(formatting['layout'], images=(len(images) > 0))
  column_offsets = offsets
  if 'columns' in formatting and formatting['columns'] > 1:
    column_offsets = get_column_offsets(offsets, formatting['columns'], column=0)
  x = column_offsets['x0']
  y = column_offsets['y0']
  column = 0
  current_table = []
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    backend.set_font('standard', '', formatting['dimensions']['font_size_standard'])
  else:
    backend.set_font_size(formatting['dimensions']['font_size_standard'])
  print('textbox', offsets)
  backend.textbox(lines=lines, x=x, y=y, w=offsets['w'], h=offsets['h'], headlines=headlines, h_level=None, text_color=text_color, align=get_alignment(formatting), markdown_format=True)
#  for line in lines:
#    #column_offsets = offsets
#    column_divider = False
#    if 'columns' in formatting and formatting['columns'] > 1:
#      if len(line) > 3 and all([c == '-' for c in line]) and column < formatting['columns']-1:
#        column += 1
#        column_offsets = get_column_offsets(offsets, formatting['columns'], column)
#        column_divider = True
#        x = column_offsets['x0']
#        y = column_offsets['y0']
#    #print('offsets:', column_offsets)
#    #print('line:', line)
#    if len(line) > 1 and line[0] == '|' and line[-1] == '|':
#      print('{}:{}:detected table {}'.format(md_file_stripped, line_number, line))
#      current_table.append(line[1:-1].split('|'))
#      continue
#    elif(len(current_table)):
#      print('{}:{}: rendering table'.format(md_file_stripped, line_number))
#      x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
#      current_table = []
#    #print('column_offsets',column_offsets)
#    x, y = position_and_render_text_line(line, x, y, column_offsets, headlines, text_color, formatting, column_divider=column_divider)
#  if(len(current_table)):
#    print('{}:{}: rendering table'.format(md_file_stripped, line_number))
#    x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
#    current_table = []
  if 'footer' in formatting:
    backend.set_text_color(formatting.get('footer_color', default_footer_color))
    if 'fonts' in formatting and 'font_file_footer' in formatting['fonts']:
      backend.set_font('font_footer', '', formatting['dimensions']['font_size_footer'])
    else:
      backend.set_font_size(formatting['dimensions']['font_size_footer'])
    #x = formatting['dimensions']['page_width']//2-backend.get_string_width(formatting['footer'])//2
    x = formatting['dimensions']['margin_footer']
    backend.text(txt=formatting['footer'], x=x, y=formatting['dimensions']['page_height']-formatting['dimensions']['margin_footer']-formatting['dimensions']['em_footer'], em=formatting['dimensions']['em_footer'], footer=True) #, w=offsets['w'], align='L')
#    backend.set_text_color(text_color)
#  elif(len(current_table)):
#    print('{}: {}: rendering table'.format(md_file_stripped, line_number))
#    x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
#    current_table = []
# MOVED TO BACKEND

#  if len(l4_boxes):
#    backend.l4_boxes(l4_boxes, , x, y, w, h, align='left')
  if len(l4_boxes):
    print('{}:{}: l4_boxes: \n  {}'.format(md_file_stripped, line_number, yaml.dump(l4_boxes).replace('\n', '\n  ')))
  box_offsets_list = []
  for i,lines in enumerate(l4_boxes):
    box_width = int(.5*formatting['dimensions']['page_width'])
    box_x = formatting['dimensions']['page_width']//2-box_width//2
    box_height = formatting['dimensions']['em']*(len(lines))+formatting['dimensions']['internal_margin']*2
    box_y = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']-box_height
    box_offsets_list.append({'x0': box_x, 'y0': box_y, 'w': box_width, 'h': box_height})
  for i in range(len(box_offsets_list)):
    i_box_offset = box_offsets_list[i]
    y_offset = 0
    for j in range(i+1, len(box_offsets_list)):
      j_box_offset = box_offsets_list[j]
      y_offset += j_box_offset['h']+formatting['dimensions']['internal_margin']
    box_offsets_list[i]['y0'] = box_offsets_list[i]['y0']-y_offset
#
  for i,(lines,box_offsets) in enumerate(zip(l4_boxes,box_offsets_list)):
    with backend.local_context(fill_opacity=0.75, stroke_opacity=0.75):
      backend.l4_box(lines, box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], headlines, align=get_alignment(formatting), border_color=default_l4_box_border_color, border_opacity=0.75, background_color=default_l4_box_fill_color, background_opacity=0.75, markdown_format=True, text_color=[0,0,0])
    #print('backend.rect(',box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], 'round_corners=True', 'style="D"',')')
    #x = box_offsets['x0']+formatting['dimensions']['internal_margin']
    #y = box_offsets['y0']+formatting['dimensions']['internal_margin']
    #for line in lines:
    #  x, y = position_and_render_text_line(line, x, y, box_offsets, headlines, text_color, formatting, column_divider=False)
    # MOVED TO BACKEND
  return vector_images

def preprocess_formatting(formatting):
  for color in ['background_color', 'text_color', 'footer_color', 'l4_box_fill_color']:
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
      elif formatting[color] == 'darkred':
        formatting[color] = [100,0,0]
      elif formatting[color] == 'darkgreen':
        formatting[color] = [0,100,0]
      elif formatting[color] == 'darkblue':
        formatting[color] = [0,0,100]
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

def render_internal_link(link, x, y, headlines):
  #print(link)
  x_origin = x
  link = link.replace('&nbsp;', ' ')
  splitted = link.split('](#')
  link_text = splitted[0][1:]
  target = splitted[1][:-1]
  print('link', '"'+link_text+'","'+target+'"')
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    backend.set_font('standard', 'u', formatting['dimensions']['font_size_standard'])
  else:
    backend.set_font('helvetica', 'u', formatting['dimensions']['font_size_standard'])
    #backend.set_font_size(formatting['dimensions']['font_size_standard'])
  backend.set_xy(x,y)
  page_number = headlines.index(target)+1
  #print(headlines)
  print('page_number', page_number, 'target', target)
  link_ref = backend.add_link(page=page_number)
  backend.cell(txt=link_text, link=link_ref, markdown=True)
  x = backend.get_x()
  # workaround. x has a distance, similar to a space after the link.
  space_width = backend.get_string_width(' ')
  x = round(x-0.7*space_width)
  return x, y


def get_offsets_for_text(layout, images=True):
  # returns offsets for text area.
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']
  if layout in ['center', 'image_center']:
    y = formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2
    drawable_height = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y0']-formatting['dimensions']['em_title']-formatting['dimensions']['page_margins']['y1']
    if images:
      drawable_height = drawable_height//2
      y += formatting['dimensions']['internal_margin']//2
      y += drawable_height
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': y, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_half':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_small':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_small':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_fill
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
    #offsets =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  offsets['w'] = offsets['x1']-offsets['x0']
  offsets['h'] = offsets['y1']-offsets['y0']
  return offsets

def get_offsets(layout):
  # returns offsets for text area.
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center','image_fill']
  if layout in ['center', 'image_center']:
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

def put_images_on_page(md_file_stripped, line_number, images, alt_texts, layout, has_text, packed_images, crop_images, background=False, raster_images=False, treat_as_raster_images=[]):
  vector_graphics = []
  #print('crop_images', crop_images)
  #print('put_images_on_page()', 'layout', layout)
  if len(images) == 0:
    return vector_graphics
  # print("images", images,alt_texts)
  images_to_remove = []
  for i,(image,alt_text) in enumerate(zip(images,alt_texts)):
    if (image == "" or not os.path.isfile(image)) and '://' not in image:
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
      locations = get_images_locations(page_images, layout, has_text, packed_images, cred=False)
      #print('locations',locations)
    for image,location in zip(page_images,locations):
      image_to_display = image
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
          vector_graphics.append((backend.pages_count-1, image, location))
      if not is_vector_format(image) or raster_images or os.path.splitext(image)[1] in treat_as_raster_images:
        backend.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], link = '', crop_images=crop_images)

  # credit images:
  if len(credit_images):
    locations = get_images_locations(credit_images, layout, has_text, packed_images, cred=True)
    # print("credit_images", credit_images)
    for image,location in zip(credit_images,locations):
      backend.image(image, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], link = '', crop_images=True)
  return vector_graphics

def is_vector_format(filename):
  return filename.split('#')[0][-3:] in ['pdf', '.ps', 'eps', 'svg']

def get_images_locations(images, layout, has_text, packed_images=False, cred=False):
  # layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']
  #print('get_images_locations()', 'layout', layout)
  locations = []
  image_area = [0,0,formatting['dimensions']['page_width'],formatting['dimensions']['page_height']]
  #print('formatting['dimensions']['page_margins']',formatting['dimensions']['page_margins'])
  #print('layout',layout)
  image_area = get_image_area(layout, has_text)

  #print('num_images', len(images))
  #print('cred', cred)
  cred_aspect_ratio = 1.05 # /1.1
  cred_fraction = 0.6 # TODO: set reasonable constant somewhere, or let it be configurable.
  if cred:
    image_area = get_offsets_for_text(layout)
    cred_image_height = int(cred_fraction*formatting['dimensions']['page_margins']['y1'])
    image_area['y0'] = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']+int((formatting['dimensions']['page_margins']['y1']-cred_image_height)/2)
    image_area['y1'] = image_area['y0']+cred_image_height

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
    tot_width = int(image_area['h']*cred_aspect_ratio*len(images))
    image_area['x0'] = image_area['x0']+image_area['w']//2-tot_width//2
    image_area['x1'] = image_area['x0']+tot_width
    image_area['w'] = image_area['x1']-image_area['x0']
    image_area['h'] = image_area['y1']-image_area['y0']

  #print('image area size:', image_area['w'], image_area['h'], 'image grid:', grid_width, grid_height, 'margin',formatting['dimensions']['internal_margin'])
  image_size = {'w': int(image_area['w']/grid_width),
                'h': int(image_area['h']/grid_height)}
  if not packed_images and not cred:
    image_size = {'w': int((image_area['w']-(grid_width-1)*formatting['dimensions']['internal_margin'])/grid_width),
                  'h': int((image_area['h']-(grid_height-1)*formatting['dimensions']['internal_margin'])/grid_height)}
  
  #print('image_size', image_size)
  for i,image in enumerate(images):
    pos_x = i % grid_width
    pos_y = i // grid_width
    marg_x = 0
    if not packed_images and not cred:
      marg_x = formatting['dimensions']['internal_margin']
    marg_y = 0
    if not packed_images and not cred:
      marg_y = formatting['dimensions']['internal_margin']
    #print('image-grid:', pos_x, pos_y, marg_x, marg_y)
    #location  = {'x0': image_area['x0']+pos_x*image_size['w']+marg_x, 'y0': image_area['y0']+pos_y*image_size['h']+marg_y, 'w': image_size['w']-marg_x, 'h': image_size['h']-marg_y}
    location  = {'x0': image_area['x0']+pos_x*(image_size['w']+marg_x),
                 'y0': image_area['y0']+pos_y*(image_size['h']+marg_y),
                 'w': image_size['w'],
                 'h': image_size['h']}
    #print('location',location)
    locations.append(location)
  return locations

def get_image_area(layout, has_text):
  if layout in ['center', 'image_center']:
    drawable_height = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y0']-formatting['dimensions']['em_title']-formatting['dimensions']['page_margins']['y1']
    if has_text:
      image_area = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': drawable_height//2+formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']-formatting['dimensions']['internal_margin']//2}
    else:
      image_area = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']+formatting['dimensions']['internal_margin']*2, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
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

def put_vector_images_on_pdf_with_crop(output_file, vector_images, crop_images):
  reader = PdfReader(output_file)
  area = RectXObj(reader.pages[0])
  #print('reader area', area.w, area.h)
  points_per_mm = area.w/formatting['dimensions']['page_width']
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
        image_file_pdf = '/tmp/pymdslides_tmp_file'
        image_file_pdf += '-'+str(time.time())+'.backend'
        if image_file[-3:] == 'svg':
          cairosvg.svg2pdf(url=image_file, write_to=image_file_pdf)
        if image_file[-3:] == 'eps':
          os.system('epstopdf '+image_file+' -o '+image_file_pdf)
        elif image_file[-3:] == 'backend':
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
        #print(formatting['dimensions']['page_height'],desired_y,points_per_mm,image_height)
        image_pdf_page_xobj.y = (formatting['dimensions']['page_height']-desired_y-desired_height)*points_per_mm
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

  print('pdfrw writing', output_file)
  writer.write(output_file)


def put_vector_images_on_pdf(output_file, vector_images, crop_images):
  reader = PdfReader(output_file)
  area = RectXObj(reader.pages[0])
  #print('reader area', area.w, area.h)
  points_per_mm = area.w/formatting['dimensions']['page_width']
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
        image_pdf_page_xobj.y = (formatting['dimensions']['page_height']-desired_y-desired_height)*points_per_mm
        #image_pdf_page_xobj.y = 50
        #print('positioned area', image_pdf_page_xobj.x, image_pdf_page_xobj.y, image_pdf_page_xobj.w, image_pdf_page_xobj.h)
        PageMerge(writer.pagearray[i]).add(image_pdf_page_xobj, prepend=False).render()
        if image_file_pdf != image_file:
          print('remove(',image_file_pdf,')')
          os.remove(image_file_pdf)
    else:  
      # workaround. needed to retain the page size for some reason.
      PageMerge(writer.pagearray[i]).render()

  print('pdfrw writing', output_file)
  writer.write(output_file)

def logo_watermark(output_file, logo_path):
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
      #print('dict',k,d1[k])
      d1[k] = recursive_dict_update(d1[k], d2[k])
    else:
      #print('key not in d1 or not dict. replacing.',k,d2[k])
      d1[k] = d2[k]
  return d1

def cleanup_md_line(line):
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
  return line

def preprocess_md_page(content, line_number, config):
  page = {'headline': '', 'headline_h2': '', 'content': [], 'line_numbers': [], 'images': [], 'config': copy.deepcopy(config)}
  for i,line in enumerate(content):
    content[i] = cleanup_md_line(line)
    if line.startswith('[//]: # (') and line.endswith(')'):
      print('{}:{}: Ignoring markdown comment: {}'.format(md_file_stripped, line_number, line[9:-1]))
      content[i] = '' # needed to not mess up line numbers.
    #print(content[i])
    if line.strip().startswith('# '):
      page['headline'] = line[2:]
    elif line.strip().startswith('## '):
      page['headline_l2'] = line[3:]

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
    for content_line_number,line in enumerate(content_lines):
      stripped_line = line.strip()
      if any([stripped_line.startswith(x) for x in ['*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']]):

        page_lengths.append(content_line_number+1)

  #print('page_lengths',page_lengths)
  pages = []
  for page_length in page_lengths:
    p = copy.deepcopy(page)
    p['content'] = p['content'][:page_length]
    p['line_numbers'] = p['line_numbers'][:page_length]
    #print('p',p)
    pages.append(p)
  return pages

def get_alignment(formatting):
  if formatting['layout'] ==  'center':
    return 'center'
  else:
    return 'left'
  #if formatting['layout'] == 'image_left_half':
  #elif formatting['layout'] == 'image_left_small':
  #elif formatting['layout'] == 'image_right_half':
  #elif formatting['layout'] ==  'image_right_small':
  #elif formatting['layout'] == 'image_center':
  #elif formatting['layout'] == 'image_fill':
  
if __name__ == "__main__":
  md_file = sys.argv[1]
  print('md_file:',md_file)
  output_format = 'html'
  if len(sys.argv) > 2:
    output_format = sys.argv[2]
  output_file = '.'.join(md_file.split('.')[:-1])+'.'+output_format
  md_file_stripped = md_file.split('/')[-1]

  raster_images = False
  if '--raster-images' in sys.argv or output_format == 'html':
    raster_images = True
  if output_format == 'html':
    treat_as_raster_images = ['svg']
    
  
  script_home = os.path.dirname(os.path.realpath(__file__))
  print('script_home', script_home)

  vector_images = {}

  document_title = ""

  with open(md_file, 'r') as f:
    md_contents = f.read()
  content = []
  # default formatting:
  formatting = {'layout': default_layout, 'crop_images': default_crop, 'dimensions': default_dimensions}
  #print('initial formatting', formatting)
  config_file = os.path.join(script_home, 'config.yaml')
  if os.path.exists(config_file):
    print('Reading default config in {}.'.format(config_file))
    with open(config_file, 'r') as f:
      default_config = yaml.safe_load(f.read())
    formatting = recursive_dict_update(formatting, default_config)

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

  previous_headline = -1
  
  for line_number,line in enumerate(md_contents_lines):
    if current_yaml:
      # this line contains a continuation of yaml content. Parsing later.
      current_yaml += '\n'+line
      #print('current_yaml',current_yaml)
    elif line.startswith('# '):
      if preamble:
        # formatting from preamble is global for whole document:
        #print('preamble. setting global formatting')
        global_formatting = copy.deepcopy(formatting)
        content = [line]
        preamble = False
      else:
        #print(yaml.dump(formatting))
        preprocessed = preprocess_md_page(content, previous_headline, formatting)
        #print('preprocessed',preprocessed)
        preprocessed_md += preprocessed
        # reset to global config.
        formatting = copy.deepcopy(global_formatting)
        content = [line]
      print('headline',line)
      previous_headline = line_number
      #current_headline = line[2:]
    elif line == '---':
      # this line begins yaml content. Parsing later.
      current_yaml = line
      #print('current_yaml',current_yaml)
    else:
      content.append(line)
    if len(current_yaml) > 3 and current_yaml[-3:] == '---':
      # this and possibly preceding lines has contained yaml content. Parse formatting yaml:
      current_yaml = current_yaml[3:-3] # remove beginning and ending three dashes (syntax)
      try:
        new_formatting = yaml.safe_load(current_yaml)
        if new_formatting is not None:
          #formatting.update(new_formatting)
          formatting = recursive_dict_update(formatting, new_formatting)
          #print('formatting', formatting)
          print('{}:{}: Updating formatting from Yaml syntax: \n  {}'.format(md_file_stripped, line_number, current_yaml.replace('\n', '\n  ')))
          #print(yaml.dump(formatting))
        else:
          print('{}:{}: Ignoring Yaml formatting configuration: \n  {}'.format(md_file_stripped, line_number, current_yaml.replace('\n', '\n  ')))
      except Exception as e:
        #print(e)
        raise SyntaxError('Line '+str(line_number)+': Incorrect YAML formatting information: '+current_yaml+'\nMore information: '+str(e))
      current_yaml = '' # reset yaml. Next line is not a continuation of a yaml configuration.

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

  if output_format == 'pdf':
    backend = backend_pdf(md_file_stripped, formatting, script_home, output_file)
  elif output_format == 'html':
    backend = backend_html(md_file_stripped, formatting, script_home, output_file)
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
  if output_format == 'html':
    logo_width=23
    logo_height=30
    if logo_path is not None:
      backend.set_logo(logo_path, x=formatting['dimensions']['page_width']-logo_width-formatting['dimensions']['margin_footer'], y=formatting['dimensions']['page_height']-logo_height-formatting['dimensions']['margin_footer'] , w=logo_width, h=logo_height)

  # MAIN PROCESSING LOOP.

  #print('\n'.join(preprocessed_md_contents))
  for page_number, page in enumerate(preprocessed_md):
    if 'hidden' in page['config'] and page['config']['hidden']:
      print('------------------------------------\n{}:{}: This page is hidden. Will not generate page.'.format(md_file_stripped, page['line_numbers'][0]))
      continue
    #print(page['headline'])
    #print(yaml.dump(page['config']))
    # supporting single asterixes for italics in markdown.

    print('{}:{}: generating page (#) {}'.format(md_file_stripped, page['line_numbers'][-1], page_number))
    # TODO: separate images and content below.
    vector_images_page = dump_page_content(backend, page['images']+page['content'], page['config'], headlines, raster_images, treat_as_raster_images, md_file_stripped, page['line_numbers'][0])
    page_number += 1
    print('------------------------------------')
    if len(vector_images_page) > 0:
      vector_images[backend.pages_count-1] = vector_images_page


  # POST PROCESSING. LOGGING GIT COMMIT.

  git_commit = get_git_commit(script_home)

  backend.set_title(document_title)
  backend.set_producer('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  backend.set_creator('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  backend.set_creation_date(datetime.now(datetime.utcnow().astimezone().tzinfo))

  print('writing file:',output_file)
  backend.output(output_file)

  # VECTOR IMAGES FOR PDF BACKEND:

  if output_format == 'pdf':
    if len(vector_images) > 0:
      print('vector_images',len(vector_images))
      #modified_output_file = output_file+'-with-graphics.pdf'
      #shutil.copyfile(output_file, modified_output_file)
      #put_vector_images_on_pdf(modified_output_file, vector_images)
      put_vector_images_on_pdf(output_file, vector_images, formatting['crop_images'])

    if logo_path and os.path.exists(logo_path) and os.path.isfile(logo_path):
      logo_watermark(output_file, logo_path)


