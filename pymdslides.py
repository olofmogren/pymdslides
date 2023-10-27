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

from fpdf import FPDF
import sys,math,time,re
from PIL import Image, ImageOps
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['text.usetex'] = True
#import latextools
import numpy as np
from subprocess import Popen,PIPE
from datetime import datetime

import cairosvg
from pdfrw import PdfReader, PdfWriter, PageMerge
from pdfrw.pagemerge import RectXObj
import shutil
import yaml
import copy
from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain

import copy

layouts = ['image_left_half', 'image_left_small', 'image_right_half', 'image_right_small', 'center', 'image_center', 'image_fill']

default_text_color= [0,0,0]
default_layout = 'center'
default_crop = True
default_tiny_footer_color= [100,100,100]
default_l4_box_border_color = 200
default_l4_box_fill_color = [230,240,255]
default_dimensions = {
        'page_width': 480,
        'page_height': 270,
        'page_margins': {'x0': 30, 'y0': 40, 'x1': 30, 'y1': 40},
        'internal_margin': 10,
        'font_size_standard': 34,
        'font_size_title': 72,
        'font_size_subtitle': 40,
        'font_size_footer': 12,
        'pixel_per_mm': .15, # magical numbers that make the text align with the equations. .15 corresponds to text size 34, .17 corresponds to text size 40
        'em': 18,
        'em_title': 26,
        'tiny_footer_em': 6,
        'margin_tiny_footer': 4,
}

def dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images, md_file_stripped, line_number):
  print('--------------------------------------')
  pdf.add_page()
  #pdf.text(txt=content, markdown=True)
  # this seems to do nothing. checking also in render_text_line.
  formatting = preprocess_formatting(formatting)
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
        if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
          # a hack. assumes that if we have selected a font, it is a unicode enabled font, with the bullet symbol.
          if line.startswith('* '):
            # pretty bullet symbols
            line = '• '+line[2:]
        l4_lines.append(line)
      else:
      #elif line:
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
  return render_page(pdf, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, md_file_stripped, line_number)

def render_page(pdf, title, subtitle, images, alt_texts, lines, l4_boxes, formatting, headlines, raster_images, md_file_stripped, line_number):
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

  pdf.set_fill_color(formatting['background_color'])
  pdf.rect(x=0, y=0, w=formatting['dimensions']['page_width'], h=formatting['dimensions']['page_height'], style='F')
  pdf.set_text_color(text_color)

  packed_images = True
  if 'background_image' in formatting:
    print('{}:{}: background_image {}'.format(md_file_stripped, line_number, formatting['background_image']))
    vec_imgs = put_images_on_page([formatting['background_image']], [''], formatting['layout'], len(lines) > 0, packed_images, True, background=True, raster_images=raster_images)
    vector_images += vec_imgs

  if 'packed_images' in formatting and formatting['packed_images'] == False:
    packed_images = False
  print('{}:{}: crop_images {}'.format(md_file_stripped, line_number, formatting['crop_images']))
  vec_imgs = put_images_on_page(images, alt_texts, formatting['layout'], len(lines) > 0, packed_images, formatting['crop_images'], background=False, raster_images=raster_images)
  vector_images += vec_imgs
  
  offsets = get_offsets(formatting['layout'])
  x = offsets['x0']
  y = offsets['y0']

  # if title is alone, put it in middle of page
  if 'title_vertical_center' in formatting and formatting['title_vertical_center']: # and formatting['layout'] in ['image_full', 'image_left_half', 'image_left_small', 'image_right_half', 'image_right_full']:
    y = formatting['dimensions']['page_height']//2-formatting['dimensions']['em_title']//2
  if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
    pdf.set_font('font_title', '', formatting['dimensions']['font_size_title'])
  else:
    pdf.set_font_size(formatting['dimensions']['font_size_title'])
  # CENTERING TITLE:
  if formatting['layout'] == 'center':
    width = pdf.get_string_width(title)
    centering_offset = round((offsets['w']-width)/2)
    print('title_width',width,x,centering_offset)
    x = x+centering_offset
  pdf.set_xy(x,y)
  pdf.text(txt=title, x=x, y=y)#, w=offsets['w'])
  x = offsets['x0']
  y += formatting['dimensions']['em_title']

  if subtitle:
    x_subtitle = x+formatting['dimensions']['em']
    y_subtitle = y-formatting['dimensions']['em_title']//2
    if 'fonts' in formatting and 'font_file_title' in formatting['fonts']:
      pdf.set_font('font_title', '', formatting['dimensions']['font_size_subtitle'])
    else:
      pdf.set_font_size(formatting['dimensions']['font_size_subtitle'])
    # CENTERING SUBTITLE:
    if formatting['layout'] == 'center':
      x_subtitle = x
      width = pdf.get_string_width(subtitle)
      centering_offset = round((offsets['w']-width)/2)
      print('subtitle_width',width,x,centering_offset)
      x_subtitle = x_subtitle+centering_offset
    pdf.set_xy(x_subtitle,y_subtitle)
    pdf.text(txt=subtitle, x=x_subtitle, y=y_subtitle)#, w=offsets['w'])
  x = offsets['x0']
  y += formatting['dimensions']['em_title']

  offsets = get_offsets_for_text(formatting['layout'], images=(len(images) > 0))
  column_offsets = offsets
  if 'columns' in formatting and formatting['columns'] > 1:
    column_offsets = get_column_offsets(offsets, formatting['columns'], column=0)
  x = column_offsets['x0']
  y = column_offsets['y0']
  column = 0
  current_table = []
  for line in lines:
    #column_offsets = offsets
    column_divider = False
    if 'columns' in formatting and formatting['columns'] > 1:
      if len(line) > 3 and all([c == '-' for c in line]) and column < formatting['columns']-1:
        column += 1
        column_offsets = get_column_offsets(offsets, formatting['columns'], column)
        column_divider = True
        x = column_offsets['x0']
        y = column_offsets['y0']
    #print('offsets:', column_offsets)
    #print('line:', line)
    if len(line) > 1 and line[0] == '|' and line[-1] == '|':
      print('{}:{}:detected table {}'.format(md_file_stripped, line_number, line))
      current_table.append(line[1:-1].split('|'))
      continue
    elif(len(current_table)):
      print('{}:{}: rendering table'.format(md_file_stripped, line_number))
      x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
      current_table = []
    #print('column_offsets',column_offsets)
    x, y = position_and_render_text_line(line, x, y, column_offsets, headlines, text_color, formatting, column_divider=column_divider)
  if 'tiny_footer' in formatting:
    pdf.set_text_color(formatting.get('tiny_footer_color', default_tiny_footer_color))
    if 'fonts' in formatting and 'font_file_footer' in formatting['fonts']:
      pdf.set_font('font_footer', '', formatting['dimensions']['font_size_footer'])
    else:
      pdf.set_font_size(formatting['dimensions']['font_size_footer'])
    #x = formatting['dimensions']['page_width']//2-pdf.get_string_width(formatting['tiny_footer'])//2
    x = formatting['dimensions']['margin_tiny_footer']
    pdf.text(txt=formatting['tiny_footer'], x=x, y=formatting['dimensions']['page_height']-formatting['dimensions']['margin_tiny_footer']) #, w=offsets['w'], align='L')
    pdf.set_text_color(text_color)
  elif(len(current_table)):
    print('{}: {}: rendering table'.format(md_file_stripped, line_number))
    x , y = render_table(current_table, x, y, column_offsets, headlines, text_color)
    current_table = []

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

  for i,(lines,box_offsets) in enumerate(zip(l4_boxes,box_offsets_list)):
    pdf.set_draw_color(formatting.get('l4_box_border_color', default_l4_box_border_color))
    pdf.set_fill_color(formatting.get('l4_box_fill_color', default_l4_box_fill_color))
    with pdf.local_context(fill_opacity=0.75, stroke_opacity=0.75):
      pdf.rect(box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], round_corners=True, style="DF", corner_radius=10)
    #print('pdf.rect(',box_offsets['x0'], box_offsets['y0'], box_offsets['w'], box_offsets['h'], 'round_corners=True', 'style="D"',')')
    x = box_offsets['x0']+formatting['dimensions']['internal_margin']
    y = box_offsets['y0']+formatting['dimensions']['internal_margin']
    for line in lines:
      x, y = position_and_render_text_line(line, x, y, box_offsets, headlines, text_color, formatting, column_divider=False)
  return vector_images

def preprocess_formatting(formatting):
  for color in ['background_color', 'text_color', 'tiny_footer_color']:
    if color in formatting:
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

def position_and_render_text_line(line, x, y, offsets, headlines, text_color, formatting, column_divider=False):
  origin_x = x
  if formatting['layout'] == 'center':
    # CENTERING LINE:
    width = get_text_line_width(line, x, y, offsets, headlines, text_color, column_divider)
    #print('centering',offsets)
    print('width', width)
    centering_offset = round((offsets['w']-width)/2)
    print('centering_offset', centering_offset)
    x = x+centering_offset
  x, y, width = render_text_line(line, x, y, offsets, headlines, text_color, column_divider)
  x = origin_x
  return x, y
    
def render_text_line(line, x, y, offsets, headlines, text_color, column_divider=False):
    #print('line:',line)
    origin_x = x
    origin_y = y
    #print(offsets)
    width = offsets['w']
    pdf.set_xy(x,y)
    if pdf.will_page_break(formatting['dimensions']['em']):
      print('line will overflow the page. not including in PDF!!!',line)
      return x,y,0
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
      y += int(0.5*formatting['dimensions']['em'])
    elif len(line) > 3 and all([c == '-' for c in line]):
      pdf.set_line_width(0.5)
      # TODO: configuration of column divider line color
      pdf.set_draw_color(160,160,160)
      if column_divider:
        x = offsets['x0']-formatting['dimensions']['internal_margin']//2
        pdf.line(x1=x, y1=offsets['y0'], x2=x, y2=offsets['y1'])
      else:
        pdf.line(x1=x, y1=y+int(0.5*formatting['dimensions']['em']), x2=x+offsets['w'], y2=y+int(0.5*formatting['dimensions']['em']))
      y += formatting['dimensions']['em']
      if column_divider:
        y = origin_y
      pdf.set_draw_color(text_color)
    else:
      pos = 0
      for tag in merged:
        if tag[0] > pos:
          pre_tag = line[pos:tag[0]-1]
          #print('rendering pre_tag', pre_tag)
          x, new_y = render_part_of_line(pre_tag, x, y)
          heights.append(formatting['dimensions']['em'])
        if tag[2] == 'latex':
          formula = line[tag[0]:tag[1]]
          x, new_y, latex_width = render_latex(formula, x, y, text_color)
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
        heights.append(formatting['dimensions']['em'])
        heights.append(new_y-origin_y)
      y = origin_y + max(heights)
      width = x-origin_x
      #print('y', origin_y, y)
    return origin_x, y, width

def get_text_line_width(line, x, y, offsets, headlines, text_color, column_divider=False):
    #print(offsets)
    #print('line', line, len(line))
    width = offsets['w']
    if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
      pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
    else:
      pdf.set_font_size(formatting['dimensions']['font_size_standard'])
    if pdf.will_page_break(formatting['dimensions']['em']):
      print('line will overflow the page. not including in PDF!!!',line)
      return width
    if line.startswith('###') and (len(line) <= 3 or line[3] != '#'):
        line = '**'+line[4:]+'**'
    latex_sections = get_latex_sections(line)
    internal_links = get_internal_links(line)
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
          new_widths.append(pdf.get_string_width(markdown_to_text(pre_tag)))
          #print('pretag width',new_widths[-1],'('+pre_tag+')')
        if tag[2] == 'latex':
          formula = line[tag[0]:tag[1]]
          x, new_y, latex_width = render_latex(formula, x, y, text_color, dry_run=True)
          new_widths.append(latex_width)
          #print('latex width',new_widths[-1],'('+formula+')')
        else: # internal link
          link = line[tag[0]:tag[1]+1]
          splitted = link.split(')[#')
          link_text = splitted[0][1:]
          new_widths.append(pdf.get_string_width(link_text))
          #print('link width',new_widths[-1],'('+link_text+')')
        pos = tag[1]+1
      if pos < len(line):
        new_widths.append(pdf.get_string_width(markdown_to_text(line[pos:])))
        #print('last part width',new_widths[-1],'('+line[pos:]+')')
    #print('sum',sum(new_widths))
    return sum(new_widths)

def render_table(table, x, y, offsets, headlines, text_color, column_divider=False):
  print('table:',table)
  origin_x = x
  origin_y = y
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
  else:
    pdf.set_font_size(formatting['dimensions']['font_size_standard'])
  # due to a bug (in my code or in pfpdf), the table is centered on the page. uncentering:
  uncentered_x = x-(formatting['dimensions']['page_width']//2-offsets['w']//2)
  pdf.set_xy(uncentered_x,y)
  pdf.set_xy(0,y)
  pdf.set_left_margin(offsets['x0'])
  with pdf.table(width=offsets['w'], align='LEFT', markdown=True) as pdf_table:
    for tr in table:
      row = pdf_table.row()
      for td in tr:
        row.cell(td)
  y += int(formatting['dimensions']['em']*len(table)*1.8)
  return origin_x, y

def render_part_of_line(part, x, y):
  #print('part', '"'+part+'"')
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
  else:
    pdf.set_font_size(formatting['dimensions']['font_size_standard'])
  pdf.set_xy(x,y)
  part = part.replace('&nbsp;', ' ')
  if not part.strip():
    pdf.text(txt=part, x=x, y=y)#, w=offsets['w'], align=align)
  else:
    #print(part)
    pdf.cell(txt=part, markdown=True)
  x = pdf.get_x()
  return x, y

def render_internal_link(link, x, y, headlines):
  #print(link)
  x_origin = x
  link = link.replace('&nbsp;', ' ')
  splitted = link.split(')[#')
  link_text = splitted[0][1:]
  target = splitted[1][:-1]
  print('link', '"'+link_text+'","'+target+'"')
  if 'fonts' in formatting and 'font_file_standard' in formatting['fonts']:
    pdf.set_font('font_standard', 'u', formatting['dimensions']['font_size_standard'])
  else:
    pdf.set_font_size(formatting['dimensions']['font_size_standard'])
  pdf.set_xy(x,y)
  page_number = headlines.index(target)+1
  #print(headlines)
  print('page_number', page_number, 'target', target)
  fpdf_link = pdf.add_link(page=page_number)
  pdf.cell(txt=link_text, link=fpdf_link, markdown=True)
  x = pdf.get_x()
  return x, y

def render_latex(formula, x, y, text_color, dry_run=False):
  return render_latex_matplotlib(formula, x, y, text_color, dry_run=dry_run)

def render_latex_latextools(formula, x, y):
    # seems impossible to import svg or pdf!
    formula = '$'+formula+'$'
    #print('formula', formula)
    # Latex!
    latex_eq = latextools.render_snippet(formula, commands=[latextools.cmd.all_math])
    #svg_eq = latex_eq.as_svg()
    tmp_f = '/tmp/pymdslides_tmp_file'
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
    #pdf.template(tmp_f, x=x, y=y, w=60, h=formatting['dimensions']['em'])
    x += width_mm
    y += height_mm-y_offset # TODO: also give the y_offset space above the line
    return x, y, width_mm

def render_latex_matplotlib(formula, x, y, text_color, dry_run=False):
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
    #pdf.image(logo_path, x=formatting['dimensions']['page_width']-30, y=formatting['dimensions']['page_height']-35, w=24, h=30)
    arbitrary_image_margin_mm = 1
    width_mm = int(im_width*formatting['dimensions']['pixel_per_mm'])
    height_mm = int(im_height*formatting['dimensions']['pixel_per_mm'])
    baseline_offset_mm = int(baseline_offset*formatting['dimensions']['pixel_per_mm'])
    #y_offset = (height_mm-formatting['dimensions']['em'])//2
    print('baseline_offset_mm', baseline_offset_mm)
    y_offset = baseline_offset_mm+arbitrary_image_margin_mm
    print('y_offset', y_offset)

    if not dry_run:
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
    return x,y,width_mm


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
    y = formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']
    drawable_height = formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y0']-formatting['dimensions']['em_title']-formatting['dimensions']['page_margins']['y1']
    if images:
      drawable_height = drawable_height//2
      y += formatting['dimensions']['internal_margin']//2
      y += drawable_height
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': y, 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_half':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_small':
    offsets =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_small':
    offsets =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_fill
    offsets = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
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
      locations = [{'x0': 0, 'y0': 0, 'w': formatting['dimensions']['page_width'], 'h': formatting['dimensions']['page_height']}]
      #print('background location', locations)
    else:
      locations = get_images_locations(page_images, layout, has_text, packed_images, cred=False)
      #print('locations',locations)
    for image,location in zip(page_images,locations):
      image_to_display = image
      if is_vector_format(image):
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
          vector_graphics.append((pdf.pages_count-1, image, location))
      if not is_vector_format(image) or raster_images:
        if crop_images:
          #image_to_display_2 = get_cropped_image_file(image_to_display, location)
          #if image_to_display_2 != image_to_display and image_to_display != image:
          #  # remove first tmp file:
          #  print('remove(',image_to_display,')')
          #  os.remove(image_to_display)
          #image_to_display = image_to_display_2
          viewpoint = location
          location = get_cropped_location(image_to_display, location)
          with pdf.rect_clip(x=viewpoint['x0'], y=viewpoint['y0'], w=viewpoint['w'], h=viewpoint['h']):
            #print('putting cropped image',image_to_display)
            pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
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
          pdf.image(image_to_display, x=location['x0'], y = location['y0'], w = location['w'], h = location['h'], type = '', link = '')
        if image_to_display != image:
          # tmpfile
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
  tmp_f = '/tmp/pymdslides_tmp_file'
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
      image_area = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': drawable_height//2+formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title']-formatting['dimensions']['internal_margin']//2}
    else:
      image_area = {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_left_half':
    image_area =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width']//2, 'y1': formatting['dimensions']['page_height']}
  elif layout == 'image_left_small':
    image_area =  {'x0': formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': (formatting['dimensions']['page_width']//2)-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  elif layout == 'image_right_half':
    image_area =  {'x0': formatting['dimensions']['page_width']//2, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
  elif layout == 'image_right_small':
    image_area =  {'x0': (formatting['dimensions']['page_width']//2)+formatting['dimensions']['page_margins']['x0'], 'y0': formatting['dimensions']['page_margins']['y0']+formatting['dimensions']['em_title'], 'x1': formatting['dimensions']['page_width']-formatting['dimensions']['page_margins']['x1'], 'y1': formatting['dimensions']['page_height']-formatting['dimensions']['page_margins']['y1']}
  else: #image_full
    image_area =  {'x0': 0, 'y0': 0, 'x1': formatting['dimensions']['page_width'], 'y1': formatting['dimensions']['page_height']}
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

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)


def put_vector_images_on_pdf(pdf_file, vector_images, crop_images):
  reader = PdfReader(pdf_file)
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

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)

def logo_watermark(pdf_file, logo_path):
  reader = PdfReader(pdf_file)
  writer = PdfWriter()
  writer.pagearray = reader.Root.Pages.Kids

  pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height'])) # 16:9
  pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height'])) # 16:9
  pdf.add_page()
  logo_width=23
  logo_height=30
  pdf.image(logo_path, x=formatting['dimensions']['page_width']-logo_width-formatting['dimensions']['margin_tiny_footer'], y=formatting['dimensions']['page_height']-logo_height-formatting['dimensions']['margin_tiny_footer'] , w=logo_width, h=logo_height)
  reader = PdfReader(fdata=bytes(pdf.output()))
  logo_page = reader.pages[0]

  for i in range(len(writer.pagearray)):
    #print('putting logo on ',i)
    PageMerge(writer.pagearray[i]).add(logo_page, prepend=False).render()

  print('pdfrw writing', pdf_file)
  writer.write(pdf_file)

def get_git_commit(script_home):
  p = Popen(["/usr/bin/git","log","--pretty=format:\"%H\"","-1"], cwd=script_home, stdout=PIPE, stderr=PIPE)
  res_out,res_err = p.communicate()
  git_commit = res_out.decode()
  print("{}: git commit: {}".format(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), git_commit))
  return git_commit

def markdown_to_text(md_data):
  parser = MarkdownIt(renderer_cls=RendererPlain)
  return parser.render(md_data)

def recursive_dict_update(d1, d2):
  for k in d2:
    if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
      #print('dict',k,d1[k])
      d1[k] = recursive_dict_update(d1[k], d2[k])
    else:
      #print('key not in d1 or not dict. replacing.',k,d2[k])
      d1[k] = d2[k]
  return d1

if __name__ == "__main__":
  md_file = sys.argv[1]
  print('md_file:',md_file)
  pdf_file = '.'.join(md_file.split('.')[:-1])+'.pdf'
  md_file_stripped = md_file.split('/')[-1]

  raster_images = False
  if '--raster-images' in sys.argv:
    raster_images = True
  
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
    #print('default config', default_config)
    #formatting.update(default_config)
    formatting = recursive_dict_update(formatting, default_config)
    #print('formatting', formatting)
    #print(formatting)

  global_formatting = {}
  preamble=True
  headlines = []
  headlines_h2 = {}
  current_yaml = ''
  for line_number,line in enumerate(md_contents.split('\n')):
    if current_yaml:
      # this line contains a continuation of yaml content. Needs to be ignored in the loop for headlines.
      current_yaml += '\n'+line
      #print('current_yaml',current_yaml)
    elif line.startswith('#') and (len(line) <= 1 or line[1] != '#'):
      if not document_title:
        document_title = line[3:].strip()
      headlines.append(line[2:].strip())
    elif line.startswith('##') and (len(line) <= 2 or line[2] != '#'):
      headlines_h2[len(headlines)-1] = line[3:].strip()
    elif line == '---':
      # this line begins yaml content. Parsing later.
      current_yaml = line
      #print('current_yaml',current_yaml)
    if len(current_yaml) > 3 and current_yaml[-3:] == '---':
      # this line ends yaml content. Parsing later.
      # TODO: dirty workaround. Other ways to hide page.
      if 'hidden: true' in current_yaml:
        headlines = headlines[:-1]
      current_yaml = ''
  for i in range(len(headlines)):
    if headlines[i] == '' and i in headlines_h2:
      headlines[i] = headlines_h2[i]
  current_yaml = ''
  page_number = 0
  for line_number,line in enumerate(md_contents.split('\n')):
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

    if current_yaml:
      # this line contains a continuation of yaml content. Parsing later.
      current_yaml += '\n'+line
      #print('current_yaml',current_yaml)
    elif line.startswith('# '):
      if preamble:
        # formatting from preamble is global for whole document:
        #print('preamble. setting global formatting')
        global_formatting = copy.deepcopy(formatting)
        content = []
        preamble = False
        pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height'])) # 16:9
        pdf.set_font('Helvetica', '', formatting['dimensions']['font_size_standard'])
        if 'fonts' in formatting:
          if formatting['fonts']['font_file_standard']:
            fname = formatting['fonts']['font_file_standard']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_standard', '', fname)
            pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
          if formatting['fonts']['font_file_standard_italic']:
            fname = formatting['fonts']['font_file_standard_italic']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_standard', 'i', fname)
          if formatting['fonts']['font_file_standard_bold']:
            fname = formatting['fonts']['font_file_standard_bold']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_standard', 'b', fname)
          if formatting['fonts']['font_file_standard_bolditalic']:
            fname = formatting['fonts']['font_file_standard_bolditalic']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_standard', 'bi', fname)
          if formatting['fonts']['font_file_footer']:
            fname = formatting['fonts']['font_file_footer']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_footer', '', fname)
          if formatting['fonts']['font_file_title']:
            fname = formatting['fonts']['font_file_title']
            if os.path.exists(os.path.join(script_home, fname)):
              fname = os.path.join(script_home, fname)
            pdf.add_font('font_title', '', fname)
        pdf.set_text_color(0,0,0)

        #pdf.set_image_filter("FlatDecode")
        pdf.oversized_images = "DOWNSCALE"
        print('{}:{}: pdf.oversized_images_ratio {}'.format(md_file_stripped, line_number, pdf.oversized_images_ratio))
      else:
        print('{}:{}: generating page (#) {}'.format(md_file_stripped, line_number, page_number))
        if 'visibility' in formatting and formatting['visibility'] == 'hidden':
          print('------------------------------------\n"{}:{}: visibility":"hidden" is deprecated. use "hidden": true instead.'.format(md_file_stripped, line_number))
          print('------------------------------------\n{}:{}: This page is hidden. Will not generate pdf page.'.format(md_file_stripped, line_number))
          vector_images_page = []

        elif 'hidden' in formatting and formatting['hidden']:
          print('------------------------------------\n{}:{}: This page is hidden. Will not generate pdf page.'.format(md_file_stripped, line_number))
          vector_images_page = []
        else:
          vector_images_page = dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images, md_file_stripped, line_number)
          page_number += 1
          print('------------------------------------')
        if len(vector_images_page) > 0:
          vector_images[pdf.pages_count-1] = vector_images_page
        # reset page-specific formatting:
        #print('resetting page-specific formatting')
        formatting = copy.deepcopy(global_formatting)
        #print(yaml.dump(formatting))
      content = [line]
      #current_headline = line[2:]
    elif line.startswith('[//]: # (') and line.endswith(')'):
      print('{}:{}: Ignoring markdown comment: {}'.format(md_file_stripped, line_number, line[9:-1]))
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


  print('{}:{}: generating page (last)'.format(md_file_stripped, line_number))
  if 'visibility' in formatting and formatting['visibility'] == 'hidden':
    print('------------------------------------\n"{}:{}: visibility":"hidden" is deprecated. use "hidden": true instead.'.format(md_file_stripped, line_number))
    print('------------------------------------\n{}:{}: This page is hidden. Will not generate pdf page.'.format(md_file_stripped, line_number))
    vector_images_page = []
  elif 'hidden' in formatting and formatting['hidden']:
    print('------------------------------------\n{}:{}: This page is hidden. Will not generate pdf page.'.format(md_file_stripped, line_number))
  else:
    vector_images_page = dump_page_content_to_pdf(pdf, content, formatting, headlines, raster_images, md_file_stripped, line_number)
    print('------------------------------------')
  if len(vector_images_page) > 0:
     vector_images[pdf.pages_count-1] = vector_images_page


  git_commit = get_git_commit(script_home)

  pdf.set_title(document_title)
  pdf.set_producer('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  pdf.set_creator('pymdslides, git commit: '+git_commit+' https://github.com/olofmogren/pymdslides/')
  pdf.set_creation_date(datetime.now(datetime.utcnow().astimezone().tzinfo))

  print('writing pdf file:',pdf_file)
  pdf.output(pdf_file)

  if len(vector_images) > 0:
    print('vector_images',len(vector_images))
    #modified_pdf_file = pdf_file+'-with-graphics.pdf'
    #shutil.copyfile(pdf_file, modified_pdf_file)
    #put_vector_images_on_pdf(modified_pdf_file, vector_images)
    put_vector_images_on_pdf(pdf_file, vector_images, formatting['crop_images'])

  logo_path = os.path.join(script_home,'logo.png')
  if 'logo_path' in formatting:
    if os.path.exists(os.path.join(script_home,formatting['logo_path'])):
      logo_path = os.path.join(script_home,formatting['logo_path'])
    else:
      logo_path = formatting['logo_path']
  if logo_path and os.path.exists(logo_path):
    logo_watermark(pdf_file, logo_path)


