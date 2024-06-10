# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.


import os, os.path, shutil, re
from lxml import etree as ET
from markdown2 import markdown
from lxml.html.soupparser import fromstring
from PIL import Image
from urllib.parse import urlparse
import requests

class backend_html:
  def __init__(self, input_file, formatting, script_home, output_file, copy_resources_to=None):
    self.output_file = output_file
    self.output_dir = os.path.dirname(output_file)
    if len(self.output_dir) > 0:
      self.output_dir += '/'
    if copy_resources_to == 'sub_dir':
      self.resources_dir = os.path.join(self.output_dir,os.path.splitext(os.path.basename(output_file))[0]+'_pymd_resources/')
    elif copy_resources_to == 'same_dir':
      self.resources_dir = self.output_dir
    else:
      self.resources_dir = None
    if self.resources_dir is not None:
      try:
        os.makedirs(self.resources_dir)
      except FileExistsError:
        pass
    self.font_files = {}
    self.font_names = {}
    self.font_sizes = {}
    for font_cat in ['title', 'standard', 'footer']:
      if 'fonts' in formatting and 'font_file_{}'.format(font_cat) in formatting['fonts']:
        ttf_file = formatting['fonts']['font_file_{}'.format(font_cat)]
        fontname = font_file_to_font_name(ttf_file)
        if 'fonts' in formatting and 'font_name_{}'.format(font_cat) in formatting['fonts']:
          fontname = formatting['fonts']['font_name_{}'.format(font_cat)]
        woff2_file = change_filename_extension(ttf_file, 'woff2')
        if not os.path.exists(os.path.join(script_home,woff2_file)):
          print(os.path.join(script_home,woff2_file), 'not found. Will try to convert ttf file.')
          from fontTools.ttLib import TTFont
          f = TTFont(os.path.join(script_home,ttf_file))
          f.flavor='woff2'
          f.save(os.path.join(script_home,woff2_file))
        if self.resources_dir is not None:
          shutil.copy(os.path.join(script_home,woff2_file), self.resources_dir)
          if self.resources_dir == self.output_dir:
            self.font_files[font_cat] = os.path.basename(woff2_file)
          else:
            self.font_files[font_cat] = self.resources_dir+os.path.basename(woff2_file)
        else:
          self.font_files[font_cat] = woff2_file
        self.font_names[font_cat] = fontname
    for font_cat in ['title', 'subtitle', 'standard', 'footer']:
      if 'dimensions' in formatting and 'font_size_{}'.format(font_cat) in formatting['dimensions']:
        self.font_sizes[font_cat] = self.html_font_size(formatting['dimensions']['font_size_{}'.format(font_cat)])
        if font_cat == 'subtitle':
          self.font_sizes[font_cat+'_l3'] = self.html_font_size(formatting['dimensions']['font_size_{}'.format(font_cat)]/1.4)
          self.font_sizes[font_cat+'_l4'] = self.html_font_size(formatting['dimensions']['font_size_{}'.format(font_cat)]/1.4)

    mathjax_url = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-svg.js'
    mathjax_local_file = os.path.join(script_home, 'mathjax', 'tex-mml-svg.js')
    if not os.path.exists(mathjax_local_file):
      print('Downloading mathjax to local storage...')
      response = requests.get(mathjax_url)
      print(response)
      os.makedirs(os.path.dirname(mathjax_local_file))
      with open(mathjax_local_file, 'wb') as f:
        f.write(response.content)
    if self.resources_dir is not None:
      if self.resources_dir == self.output_dir:
        shutil.copy(mathjax_local_file, os.path.join(self.output_dir, os.path.basename(mathjax_local_file)))
        mathjax_url = mathjax_local_file
      else:
        shutil.copy(mathjax_local_file, os.path.join(self.resources_dir, os.path.basename(mathjax_local_file)))
        mathjax_url = os.path.join(self.resources_dir, os.path.basename(mathjax_local_file))
    else:
      mathjax_url = mathjax_local_file
      
      

    default_style = '''
body {{
  overflow: hidden;
}}
@font-face {{
  font-family: {};
  src: url('{}') format('woff2');
}}
@font-face {{
  font-family: {};
  src: url('{}') format('woff2');
}}
@font-face {{
  font-family: {};
  src: url('{}') format('woff2');
}}
h1 {{
  font-family: {}, Arial, Sans-Serif;
  /*font-size: 4cqw;*/
  font-size: {};
}}
h2 {{
  font-family: {}, Arial, Sans-Serif;
  /*font-size: 2.8cqw;*/
  font-size: {};
}}
h3 {{
  font-family: {}, Arial, Sans-Serif;
  /*font-size: 2cqw;*/
  font-size: {};
}}
h4 {{
  font-family: {}, Arial, Sans-Serif;
  /*font-size: 2cqw;*/
  font-size: {};
}}
body {{
  font-family: {}, Arial, Sans-Serif;
  background-color: black;
}}
div.page_div {{
  width: 100vw;
  height: 56.25vw; /* height:width ratio = 9/16 = .5625  */
  max-height: 100vh;
  max-width: 177.78vh; /* 16/9 = 1.778 */
  margin: auto;
  position: absolute;
  top:0;
  bottom:0; /* vertical center */
  left:0;
  right:0; /* horizontal center */'
  container-type: size;
  overflow: hidden;
}}
div.subcontainer {{
  container-type: size;
  width: 100%;
  height: 100%;
  font-size: {};
}}
div.prev-page-click-div {{
  position: absolute;
  left: 0;
  top: 0;
  width: 25%;
  height: 100%;
  z-index: 7;
}}
div.next-page-click-div {{
  position: absolute;
  left: 25%;
  top: 0;
  width: 75%;
  height: 100%;
  z-index: 7;
}}
div.black_div {{
  background-color: #000;
  color: #fff;
  position: absolute;
  top:0;
  left: 0;
  width: 100vw;
  height: 100vh;
  visibility: hidden;
  z-index: 8;'
}}
'''.format(self.font_names['title'], self.font_files['title'], self.font_names['standard'], self.font_files['standard'], self.font_names['footer'], self.font_files['footer'], self.font_names['title'], self.font_sizes['title'], self.font_names['title'], self.font_sizes['subtitle'], self.font_names['title'], self.font_sizes['subtitle_l3'], self.font_names['title'], self.font_sizes['subtitle_l4'], self.font_names['standard'], self.font_sizes['standard'])
    #print('name',self.font_names['footer'])
    #print('size',self.font_sizes['footer'])
    default_style += '''div.footer {{
  font-family: {}, Arial, Sans-Serif;
  /*font-size: 1cqw;*/
  font-size: {};
}}
/*div {{
border: 1px #ccc solid;
}}
p {{
border: 1px #ccc solid;
}}*/
'''.format(self.font_names['footer'], self.font_sizes['footer'])


    default_javascript = '''
var currentPageId = "page-1";
var blackPageVar = false;
function blackPage() {
  if (blackPageVar) {
    document.getElementById('black_div').style.visibility = 'hidden';
    //alert('un-black page');
  }
  else {
    document.getElementById('black_div').style.visibility = 'visible';
    //alert('black page');
  }
  blackPageVar = !blackPageVar;
}
function mouseuphandler(e) {
  e.pageX;
  width = document.getElementById(currentPageId).offsetWidth;
  //alert(width);
  if (e.pageX < 0.25*width) {
    prevPage();
  }
  else {
    nextPage()
  }
}
function pageLoad(){
  var currentPageId = "page-1";
  newPageId = window.location.hash.substring(1);
  if (newPageId != "") {
    //if (currentPageId != newPageId){
      goToPage(newPageId);
    //}
  }
}
function prevPage(){
  splits = currentPageId.split("-");
  currentPageNumber = parseInt(splits[1]);
  prevPageNumber = currentPageNumber-1;
  pageId = "page-"+prevPageNumber;
  element = document.getElementById(pageId);
  if (element) {
    document.getElementById(currentPageId).style.visibility="hidden";
    document.getElementById(pageId).style.visibility="visible";
    currentPageId = pageId;
    window.location.hash = pageId;
  }
}
function nextPage(){
  splits = currentPageId.split("-");
  currentPageNumber = parseInt(splits[1]);
  nextPageNumber = currentPageNumber+1;
  pageId = "page-"+nextPageNumber;
  element = document.getElementById(pageId);
  if (element) {
    document.getElementById(currentPageId).style.visibility="hidden";
    document.getElementById(pageId).style.visibility="visible";
    currentPageId = pageId;
    window.location.hash = pageId;
  }
}
function goToPage(pageId){
    //alert(pageId);
    document.getElementById(currentPageId).style.visibility="hidden";
    document.getElementById(pageId).style.visibility="visible";
    currentPageId = pageId;
    window.location.hash = pageId;
}
document.onkeydown = function(event) {
  switch (event.keyCode) {
    case 33:
      // page up
      prevPage();
    break;
    case 34:
      // page down
      nextPage();
    break;
    case 37:
      // left arrow
      prevPage();
    break;
    case 38:
      // up arrow
      prevPage();
    break;
    case 32:
      //space
      nextPage();
    break;
    case 39:
      // right arrow
      nextPage();
    break;
    case 40:
      // down arrow
      nextPage();
    break;
    case 66:
      // b - blank/black
      blackPage();
    break;
    case 70:
      // f - fulscreen
      if (window.fullScreen) {
        document.exitFullscreen();
      }
      else {
        document.documentElement.requestFullscreen();
      }
    break;
  }
};
'''

    self.html = ET.Element('html')
    self.head = ET.Element('head')
    self.html.append(self.head)
    self.doc_style = ET.Element('style')
    self.doc_style.text = default_style
    self.head.append(self.doc_style)
    self.title = ET.Element('title')
    self.title.text = 'PYMD HTML SLIDES'
    self.head.append(self.title)
    self.script = ET.Element('script')
    self.script.text = default_javascript
    self.head.append(self.script)
# <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
# <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    mathjax0 = ET.Element('script')
    mathjax0.text = '''
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']]
  },
  svg: {
    fontCache: 'global'
  }
};
'''
    self.head.append(mathjax0)
    #mathjax1 = ET.Element('script')
    #mathjax1.set('src', 'https://polyfill.io/v3/polyfill.min.js?features=es6')
    #mathjax1.text = ' '
    #self.head.append(mathjax1)
    mathjax2 = ET.Element('script')
    mathjax2.set('id', 'MathJax-script')
    mathjax2.set('async', 'true')
    mathjax2.set('src', mathjax_url)
    mathjax2.text = ' '
    self.head.append(mathjax2)

    self.body = ET.Element('body')
    self.body.set('onload', 'pageLoad();')
    self.html.append(self.body)
    self.current_page_div = None

    black_div = ET.Element('div')
    black_div.set('class', 'black_div')
    black_div.set('id', 'black_div')
    #black_div.set('class', 'page_div')
    self.body.append(black_div)
    loading_div = ET.Element('div')
    style = 'margin: auto;'
    loading_span1 = ET.Element('p')
    loading_span1.text = 'Loading'
    loading_span2 = ET.Element('p')
    loading_span2.text = 'PYMD slides requires a javascript-enabled browser.'
    #br = ET.element('br')
    loading_div.append(loading_span1)
    #loading_div.append(br)
    loading_div.append(loading_span2)
    self.body.append(loading_div)

    self.page_width = formatting['dimensions']['page_width']
    self.page_height = formatting['dimensions']['page_height']

    self.text_color = dec_to_hex_color([0,0,0])

    self.oversized_images = "DOWNSCALE"
    self.downscale_resolution_width = 3840
    self.downscale_resolution_height = 2160


    self.input_file_name = input_file
    self.x = formatting['dimensions']['page_margins']['x0']
    self.y = formatting['dimensions']['page_margins']['y0']
    self.pages_count = 0
    self.formatting = formatting
    self.script_home = script_home
    self.logo = None

  def set_logo(self, logo, x, y, w, h, copy=True):
    #print('setting_logo', str(logo))
    new_filename = logo
    if copy and self.resources_dir is not None:
      if self.resources_dir == self.output_dir:
        new_filename = os.path.basename(logo)
        shutil.copyfile(logo, os.path.join(self.output_dir, new_filename))
      else:
        new_filename = os.path.join(self.resources_dir,os.path.basename(logo))
        shutil.copyfile(logo, new_filename)
    self.logo = new_filename
    self.logo_x = x
    self.logo_y = y
    self.logo_w = w
    self.logo_h = h

  def html_x(self, x):
    x_frac = x/self.page_width
    #return str(round(x_frac*100))+'%'
    return '{:.2f}%'.format(x_frac*100)

  def html_y(self, y):
    y_frac = y/self.page_height
    #return str(round(y_frac*100))+'%'
    return '{:.2f}%'.format(y_frac*100)

  def html_font_size(self, font_size):
    #print(font_size)
    result = '{:.2f}cqw'.format(font_size/16.0)
    #print(result)
    return result

  def unbreakable(self):
    class unbreakabler:
      def __init__(self):
        pass
      def __enter__(self):
        pass
      def __exit__(self, type, value, traceback):
        pass
    return unbreakabler()

  def local_context(self, *args, **kwargs):
    class local_contexter:
      def __init__(self):
        pass
      def __enter__(self):
        pass
      def __exit__(self, type, value, traceback):
        pass
    return local_contexter()

  def add_page(self):
    # onmouseup (onclick fires also with onmousedown, resulting in two events) on previous page will take us to this one
    self.override_font = {}
    self.override_font_size = {} # override fonts are per page.
    self.pages_count += 1
    self.current_page_div = ET.Element('div')
    self.body.append(self.current_page_div)
    self.current_page_div.set('id', 'page-{}'.format(self.pages_count))
    html_class = 'page_div'
    style = ''
    self.current_page_div.set('class', html_class)
    #if self.pages_count == 1:
    #    style += 'visibility: visible; '
    #else:
    #    style += 'visibility: hidden; '
    style += 'visibility: hidden; ' # all pages hidden at first
    style += 'background-color: white; '
    self.current_page_div.set('style', style)
    subcontainer = ET.Element('div')
    subcontainer.set('class', 'subcontainer')
    self.current_page_div.append(subcontainer)
    self.current_page_div = subcontainer
    self.current_page_div.set('onmouseup', 'mouseuphandler(event);')
    #self.current_page_div.set('style', 'width: 100vw; height: 56.25vw; /* height:width ratio = 9/16 = .5625  */ background: pink; max-height: 100vh; max-width: 177.78vh; /* 16/9 = 1.778 */ margin: auto; position: absolute; top:0;bottom:0; /* vertical center */ left:0;right:0; /* horizontal center */')
    if len(self.current_page_div) == 0 and self.current_page_div.text == '':
      self.current_page_div.text = ' ' # no break space
    if self.logo is not None:
      logo_img = ET.Element('img')
      #print('setting src', self.logo)
      logo_img.set('src', self.logo)
      style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; z-index: 5;'.format(self.html_x(self.logo_x),self.html_y(self.logo_y),self.html_x(self.logo_w),self.html_y(self.logo_h))
      logo_img.set('style', style)
      self.current_page_div.append(logo_img)
    self.current_footer_div = None
    return True

  def set_title(self, title, *args, **kwargs):
    if title != '':
      self.title.text = title
    return True

  def set_producer(self, *args, **kwargs):
    return True

  def set_creator(self, *args, **kwargs):
    meta = ET.Element('meta')
    meta.set('generator', args[0])
    self.head.append(meta)
    return True

  def set_creation_date(self, *args, **kwargs):
    meta = ET.Element('meta')
    meta.set('generation-date', str(args[0]))
    self.head.append(meta)
    return True

  def set_text_color(self, color):
    self.text_color = dec_to_hex_color(color)
    return True

  def set_draw_color(self, color):
    self.draw_color = dec_to_hex_color(color)
    return True

  def set_fill_color(self, color):
    self.fill_color = dec_to_hex_color(color)
    return True

  def set_font(self, category, font_name, font_size):
    # the following is only used if these are already defined.
    font_size = self.html_font_size(font_size)
    element = self.current_page_div
    if category == 'title':
      element = self.current_title_tag
    elif category == 'subtitle':
      element = self.current_subtitle_tag
    elif category == 'standard':
      element = self.current_page_div
    elif category == 'footer':
      element = self.current_footer_div
    if font_name is not None:
      self.override_font[category] = font_name
      selector = 'font-family'
      val = font_name
      self.update_element_css(element, selector, val)
    if font_size is not None:
      self.override_font_size[category] = font_size
      selector = 'font-size'
      val = font_size
      self.update_element_css(element, selector, val)
    return True

  def update_element_css(self, element, selector, val):
    style = element.get('style')
    style = self.update_css_string(style, selector, val)
    element.set('style', style)

  def update_css_string(self, style, selector, val):
    style = self.remove_css_selector(style, selector)
    return style + selector+': '+str(val)+'; '

  def set_font_size(self, category, font_size):
    # the following is only used if these are already defined.
    font_size = self.html_font_size(font_size)
    element = self.current_page_div
    if category == 'title':
      element = self.current_title_tag
    elif category == 'subtitle':
      element = self.current_subtitle_tag
    elif category == 'standard':
      element = self.current_page_div
    elif category == 'footer':
      element = self.current_footer_div
    if font_size is not None:
      self.override_font_size[category] = font_size
      selector = 'font-size'
      val = font_size
      self.update_element_css(element, selector, val)
    return True

  def get_string_width(self, text):
    return len(text)*10 # TODO!!!

  def remove_css_selector(self, style, selector):
    loc = style.find(selector)
    if loc == -1:
      return style
    else:
      part1 = style[:loc]
      part2 = style[loc:]
      loc2 = part2.find(';')
      part2 = part2[loc2+1:]
      return part1+part2

  def set_background_color(self, color):
    color = dec_to_hex_color(color)
    style = self.current_page_div.get('style')
    if style is None:
      style = ''
    if len(style) > 0 and style[-1] != ';':
      style += ';'
    style = self.remove_css_selector(style, 'background-color')
    style += ' background-color: {};'.format(color)
    self.current_page_div.set('style', style)

  def rect(self, x, y, w, h, round_corners, corner_radius, *args, **kwargs):
    #print('rect','round corners' if round_corners else 'not round corners')
    rect = ET.Element('div')
    self.current_page_div.append(rect)
    self.x = x
    self.y = y
    style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; border: 1px solid {}; background-color: {};'.format(self.html_x(x),self.html_y(y),self.html_x(w),self.html_y(h),self.draw_color,self.fill_color)
    if round_corners and corner_radius > 0:
      style += 'border-radius: {};'.format(corner_radius)
    rect.set('style', style)
    #if len(rect) == 0 and rect.text == '':
    rect.text = ' ' # no break space

    return True

  def textbox(self, lines, x, y, w, h, headlines, h_level=None, align='left', markdown_format=True, text_color=None):
    formatted_lines = lines
    if align == 'left':
      align = 'start'
    elif align == 'right':
      align = 'end'
    text_div = ET.Element('div')
    self.current_page_div.append(text_div)
    text_tag = text_div
    if text_color is not None:
      text_color = dec_to_hex_color(text_color)
    else:
      text_color = self.text_color
    style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; text-align: {}; overflow: hidden; text-wrap: nowrap; color: {}; '.format(self.html_x(x), self.html_y(y), self.html_x(w), self.html_y(h), align, text_color)
    #print('textbox div style', style)
    if h_level is not None:
      text_div.set('style', style)
      h_tag = ET.Element('h'+str(h_level))
      style = 'margin: 0; padding: 0;'
      if h_level == 1:
        self.current_title_tag = h_tag
        if 'title' in self.override_font:
          style = self.update_css_string(style, 'font-family', self.override_font['title'])
        if 'title' in self.override_font_size:
          style = self.update_css_string(style, 'font-size', self.override_font_size['title'])
      elif h_level == 2:
        self.current_subtitle_tag = h_tag
        if 'subtitle' in self.override_font:
          style = self.update_css_string(style, 'font-family', self.override_font['subtitle'])
        if 'subtitle' in self.override_font_size:
          style = self.update_css_string(style, 'font-size', self.override_font_size['subtitle'])
      h_tag.set('style', style)
      text_div.append(h_tag)
      text_tag = h_tag
      text_tag.text = '\n'.join(lines)
    else:
      if 'standard' in self.override_font:
        style = self.update_css_string(style, 'font-size', self.override_font['standard'])
      if 'standard' in self.override_font_size:
        style = self.update_css_string(style, 'font-size', self.override_font_size['standard'])
      text_div.set('style', style)
    if markdown_format:
      new_lines = []
      for line in lines:
         if len(line) > 3 and all([c == '-' for c in line]):
            new_lines.append('')
         new_lines.append(line)

      lines = new_lines
      formatted_lines = md_to_html('\n'.join(lines))
      
      #formatted_lines = formatted_lines.replace('\n', '<br />\n')
      #if len(lines) > 0 and 'A small one' in lines[0]:
      #  print(lines)
      #  print(formatted_lines)
      tree = fromstring(formatted_lines)
      #print(trees)
      for subtree in tree: # parser puts everything in an <html> root
        text_tag.append(subtree)
      self.align_tables([text_tag], align)
    else:
      text_tag.text = '\n'.join(formatted_lines)
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break sspace
    self.fix_local_links([text_div], headlines)
    self.x = x
    self.y = y+h
    return x,y+h


  def l4_box(self, lines, x, y, w, h, headlines, align='left', border_color=[0,0,0], border_opacity=0.75, background_color=[255,255,255], background_opacity=0.75, markdown_format=True, text_color=None):
    formatted_lines = lines
    if align == 'left':
      align = 'start'
    elif align == 'right':
      align = 'end'
    text_div = ET.Element('div')
    self.current_page_div.append(text_div)
    text_tag = text_div
    bgcolor = dec_to_hex_color(background_color, background_opacity)
    bcolor = dec_to_hex_color(border_color, border_opacity)
    if text_color is not None:
      text_color = dec_to_hex_color(text_color)
    else:
      text_color = self.text_color
    style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; text-align: {}; z-index: 4; margin: 0; padding: -1cqw 1cqw 0 1cqw; background-color: {}; border: 1px {} solid; border-radius: 15px; overflow: hidden; color: {}; '.format(self.html_x(self.x), self.html_y(self.y), self.html_x(w), self.html_y(h), align, bgcolor, bcolor, text_color)
    print('align', align)
    if align == 'center':
      style += 'align-items: center; '
    text_div.set('style', style)
    if markdown_format:
      new_lines = []
      for line in lines:
         if len(line) > 3 and all([c == '-' for c in line]):
            new_lines.append('')
         new_lines.append(line)
      lines = new_lines
      formatted_lines = md_to_html('\n'.join(lines))
      #formatted_lines = formatted_lines.replace('\n', '<br />\n')
      #if len(lines) > 0 and 'A small one' in lines[0]:
      #  print(lines)
      #  print(formatted_lines)
      tree = fromstring(formatted_lines)
      #print(trees)
      for subtree in tree: # parser puts everything in an <html> root
        text_tag.append(subtree)
      self.align_tables([text_tag], align)
    else:
      text_tag.text = '\n'.join(lines)
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break sspace
    self.x = x
    self.y = y+h
    return True

  def align_tables(self, tag, align):
    for child in tag:
      if child.tag == 'table':
        style = child.get('style')
        if style == None:
          style = ''
        if align == 'center':
          style = self.update_css_string(style, 'margin-left', 'auto')
          style = self.update_css_string(style, 'margin-right', 'auto')
        elif align == 'right':
          style = self.update_css_string(style, 'right', '0')
        if style != '':
          child.set('style', style)
      self.align_tables(child, align)
    
  def fix_local_links(self, tag, headlines):
    for child in tag:
      if child.tag == 'a':
        href = child.get('href')
        if len(href) > 0 and href[0] == '#':
          page_no = int(headlines.index(href[1:].strip()))+1
          child.set('href', '#')
          child.set('onclick', 'goToPage("page-{}"); return false;'.format(page_no))

      self.fix_local_links(child, headlines)
    
  def text(self, txt, x, y, h_level=None, em=10, footer=False, text_color=None):
    text_div = ET.Element('div')
    self.current_page_div.append(text_div)
    self.x = x
    self.y = y
    if text_color is not None:
      text_color = dec_to_hex_color(text_color)
    else:
      text_color = self.text_color
    style = 'position: absolute; left: {}; top: {}; color: {};'.format(self.html_x(self.x),self.html_y(self.y), text_color)
    if footer:
      #style += 'font-face: Roboto Mono; font-size: 1cqw; padding: 0; margin: 0;'
      text_div.set('class', 'footer')
      text_div.set('id', 'footer')
      self.current_footer_div = text_div
      if 'footer' in self.override_font:
        style = self.update_css_string(style, 'font-size', self.override_font['footer'])
      if 'footer' in self.override_font_size:
        style = self.update_css_string(style, 'font-size', self.override_font_size['footer'])
    else:
      if h_level is None:
        if 'standard' in self.override_font:
          style = self.update_css_string(style, 'font-size', self.override_font['standard'])
        if 'standard' in self.override_font_size:
          style = self.update_css_string(style, 'font-size', self.override_font_size['standard'])
    text_div.set('style', style)
    text_tag = text_div
    if h_level is not None:
      h_tag = ET.Element('h'+str(h_level))
      style = 'margin: 0; padding: 0;'
      text_div.append(h_tag)
      text_tag = h_tag
      if h_level == 1:
        self.current_title_tag = text_tag
        if 'title' in self.override_font:
          style = self.update_css_string(style, 'font-family', self.override_font['title'])
        if 'title' in self.override_font_size:
          style = self.update_css_string(style, 'font-size', self.override_font_size['title'])
      elif h_level == 2:
        self.current_subtitle_tag = text_tag
        if 'subtitle' in self.override_font:
          style = self.update_css_string(style, 'font-family', self.override_font['subtitle'])
        if 'subtitle' in self.override_font_size:
          style = self.update_css_string(style, 'font-size', self.override_font_size['subtitle'])
      h_tag.set('style', style)
    text_tag.text = txt
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break sspace
    self.y = self.y+em
    return True

  def add_link(self, *args, **kwargs):
    return self.pages_count

  def cell(self, *args, **kwargs):
    text_div = ET.Element('div')
    self.current_page_div.append(text_div)
    if 'x' in kwargs:
      self.x = kwargs['x']
    if 'y' in kwargs:
      self.x = kwargs['y']
    text_div.set('style', 'position: absolute; left: {}; top: {}'.format(self.html_x(self.x),self.html_y(self.y)))
    if 'link' in kwargs:
      a = ET.Element('a')
      self.current_page_div.append(a)
      a.set('href',str(kwargs['link']))
      a.text = kwargs['txt']
    else:
      text_div.text = kwargs['txt']
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break space
    return True

  def line(self, *args, **kwargs):
    return False

  def table(self, *args, **kwargs):
    table = ET.Element('table')
    self.current_page_div.append(table)
    return table

  def set_line_width(self, *args, **kwargs):
    return False

  def will_page_break(self, *args, **kwargs):
    return False

  def image(self, file, x, y, w, h, crop_images=False, copy=True, link=None):
    media_tag = ET.Element('img')
    style = ''
    new_filename = file
    already_copied = False
    extension = os.path.splitext(file)[1]
    is_video = is_video_link(file)

    if is_video:
      media_tag = ET.Element('iframe')
      media_tag.set('frameborder', '0')
      media_tag.set('allow', 'autoplay; encrypted-media')
      media_tag.set('allowfullscreen', 'true')
      media_tag.text = ' '
      media_tag.set('src', file)
    else:
      if self.oversized_images == "DOWNSCALE" and self.resources_dir is not None:
        width = self.html_x(w)
        height = self.html_y(h)
        if extension != 'svg':
          with Image.open(file) as im:
            im_w, im_h = im.size
            im_aspect = im_w/im_h
            box_aspect = w/h
            if im_aspect > box_aspect:
              # image will be its own width
              target_width_pixels = float(width[:-1])*self.downscale_resolution_width
              target_height_pixels = (1/im_aspect)*target_width_pixels
            else:
              # image will be its own height
              target_height_pixels = float(height[:-1])*self.downscale_resolution_height
              target_width_pixels = im_aspect*target_height_pixels
            if target_width_pixels < im_w:
              print('downscaling image',file)
              im.resize((target_width_pixels, target_height_pixels))
              new_filename = self.resources_dir+os.path.basename(file)
              im.save(new_filename)
              already_copied = False
      if copy and not already_copied and self.resources_dir is not None:
        if self.resources_dir == self.output_dir:
          new_filename = os.path.basename(file)
          shutil.copyfile(file, os.path.join(self.output_dir, new_filename))
        else:
          new_filename = self.resources_dir+os.path.basename(file)
          shutil.copyfile(file, new_filename)
      media_tag.set('src', new_filename)
    style += 'position: absolute; left: {}; top: {}; width: {}; height: {};'.format(self.html_x(x), self.html_y(y), self.html_x(w), self.html_y(h))
    #print('image style',style)
    if crop_images == False:
      style += ' object-fit: contain;'
    else:
      style += ' object-fit: cover;'
    media_tag.set('style', style)
    self.current_page_div.append(media_tag)
    self.set_xy(self.x, self.y+h)
    return True

  def rect_clip(self, *args, **kwargs):
    class rect_clipper:
      def __init__(self):
        pass
      def __enter__(self):
        pass
      def __exit__(self, type, value, traceback):
        pass
    return rect_clipper()

  def get_x(self):
    return self.x

  def get_y(self):
    return self.y

  def set_xy(self, x, y):
    self.x = x
    self.y = y
    return True

  def get_format(self):
    return 'html'

  def ensure_closing_tags(self, T):
    #if T.tag == 'div':
    #  print('div:',T, len(T), T.text)
    if T.tag in ['div', 'p'] and len(T) == 0 and (T.text == '' or T.text is None):
      #print('makes sure no empty divs makes unclosed divs. found one.')
      T.text = ' ' # no break sspace
    for c in T:
      self.ensure_closing_tags(c)

  def output(self, filename):
    #with open(args[0], 'w') as f:
    #  f.write(ET.tostring(self.html, encoding="unicode"))
    #tree = ET.ElementTree(self.html)
    #ET.indent(tree, space="\t", level=0)

    self.ensure_closing_tags(self.html)

    with open(filename, 'w') as f:
      #s = ET.tostring(tree, xml_declaration=True, encoding="UTF-8", doctype="<!DOCTYPE html>")
      ET.indent(self.html, space="\t", level=0)
      s = ET.tostring(self.html, method='html', encoding="unicode")
      s = '<!DOCTYPE html>\n\n'+s
      f.write(s)
    # TODO: index.html shutil.copyfile(filename, os.path.join(resources_dir, 'index.html'))
    #tree.docinfo.doctype = '<!DOCTYPE html>'
    #tree.write(args[0], encoding="utf-8", xml_declaration=True)
    return True

def md_to_html(md):
  md_, formulas_ = md_extract_formulas(md)
  print('md_to_html:',md_)
  html = markdown(md_, extras=['cuddled-lists', 'tables'])
  finalOutput = md_reconstruct_math(html, formulas_)
  return finalOutput

def md_extract_formulas(md):
  md_sane_lines = []
  formulas = []
  for line in md.split('\n'):
    if '$' in line:
      formula_starts_ends = []
      formula_start = None
      for p in range(len(line)):
        if line[p] == '$' and (p == 0 or line[p-1] != '\\'):
          if formula_start is None:
            formula_start = p
          else:
            formula_starts_ends.append((formula_start,p+1))
            formula_start = None
      new_line = ''
      pos = 0
      number = 0
      for (s,e) in formula_starts_ends:
        new_line += line[pos:s]+'${}$'.format(number)
        formulas.append((number, line[s:e]))
        number += 1
        pos = e
      md_sane_lines.append(new_line)
    else:
      md_sane_lines.append(line)
  return '\n'.join(md_sane_lines), formulas

def md_reconstruct_math(html, formulas):
  for (n,f) in formulas:
    html = html.replace('${}$'.format(n), f)
  return html

def dec_to_hex_color(color, alpha=1.0):
  a = 'ff'
  if type(color) == str:
    c = hex(color[0:2])[2:].rjust(2, '0')+hex(color[2:4])[2:].rjust(2, '0')+hex(color[4:6])[2:].rjust(2, '0')
  elif type(color) == list:
    c = hex(color[0])[2:].rjust(2, '0')+hex(color[1])[2:].rjust(2, '0')+hex(color[2])[2:].rjust(2, '0')
  elif type(color) == int:
    c = hex(color).rjust(2, '0')+hex(color).rjust(2, '0')+hex(color).rjust(2, '0')
  if alpha < 1.0:
    a = hex(int(255*alpha))
  #print(color)
  return '#'+c+a


def font_file_to_font_name(filename):
  filename = os.path.basename(filename)
  filename = filename.split('.')[0]
  words = re.findall('[A-Z][^A-Z]*', filename)
  return ' '.join(words).replace('-', '')


def change_filename_extension(filename, extension):
  pos = filename.rfind('.')
  basename = filename[:pos]
  return basename + '.' + extension

def is_video_link(link):
  parsed_uri = urlparse(link)
  return any([x in parsed_uri.netloc for x in ['youtube', 'youtu.be', 'vimeo', 'dailymotion', 'dai.ly']])
