# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.


import os, os.path, shutil, re, time
from lxml import etree as ET
from markdown2 import markdown
from lxml.html.soupparser import fromstring
from PIL import Image
from urllib.parse import urlparse
import requests

treat_as_raster_images = ['svg']
DOWNSCALE_SLACK = 0.75


class backend_html:
  def __init__(self, input_file, formatting, script_home, overwrite_images=False):
    self.html_output_filename = os.path.join(os.path.splitext(input_file)[0],'index.html')
    self.output_dir = os.path.dirname(self.html_output_filename)
    #print('output_dir',self.output_dir)
    if len(self.output_dir) > 0 and self.output_dir[-1] != '/':
      self.output_dir += '/'
    self.graphics_dir = os.path.join(self.output_dir,'graphics')
    self.resources_dir = os.path.join(self.output_dir,'resources')
    try:
      os.makedirs(self.graphics_dir)
    except FileExistsError:
      pass
    try:
      os.makedirs(self.resources_dir)
    except FileExistsError:
      pass
    #print('graphics_dir',self.graphics_dir)
    #print('resources_dir',self.resources_dir)

    self.page_width = formatting['dimensions']['page_width']
    self.page_height = formatting['dimensions']['page_height']

    self.text_color = dec_to_hex_color([0,0,0])

    self.oversized_images = "DOWNSCALE"
    #self.oversized_images = "DONOTDOWNSCALE"
    self.downscale_resolution_width = 3840
    self.downscale_resolution_height = self.downscale_resolution_width*(self.page_height/self.page_width)
    print(self.oversized_images, self.downscale_resolution_width, self.downscale_resolution_height)

    self.input_file_name = input_file
    self.x = formatting['dimensions']['page_margins']['x0']
    self.y = formatting['dimensions']['page_margins']['y0']
    self.pages_count = 0
    self.formatting = formatting
    self.script_home = script_home
    self.logo = None

    self.current_title_tag = None
    self.current_subtitle_tag = None
    self.current_page_div = None
    self.current_footer_div = None
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
          self.font_files[font_cat] = os.path.join(self.resources_dir,os.path.basename(woff2_file))
          # strip base dir (container of index file):
          self.font_files[font_cat] = '/'.join(self.font_files[font_cat].split('/')[1:])
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
      target_mathjax_path = os.path.join(self.resources_dir, os.path.basename(mathjax_local_file))
      shutil.copy(mathjax_local_file, target_mathjax_path)
      print('copy', mathjax_local_file, target_mathjax_path)
      # strip base dir (container of index file):
      target_mathjax_path = '/'.join(target_mathjax_path.split('/')[1:])
      mathjax_url = target_mathjax_path
    else:
      mathjax_url = mathjax_local_file
      print('mathjax_url',mathjax_local_file)
      
      

    screen_css = '''
:root {{
  /* 16:9 slide box derived from viewport */
  --slide-w: min(100vw, 177.78vh);
  --slide-h: calc(var(--slide-w) * 0.5625); /* 9/16 */

  /* 1% of the slide’s width/height */
  --cqw: calc(var(--slide-w) / 100);
  --cqh: calc(var(--slide-h) / 100);
}}
@font-face {{
  font-family: "{}";
  src: url('{}') format('woff2');
}}
@font-face {{
  font-family: "{}";
  src: url('{}') format('woff2');
}}
@font-face {{
  font-family: "{}";
  src: url('{}') format('woff2');
}}
body {{
  overflow: hidden;
  background-color: black;
  font-family: "{}", Arial, Sans-Serif;
  font-weight: normal;
}}
h1 {{
  font-family: "{}", Arial, Sans-Serif;
  /*font-size: 4cqw;*/
  font-size: "{}";
  font-weight: normal;
}}
h2 {{
  font-family: "{}", Arial, Sans-Serif;
  /*font-size: 2.8cqw;*/
  font-size: "{}";
  font-weight: normal;
}}
h3 {{
  font-family: "{}", Arial, Sans-Serif;
  /*font-size: 2cqw;*/
  font-size: {};
  font-weight: normal;
}}
h4 {{
  font-family: "{}", Arial, Sans-Serif;
  /*font-size: 2cqw;*/
  font-size: {};
  font-weight: normal;
}}
.page_visible {{
  visibility: visible;
}}
.page_hidden {{
  visibility: hidden;
}}
div.page_div {{
  background-color: #fff;
}}
div.page_div {{
  background-color: #fff;
  width: 100vw;
  height: 56.25vw; /* height:width ratio = 9/16 = .5625  */
  max-height: 100vh;
  max-width: 177.78vh; /* 16/9 = 1.778 */
  margin: auto;
  position: absolute;
  top:0;
  bottom:0; /* vertical center */
  left:0;
  right:0; /* horizontal center */
  /* container-type: size; */
  overflow: hidden;
  z-index: 2;
}}
div.subcontainer {{
  container-type: size;
  width: 100%;
  height: 100%;
  font-size: {};
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
  z-index: 8;
}}
/* Floating instructions panel (reuses .loading_div element) */
div.loading_div {{
  position: fixed;
  bottom: calc(1vw + 4vw + 0.75vw); /* sit above the circle */
  right: 1vw;
  max-width: 36vw;
  background-color: rgba(0,0,0,0.85);
  color: white;
  visibility: hidden;   /* hidden by default */
  opacity: 0;
  z-index: 20;
  text-align: left;
  display: block;
  align-items: start;
  justify-content: start;
  font-size: 1vw;
  padding: 1vw 1.2vw;
  border-radius: 0.8vw;
  box-shadow: 0 0.6vw 1.6vw rgba(0,0,0,0.4);
  transition: opacity .25s ease, visibility .25s ease;
  pointer-events: none; /* no clicks when hidden */
}}
div.loading_div.visible {{
  visibility: visible;
  opacity: 1;
  pointer-events: auto; /* clickable when shown */
}}
div.loading_div.as-help .splash-only {{
  display: none;
}}

/* Floating question mark button */
#help_btn {{
  position: fixed;
  bottom: 1vw;
  right: 1vw;
  width: 4vw;                /* 4% of screen width */
  height: 4vw;
  min-width: 28px;           /* sensible floor for tiny screens */
  min-height: 28px;
  border-radius: 50%;
  background: rgba(0,0,0,0.65);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2vw;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  z-index: 21;
  box-shadow: 0 0.5vw 1.2vw rgba(0,0,0,0.35);
  transition: opacity .35s ease;
  opacity: 1;
}}
#help_btn.hidden {{ opacity: 0; pointer-events: none; }}

/* Always show the button in overview */
body.overview #help_btn {{
  opacity: 1 !important;
  pointer-events: auto !important;
}}
div.l4_box {{
  position: absolute;
  border-radius: 1cqw;
  overflow: hidden;
}}
div.l4_box p {{
  margin: 1.2cqw;
}}
div.footer {{
  font-family: "{}", Arial, Sans-Serif;
  /*font-size: 1cqw;*/
  font-size: {};
  font-weight: normal;
}}
ul {{
  margin-top: 0;
  border: 1px;
}}
li {{
  margin-top: 0em;
  margin-bottom: 0.3em;
}}
p {{
  margin-top: 0;
  margin-bottom: 0.3em;
}}
/*div {{
border: 1px #ccc solid;
/* for debugging: borders for all divs */
}}
p {{
border: 1px #ccc solid;
}}*/

/* --- Overview mode (toggle with 'O') --- */
#slides {{
  position: relative;
  z-index: 2;
}}
body.overview {{
  overflow: auto; /* allow scroll if >25 slides */
}}
body.overview #slides {{
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75vw;
  padding: 0.75vw;
  place-items: center;
}}

/* Force every page visible and sized as thumbnails */
body.overview .page_div {{
  position: relative !important;
  visibility: visible !important;
  width: calc(100vw / 5 - 1.2vw);
  height: calc((100vw / 5 - 1.2vw) * 0.5625); /* keep 16:9 */
  max-width: none;
  max-height: none;
  margin: 0;
  box-shadow: 0 0.25vw 0.75vw rgba(0,0,0,0.35);
  cursor: pointer;
  z-index: 2;
}}

/* Prevent inner content from capturing clicks during overview */
body.overview .page_div .subcontainer {{
  pointer-events: none;
}}

/* Dim the current slide a bit to indicate selection */
body.overview .page_div.is-current {{
  outline: 0.25vw solid #888;
  outline-offset: 0.25vw;
}}

/* Scale inner content so text shrinks in overview */
:root {{
  /* 5 columns => ~20% scale. Tweak if you change columns/gaps. */
  --thumb-scale: 0.2;
}}

body.overview .page_div .subcontainer {{
  /* Make the visual content 20% of normal size */
  transform: scale(var(--thumb-scale));
  transform-origin: top left;

  /* Expand the layout box inversely so the scaled content still fills the thumbnail */
  width: calc(100% / var(--thumb-scale));
  height: calc(100% / var(--thumb-scale));

  /* Keep thumbnails click-through (handled on the slide box) */
  pointer-events: none;
}}

@media print {{
  @page {{
    size: 160mm 90mm;
    margin: 0;
    -webkit-print-color-adjust: exact !important;   /* Chrome, Safari 6 – 15.3, Edge */
    color-adjust: exact !important;                 /* Firefox 48 – 96 */
    print-color-adjust: exact !important;           /* Firefox 97+, Safari 15.4+ */

  }}

  :root {{
    --slide-w: 160mm;
    --slide-h: 90mm;
    --cqw: calc(var(--slide-w) / 100);
    --cqh: calc(var(--slide-h) / 100);
  }}

  body {{
    margin:0px;
  }}
  div.page_div {{
    position: relative;
    visibility: visible;
    break-after: always;
    break-inside: avoid;
    display: table;
    /* width: 160mm;
    height: 90mm;*/
    width: var(--slide-w);
    height: var(--slide-h);
  }}
  .page_visible {{
    visibility: visible;
  }}
  .page_hidden {{
        visibility: visible;
  }}
  #help_btn {{ opacity: 0; }}
}}
'''.format(self.font_names['title'], self.font_files['title'], self.font_names['standard'], self.font_files['standard'], self.font_names['footer'], self.font_files['footer'], self.font_names['standard'], self.font_names['title'], self.font_sizes['title'], self.font_names['title'], self.font_sizes['subtitle'], self.font_names['title'], self.font_sizes['subtitle_l3'], self.font_names['title'], self.font_sizes['subtitle_l4'], self.font_sizes['standard'], self.font_names['footer'], self.font_sizes['footer'])
    #print('name',self.font_names['footer'])
    #print('size',self.font_sizes['footer'])


    default_javascript = '''
var currentPageId = "page-1";
var blackPageVar = false;
var lastPage = 0;

var overviewMode = false; // if you already declared this earlier, keep only one
var helpBtnTimer = null;

var initialHelpShown = false;

function onloadHandler() {
  gotoHash();          // make sure we still go to the right slide
  wireHelpUI();        // attach the click handlers (idempotent)
  if (!initialHelpShown) {
    var b = document.getElementById('help_btn');
    if (b) {
      b.classList.remove('hidden'); // show immediately
      if (helpBtnTimer) clearTimeout(helpBtnTimer);
      helpBtnTimer = setTimeout(function() {
        b.classList.add('hidden');  // hide after 5s
      }, 5000);
    }
    initialHelpShown = true;
  }
}
function showHelpBtn() {
  var b = document.getElementById('help_btn');
  if (b) b.classList.remove('hidden');
}
function hideHelpBtn() {
  var b = document.getElementById('help_btn');
  if (b) b.classList.add('hidden');
}


function getHelpPanel() {
  return document.getElementsByClassName('loading_div')[0];
}
function showHelpPanel() {
  var p = getHelpPanel();
  if (!p) return;
  p.classList.add('as-help');     // ← mark as help (hides splash-only)
  p.classList.add('visible');  // CSS transitions handle fade in
}
function hideHelpPanel() {
  var p = getHelpPanel();
  if (!p) return;
  p.classList.remove('visible'); // fade out
  p.classList.remove('as-help');     // ← mark as help (hides splash-only)
}

/* ensure the button works and clicks don't immediately close the panel */
function wireHelpUI() {
  var btn = document.getElementById('help_btn');
  if (btn && !btn._wired) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      showHelpPanel();
    });
    btn._wired = true;
  }
  var panel = getHelpPanel();
  if (panel && !panel._wired) {
    panel.addEventListener('click', function(e){ e.stopPropagation(); });
    panel._wired = true;
  }
  // Any click outside closes the panel
  if (!document._help_global_click) {
    document.addEventListener('click', function(){ hideHelpPanel(); });
    document._help_global_click = true;
  }
}

var overviewMode = false;

function setCurrentMarker() {
  // mark current slide for subtle outline in overview
  for (var i = 1; i <= lastPage; i++) {
    var pid = 'page-' + i;
    var el = document.getElementById(pid);
    if (!el) continue;
    if (pid === currentPageId) el.classList.add('is-current');
    else el.classList.remove('is-current');
  }
}

function enterOverview() {
  if (overviewMode) return;
  overviewMode = true;
  document.body.classList.add('overview');

  showHelpBtn();           // <— keep button visible in overview
  hideHelpPanel();         // <— close panel when mode changes

  // make all slides visible and clickable
  for (var i = 1; i <= lastPage; i++) {
    var pid = 'page-' + i;
    var el = document.getElementById(pid);
    if (!el) continue;

    // Ensure visibility regardless of page_visible/page_hidden
    el.classList.remove('page_hidden');
    el.classList.add('page_visible');

    // Attach a one-off click handler that exits overview and navigates
    el.addEventListener('click', overviewClickHandler);
  }
  setCurrentMarker();
}

function exitOverview() {
  if (!overviewMode) return;
  overviewMode = false;
  document.body.classList.remove('overview');

  hideHelpPanel();
  hideHelpBtn();           // <— fade if not within 5s

  // Remove click handlers
  for (var i = 1; i <= lastPage; i++) {
    var pid = 'page-' + i;
    var el = document.getElementById(pid);
    if (!el) continue;
    el.removeEventListener('click', overviewClickHandler);
    el.classList.remove('is-current');
  }

  // Restore single-slide view based on currentPageId
  for (var i = 1; i <= lastPage; i++) {
    var pid = 'page-' + i;
    var el = document.getElementById(pid);
    if (!el) continue;
    if (pid === currentPageId) {
      el.classList.remove('page_hidden');
      el.classList.add('page_visible');
    } else {
      el.classList.remove('page_visible');
      el.classList.add('page_hidden');
    }
  }
}

function toggleOverview() {
  if (overviewMode) exitOverview();
  else enterOverview();
}

function overviewClickHandler(e) {
  // During overview, clicking a slide selects it and exits
  var parent = e.currentTarget; // .page_div
  var pid = parent.id;
  currentPageId = pid;
  window.location.hash = pid;
  exitOverview();
  e.stopPropagation();
}

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
  var selection = window.getSelection();
  if(selection.toString().length > 0) {
    //alert('there was something selected'+selection.toString().length);
    return;
  }
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
function gotoHash(){
  var currentPageId = "page-1";
  newPageId = window.location.hash.substring(1);
  if (newPageId == "") {
    newPageId = currentPageId;
  }
  goToPage(newPageId);
}
function prevPage(){
  //alert('prevPage')
  if (overviewMode) return;  // do nothing in overview
  hideHelpPanel();
  splits = currentPageId.split("-");
  currentPageNumber = parseInt(splits[1]);
  prevPageNumber = currentPageNumber-1;
  pageId = "page-"+prevPageNumber;
  element = document.getElementById(pageId);
  if (element) {
    document.getElementById(currentPageId).classList.remove('page_visible');
    document.getElementById(currentPageId).classList.add('page_hidden');
    document.getElementById(pageId).classList.remove('page_hidden');
    document.getElementById(pageId).classList.add('page_visible');
    //document.getElementById(currentPageId).style.visibility="hidden";
    //document.getElementById(pageId).style.visibility="visible";
    currentPageId = pageId;
    window.location.hash = pageId;
  }
}
function nextPage(){
  //alert('nextPage')
  if (overviewMode) return;  // do nothing in overview
  hideHelpPanel();
  splits = currentPageId.split("-");
  currentPageNumber = parseInt(splits[1]);
  nextPageNumber = currentPageNumber+1;
  pageId = "page-"+nextPageNumber;
  element = document.getElementById(pageId);
  if (element) {
    document.getElementById(currentPageId).classList.remove('page_visible');
    document.getElementById(currentPageId).classList.add('page_hidden');
    document.getElementById(pageId).classList.remove('page_hidden');
    document.getElementById(pageId).classList.add('page_visible');
    //document.getElementById(currentPageId).style.visibility="hidden";
    //document.getElementById(pageId).style.visibility="visible";
    currentPageId = pageId;
    window.location.hash = pageId;
  }
}
function goToPage(pageId){
  //alert(pageId);
  hideHelpPanel();
  if (!document.getElementById(pageId)){
    //alert(pageId+": page not found")
    pageId = "page-1";
  }
  document.getElementById(currentPageId).classList.remove('page_visible');
  document.getElementById(currentPageId).classList.add('page_hidden');
  document.getElementById(pageId).classList.remove('page_hidden');
  document.getElementById(pageId).classList.add('page_visible');
  //document.getElementById(currentPageId).style.visibility="hidden";
  //document.getElementById(pageId).style.visibility="visible";
  currentPageId = pageId;
  window.location.hash = pageId;
  setCurrentMarker();
}
function localPageLink(pageId, event){
  //alert(pageId);
  event.stopPropagation(); // do not fire event on parent elements.
  goToPage(pageId);
}
function stopProp(event){
  event.stopPropagation();
}
document.onkeydown = function(event) {
  hideHelpPanel();
  switch (event.keyCode) {
    case 33:
      // page up
      prevPage();
    break;
    case 34:
      // page down
      nextPage();
    break;
    case 35:
      // end
      goToPage('page-'+lastPage);
    break;
    case 36:
      // home
      goToPage('page-0');
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
    case 76:
      // l - laser pointer
      if (document.getElementsByTagName("body")[0].style.cursor.includes("cursor.png")) {
        document.getElementsByTagName("body")[0].style.cursor = "initial";
      }
      else {
        document.getElementsByTagName("body")[0].style.cursor = "url('graphics/pointer.png'), auto";
      }
    break;
    case 79:
      // o - overview
      toggleOverview();
    break;
  }
};
'''

    self.html = ET.Element('html')
    self.head = ET.Element('head')
    self.html.append(self.head)
    self.doc_style = ET.Element('style')
    #self.doc_style.set('media', 'screen')
    self.doc_style.text = screen_css
    self.head.append(self.doc_style)
    self.title = ET.Element('title')
    self.title.text = 'PYMD HTML SLIDES'
    self.head.append(self.title)
    self.script = ET.Element('script')
    self.script.text = default_javascript
    self.head.append(self.script)
    mathjax0 = ET.Element('script')
    mathjax0.text = '''
MathJax = {
  tex: {
    inlineMath: [['$', '$']]
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
    self.slides_container = ET.Element('div')
    self.slides_container.set('id', 'slides')
    self.body.append(self.slides_container)
    self.body.set('onload', 'onloadHandler();')
    #self.body.set('onhashchange', 'gotoHash();')
    self.html.append(self.body)
    self.current_page_div = None

    black_div = ET.Element('div')
    black_div.set('class', 'black_div')
    black_div.set('id', 'black_div')
    #black_div.set('class', 'page_div')
    self.body.append(black_div)
    loading_div = ET.Element('div')
    loading_div.set('class', 'loading_div')
    loading_subdiv = ET.Element('div')
    loading_div.append(loading_subdiv)
    # Floating help button (question mark)
    help_btn = ET.Element('div')
    help_btn.set('id', 'help_btn')
    help_btn.set('class', 'hidden')
    help_btn.text = '?'
    self.body.append(help_btn)
    loading_span1 = ET.Element('p')
    loading_span1.text = 'Loading.'
    loading_span1.set('class', 'splash-only')
    loading_span2 = ET.Element('p')
    loading_span2.text = 'PYMD slides requires a javascript-enabled browser.'
    loading_span2.set('class', 'splash-only')
    loading_span3 = ET.Element('p')
    loading_span3.text = 'Usage: Arrow buttons, page up/down, or space to navigate.'
    loading_span4 = ET.Element('p')
    loading_span4.text = 'F for fullscreen.'
    loading_span5 = ET.Element('p')
    loading_span5.text = 'B for blank.'
    loading_span6 = ET.Element('p')
    loading_span6.text = 'O for overview grid. Click a slide to jump.'
    loading_span7 = ET.Element('p')
    loading_span7.text = 'Click on leftmost quarter for previous slide, the rest for next.'
    loading_span8 = ET.Element('p')
    loading_span8.text = 'More info: see https://github.com/olofmogren/pymdslides/ .'
    loading_subdiv.append(loading_span1)
    loading_subdiv.append(loading_span2)
    loading_subdiv.append(loading_span3)
    loading_subdiv.append(loading_span4)
    loading_subdiv.append(loading_span5)
    loading_subdiv.append(loading_span6)
    loading_subdiv.append(loading_span7)
    loading_subdiv.append(loading_span8)
    self.body.append(loading_div)
    self.overwrite_images = overwrite_images
    self.onload_added = False
    new_filename = os.path.join(self.graphics_dir,'pointer.png')
    shutil.copyfile(os.path.join(script_home, 'pointer.png'), new_filename)


  def set_logo(self, logo, x, y, w, h):
    #print('setting_logo', str(logo))
    new_filename = logo
    #if self.graphics_dir is not None:
    new_filename = os.path.join(self.graphics_dir,os.path.basename(logo))
    shutil.copyfile(logo, new_filename)

    # strip base dir (container of index file):
    new_filename = '/'.join(new_filename.split('/')[1:])
    self.logo = new_filename
    self.logo_x = x
    self.logo_y = y
    self.logo_w = w
    self.logo_h = h

  def html_x(self, x):
    x_frac = x/self.page_width
    #return str(round(x_frac*100))+'%'
    return '{:.3f}%'.format(x_frac*100)

  def html_y(self, y):
    y_frac = y/self.page_height
    #return str(round(y_frac*100))+'%'
    return '{:.3f}%'.format(y_frac*100)

  def html_font_size(self, font_size):
    #print(font_size)
    #result = '{:.3f}cqw'.format(32*font_size/self.page_width)
    result = 'calc({:.3f} * var(--cqw))'.format(32*font_size/self.page_width)
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
    self.slides_container.append(self.current_page_div)
    self.current_page_div.set('id', 'page-{}'.format(self.pages_count))
    html_class = 'page_div page_hidden'
    style = ''
    self.current_page_div.set('class', html_class)
    #if self.pages_count == 1:
    #    style += 'visibility: visible; '
    #else:
    #    style += 'visibility: hidden; '
    #style += 'visibility: hidden; ' # all pages hidden at first
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
    if font_name is not None and font_name.strip() != '':
      self.override_font[category] = font_name
      selector = 'font-family'
      val = font_name
      if element is not None:
        self.update_element_css(element, selector, val)
    if font_size is not None:
      self.override_font_size[category] = font_size
      selector = 'font-size'
      val = font_size
      if element is not None:
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
      if element is not None:
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

  def textbox(self, lines, x, y, w, h, headlines, h_level=None, align='left', markdown_format=True, text_color=None, text_vertical_align=None):
    #print('textbox', h_level, lines)
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
    style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; text-align: {}; overflow: hidden; padding-top: 0; /* text-wrap: nowrap; */ color: {};'.format(self.html_x(x), self.html_y(y), self.html_x(w), self.html_y(h), align, text_color)
    if text_vertical_align and text_vertical_align is not 'top':
      if text_vertical_align == 'bottom':
        text_vertical_align = 'flex-end'
      style += 'display: flex; align-items: {};'.format(text_vertical_align)
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
    self.fix_all_links([text_div], headlines)
    self.x = x
    self.y = y+h
    return x,y+h


  def l4_box(self, lines, x, y, w, h, headlines, align='left', border_color=[0,0,0], border_opacity=0.75, background_color=[255,255,255], background_opacity=0.75, markdown_format=True, text_color=None, text_vertical_align=None):
    formatted_lines = lines
    if align == 'left':
      align = 'start'
    elif align == 'right':
      align = 'end'
    print('l4_box', x, y, w, h, '---'.join(lines))
    text_div = ET.Element('div')
    self.current_page_div.append(text_div)
    text_tag = text_div
    bgcolor = dec_to_hex_color(background_color, background_opacity)
    #print('border: color', border_color, border_opacity)
    bcolor = dec_to_hex_color(border_color, border_opacity)
    if text_color is not None:
      text_color = dec_to_hex_color(text_color)
    else:
      text_color = self.text_color
    style = 'left: {}; top: {}; width: {}; text-align: {}; z-index: 4; margin: 0; padding: -1cqw .5cqw .5cqw .5cqw; background-color: {}; border: 1px {} solid; color: {}; display: flex; align-items: center;   /* vertical centering */'.format(self.html_x(x), self.html_y(y), self.html_x(w), align, bgcolor, bcolor, text_color)
    if text_vertical_align and text_vertical_align is not 'top':
      if text_vertical_align == 'bottom':
        text_vertical_align = 'flex-end'
      style += 'display: flex; align-items: {};'.format(text_vertical_align)
    print('align', align)
    if align == 'center':
      style += 'align-items: center; '
    text_div.set('class', 'l4_box')
    text_div.set('style', style)
    if markdown_format:
      formatted_lines = md_to_html('\n'.join(lines))
      tree = fromstring(formatted_lines)
      for subtree in tree: # parser puts everything in an <html> root
        text_tag.append(subtree)
      self.align_tables([text_tag], align)
    else:
      text_tag.text = '\n'.join(lines)
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break sspace
    #self.style_p([text_div])
    self.fix_all_links([text_div], headlines)
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
    
  def fix_all_links(self, tag, headlines):
    self.fix_local_links(tag, headlines)
    self.fix_external_links(tag)

  def fix_local_links(self, tag, headlines):
    for child in tag:
      if child.tag == 'a':
        href = child.get('href')
        if len(href) > 0 and href[0] == '#':
          print('looking for local link',href)
          try:
            page_no = int(headlines.index(href[1:].strip()))+1
            print('found local link', page_no)
            child.set('href', '#')
            child.set('onclick', 'localPageLink("page-{}", event); return false;'.format(page_no))
            child.set('onmouseup', 'stopProp(event);')
          except ValueError:
            print('Warning: Link to heading:',href[1:].strip(),'not found. Not linking.')
      self.fix_local_links(child, headlines)
    
  def fix_external_links(self, tag):
    for child in tag:
      if child.tag == 'a':
        href = child.get('href')
        if len(href) > 0 and not href[0] == '#':
          child.set('onmouseup', 'stopProp(event);')
      self.fix_external_links(child)
    
  #def style_p(self, tag):
  #  for child in tag:
  #    if child.tag == 'p':
  #      style = child.get('style')
  #      if style is None:
  #        style = ''
  #      style = self.update_css_string(style, 'margin', '1.2cqw')
  #      child.set('style', style)
  #    self.style_p(child)
    
  def text(self, txt, x, y, headlines, h_level=None, em=10, footer=False, text_color=None, markdown_format=False):
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
    if markdown_format:
      formatted = md_to_html(txt)
      tree = fromstring(formatted)
      for subtree in tree: # parser puts everything in an <html> root
        text_tag.append(subtree)
    else:
      text_tag.text = txt
    if len(text_div) == 0 and text_div.text == '':
      text_div.text = ' ' # no break sspace
    self.y = self.y+em
    self.fix_all_links([text_div], headlines)
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

  def image(self, file, x, y, w, h, crop_images=False, link=None):
    print('crop', crop_images)
    print('image', x, y, w, h, self.html_x(x), self.html_y(y), self.html_x(w), self.html_y(h))
    original_filename = file
    current_filename = file
    current_ext = os.path.splitext(current_filename)[1][1:]
    media_tag = ET.Element('img')
    style = ''
    already_copied = False
    is_video = is_video_link(file)
    page_no_is_set = False

    if is_video:
      media_tag = ET.Element('iframe')
      media_tag.set('frameborder', '0')
      media_tag.set('allow', 'autoplay; encrypted-media')
      media_tag.set('allowfullscreen', 'true')
      media_tag.text = ' '
      media_tag.set('src', file)
    else:
      input_file = current_filename.split('#')[0]
      target_filename_no_ext = os.path.join(self.graphics_dir,os.path.splitext(os.path.basename(original_filename))[0])
      if page_no_is_set:
        target_filename_no_ext += '-'+str(page_no)
      page_no = '0'
      if '#' in current_filename:
        page_no = current_filename.split('#')[1]
        page_no_is_set = True
        current_ext = current_ext.split('#')[0]
      if is_vector_format(current_filename) and not current_ext in treat_as_raster_images:
        command_is_chosen = False
        #print('possible conversion of vector format:', current_ext, shutil.which('pdf2svg'), shutil.which('eps2svg'))
        if current_ext == 'pdf' and shutil.which('pdf2svg') is not None:
          target_extension = 'svg'
          target_filename = target_filename_no_ext+'-'+page_no+'.'+target_extension
          command = 'pdf2svg {} {} {}'.format(input_file, target_filename, int(page_no)+1) # page_no is zero-indexed
          current_ext = target_extension
          command_is_chosen = True
        elif current_ext == 'eps' and shutil.which('eps2svg') is not None:
          target_extension = 'svg'
          target_filename = target_filename_no_ext+'.'+target_extension
          command = 'eps2svg {} {}'.format(input_file, target_filename)
          current_ext = target_extension
          command_is_chosen = True
        if not command_is_chosen:
          if current_ext == 'pdf':
            print('pdf: pdf2svg not found. falling back to converting to png.')
          if current_ext == 'eps':
            print('eps: eps2svg not found. falling back to converting to png.')
          target_extension = 'png'
          target_filename = target_filename_no_ext+'-'+page_no+'.'+target_extension
          command = 'magick -density 150 '+input_file+'['+page_no+'] '+target_filename
          current_ext = target_extension
          command_is_chosen = True
        print('magick image:',command)
        os.system(command)
      else:
        target_extension = current_ext
        if current_ext in ['png', 'gif']:
          target_extension = 'webp'
        target_filename = target_filename_no_ext+'.'+target_extension
        if self.oversized_images == "DOWNSCALE": # and self.graphics_dir is not None:
          #print(self.html_x(w), self.html_y(h))
          width = float(self.html_x(w)[:-1])*.01
          height = float(self.html_y(h)[:-1])*.01
          if current_ext not in ['svg', 'gif']:
            with Image.open(current_filename) as im:
              im_w, im_h = im.size
              im_aspect = im_w/im_h
              box_aspect = w/h
              if im_aspect > box_aspect:
                # image will be its own width
                #print('im_aspect > box_aspect')
                target_width_pixels = round(width*self.downscale_resolution_width)
                target_height_pixels = round((1/im_aspect)*target_width_pixels)
              else:
                # image will be its own height
                #print('im_aspect <= box_aspect')
                target_height_pixels = round(height*self.downscale_resolution_height)
                target_width_pixels = round(im_aspect*target_height_pixels)
              #print('target_width_pixels, im_w', target_width_pixels, im_w)
              if target_width_pixels < im_w*DOWNSCALE_SLACK:
                print('image requires downscaling {}, {}x{} pixels'.format(os.path.basename(current_filename), target_width_pixels, target_height_pixels))
                im = im.resize((target_width_pixels, target_height_pixels))
                target_filename = target_filename_no_ext+ '-{}x{}'.format(target_width_pixels, target_height_pixels)+'.'+target_extension
                print('target_filename', target_filename)
                print('exists', os.path.exists(target_filename), 'overwrite', self.overwrite_images)
                if not os.path.exists(target_filename) or self.overwrite_images:
                  im.save(target_filename)
                  print('saved image at ', target_filename)
                else:
                  print('reusing image at ',target_filename)
                already_copied = True
        if not already_copied:
          print('exists', os.path.exists(target_filename), 'overwrite', self.overwrite_images)
          if not os.path.exists(target_filename) or self.overwrite_images:
            if target_extension != current_ext:
              command = 'magick -define webp:lossless=false '+current_filename+' '+target_filename
              #if target_extension == 'webp':
              #  command = 'cwebp {} -o {}'.format(current_filename, target_filename)
              if current_ext == 'gif' and target_extension == 'webp':
                command = 'gif2webp {} -o {}'.format(current_filename, target_filename)
              print(command)
              os.system(command)
            else:
              shutil.copyfile(current_filename, target_filename)
              print('copied image to ', target_filename)
          else:
            print('reusing image at ',target_filename)
      # strip base dir (container of index file):
      src_filename = '/'.join(target_filename.split('/')[1:])
      print('src_filename', src_filename)
      media_tag.set('src', src_filename)
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

  def set_last_page_js(self, html_source_code):
    return html_source_code.replace('var lastPage = 0;', 'var lastPage = {};'.format(self.pages_count));

  def set_onload(self):
    if not self.onload_added:
      loading_event_element = ET.Element('img')
      loading_event_element.set('src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg==')
      loading_event_element.set('style', 'visibility: hidden;')
      loading_event_element.set('onload', 'onloadHandler()')
      self.body.append(loading_event_element)
      self.onload_added = True

  def output(self):
    #with open(args[0], 'w') as f:
    #  f.write(ET.tostring(self.html, encoding="unicode"))
    #tree = ET.ElementTree(self.html)
    #ET.indent(tree, space="\t", level=0)

    self.ensure_closing_tags(self.html)
    self.set_onload()

    print('writing file',self.html_output_filename)

    with open(self.html_output_filename, 'w') as f:
      #s = ET.tostring(tree, xml_declaration=True, encoding="UTF-8", doctype="<!DOCTYPE html>")
      ET.indent(self.html, space="\t", level=0)
      s = ET.tostring(self.html, method='html', encoding="unicode")
      s = '<!DOCTYPE html>\n\n'+s
      s = self.set_last_page_js(s)
      f.write(s)
    # TODO: index.html shutil.copyfile(filename, os.path.join(graphics_dir, 'index.html'))
    #tree.docinfo.doctype = '<!DOCTYPE html>'
    #tree.write(args[0], encoding="utf-8", xml_declaration=True)
    return True

def md_to_html(md):
  md_, formulas_ = md_extract_formulas(md)
  #print(md_)
  #print(formulas_)
  #print('md_to_html:',md_)
  html = markdown(md_, extras=['cuddled-lists', 'tables'])
  final_output = md_reconstruct_math(html, formulas_)
  return final_output

def md_extract_formulas(md):
  md_sane_lines = []
  formulas = []
  number = 0
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
      for (s,e) in formula_starts_ends:
        new_line += line[pos:s]+'${}$'.format(number)
        formulas.append((number, line[s:e]))
        number += 1
        pos = e
      if pos < len(line):
        new_line += line[pos:]
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
    if color[0] == '#' and len(color) == 7:
      c = color[1:]
    if color[0] == '#' and len(color) == 4:
      c = color[1]+color[1]+color[2]+color[2]+color[3]+color[3]
    elif color == 'white':
      c = 'ffffff'
    elif color == 'grey':
      c = '646464'
    elif color == 'black':
      c = '000000'
    elif color == 'orange':
      c = 'ffb400'
    elif color == 'red':
      c = 'ff0000'
    elif color == 'green':
      c = '00ff00'
    elif color == 'blue':
      c = '0000ff'
    elif color == 'yellow':
      c = 'ffff00'
    elif color == 'darkred':
      c = '640000'
    elif color == 'darkgreen':
      c = '006400'
    elif color == 'darkblue':
      c = '000064'
    else:
      c = hex(color[0:2])[2:].rjust(2, '0')+hex(color[2:4])[2:].rjust(2, '0')+hex(color[4:6])[2:].rjust(2, '0')
  elif type(color) == list:
    c = hex(color[0])[2:].rjust(2, '0')+hex(color[1])[2:].rjust(2, '0')+hex(color[2])[2:].rjust(2, '0')
  elif type(color) == int:
    #print('color is int')
    c = hex(color)[2:].rjust(2, '0')+hex(color)[2:].rjust(2, '0')+hex(color)[2:].rjust(2, '0')
    #print(c)
  if alpha < 1.0:
    a = hex(int(255*alpha))[2:]
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

def is_vector_format(filename):
  return filename.split('#')[0][-3:] in ['pdf', '.ps', 'eps', 'svg']
