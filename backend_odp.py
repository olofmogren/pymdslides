# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

import os
import shutil
import zipfile
import hashlib
from lxml import etree as ET
from lxml.html.soupparser import fromstring
from markdown2 import markdown
from PIL import Image, ImageOps

# OpenDocument Namespaces
NS = {
    'office': "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    'style': "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    'text': "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    'table': "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    'draw': "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    'fo': "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    'xlink': "http://www.w3.org/1999/xlink",
    'dc': "http://purl.org/dc/elements/1.1/",
    'meta': "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    'presentation': "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    'svg': "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    'manifest': "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}

for k, v in NS.items():
    ET.register_namespace(k, v)


def qn(tag):
    """Helper to convert 'prefix:tag' into '{namespace}tag'."""
    prefix, local = tag.split(':')
    return f"{{{NS[prefix]}}}{local}"


class backend_odp:
    def __init__(self, input_file, formatting, script_home, overwrite_images=False):
        base_name = os.path.splitext(input_file)[0]
        self.output_dir = base_name
        # Write both <deck>/index.odp (matching pymdslides.py) and <deck>.odp
        self.odp_output_filename = os.path.join(self.output_dir, 'index.odp')
        self.odp_root_filename = base_name + '.odp'

        os.makedirs(self.output_dir, exist_ok=True)
        self.work_dir = os.path.join(self.output_dir, '_odp_build')
        self.pictures_dir = os.path.join(self.work_dir, 'Pictures')
        os.makedirs(self.pictures_dir, exist_ok=True)

        self.formatting = formatting
        self.script_home = script_home
        self.overwrite_images = overwrite_images

        self.page_width = formatting['dimensions']['page_width']    # 480
        self.page_height = formatting['dimensions']['page_height']  # 270

        # Physical slide dimensions in mm (matches 160mm x 90mm in backend_html @media print)
        self.slide_w_mm = 160.0
        self.slide_h_mm = 90.0

        self.x = formatting['dimensions']['page_margins']['x0']
        self.y = formatting['dimensions']['page_margins']['y0']
        self.pages_count = 0

        self.text_color = '#000000'
        self.draw_color = '#000000'
        self.fill_color = '#ffffff'

        self.logo = None
        self.logo_x = 0
        self.logo_y = 0
        self.logo_w = 0
        self.logo_h = 0

        self.doc_title = 'PYMD ODP SLIDES'
        self.doc_creator = 'pymdslides'
        self.doc_date = ''

        self.style_counter = 0
        self.manifest_files = {}  # {'Pictures/foo.png': 'image/png'}

        # Font names
        self.font_names = {
            'title': 'Arial',
            'subtitle': 'Arial',
            'standard': 'Arial',
            'footer': 'Monospace',
        }
        for font_cat in ['title', 'standard', 'footer']:
            if 'fonts' in formatting and f'font_file_{font_cat}' in formatting['fonts']:
                ttf_file = formatting['fonts'][f'font_file_{font_cat}']
                fontname = font_file_to_font_name(ttf_file)
                if f'font_name_{font_cat}' in formatting['fonts']:
                    fontname = formatting['fonts'][f'font_name_{font_cat}']
                self.font_names[font_cat] = fontname
        self.font_names['subtitle'] = self.font_names['title']

        self.font_sizes = {
            'title': formatting['dimensions'].get('font_size_title', 72),
            'subtitle': formatting['dimensions'].get('font_size_subtitle', 40),
            'standard': formatting['dimensions'].get('font_size_standard', 34),
            'footer': formatting['dimensions'].get('font_size_footer', 14),
        }

        self.override_font = {}
        self.override_font_size = {}
        self.current_page_el = None

        self._init_xml_trees()

    def _init_xml_trees(self):
        # 1. content.xml root
        self.content_root = ET.Element(
            qn('office:document-content'),
            {qn('office:version'): "1.2"}
        )
        self.auto_styles = ET.SubElement(self.content_root, qn('office:automatic-styles'))
        self.body = ET.SubElement(self.content_root, qn('office:body'))
        self.presentation = ET.SubElement(self.body, qn('office:presentation'))

        # Base text styles for bold, italic, code
        st_bold = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): 'T_Bold',
            qn('style:family'): 'text'
        })
        ET.SubElement(st_bold, qn('style:text-properties'), {
            qn('fo:font-weight'): 'bold',
            qn('style:font-weight-asian'): 'bold',
            qn('style:font-weight-complex'): 'bold'
        })

        st_italic = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): 'T_Italic',
            qn('style:family'): 'text'
        })
        ET.SubElement(st_italic, qn('style:text-properties'), {
            qn('fo:font-style'): 'italic',
            qn('style:font-style-asian'): 'italic',
            qn('style:font-style-complex'): 'italic'
        })

        st_code = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): 'T_Code',
            qn('style:family'): 'text'
        })
        ET.SubElement(st_code, qn('style:text-properties'), {
            qn('fo:font-family'): self.font_names['footer']
        })

    def _next_style_id(self, prefix='S'):
        self.style_counter += 1
        return f"{prefix}_{self.style_counter}"

    def odp_x(self, x):
        return f"{(x / self.page_width) * self.slide_w_mm:.3f}mm"

    def odp_y(self, y):
        return f"{(y / self.page_height) * self.slide_h_mm:.3f}mm"

    #def odp_pt(self, font_size):
        # Convert pymdslides font units to physical points on a 160mm wide slide
        # In backend_html: 32 * font_size / page_width (% of slide width)
        # 1% of 160mm = 1.6mm = 4.535pt; tuned by 0.42 factor to match HTML rendering
    #    pt = font_size * 0.42 * (self.slide_w_mm / 160.0)
    #    return f"{pt:.1f}pt"

    def odp_pt(self, font_size):
        # Exact physical match to backend_html's (32 * font_size / page_width) * 1% of slide_w_mm:
        cqw_count = (32.0 * font_size) / self.page_width
        size_mm = cqw_count * (self.slide_w_mm / 100.0)
        size_pt = size_mm * (72.0 / 25.4)  # 1 inch = 25.4 mm = 72 pt
        return f"{size_pt:.2f}pt"


    def unbreakable(self):
        class _Ctx:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return _Ctx()

    def local_context(self, *args, **kwargs):
        class _Ctx:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return _Ctx()

    def rect_clip(self, *args, **kwargs):
        class _Ctx:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return _Ctx()

    def set_logo(self, logo, x, y, w, h):
        if logo and os.path.exists(logo):
            self.logo = logo
            self.logo_x = x
            self.logo_y = y
            self.logo_w = w
            self.logo_h = h

    def add_page(self):
        # Before starting a new page, place the logo on top of the previous page
        if self.current_page_el is not None and self.logo is not None:
            self._place_logo_on_current_page()

        self.override_font = {}
        self.override_font_size = {}
        self.pages_count += 1

        page_style_name = self._create_page_style('#ffffff')
        self.current_page_style_name = page_style_name

        self.current_page_el = ET.SubElement(self.presentation, qn('draw:page'), {
            qn('draw:name'): f"page-{self.pages_count}",
            qn('draw:style-name'): page_style_name,
            qn('draw:master-page-name'): "Default"
        })
        return True

    def _place_logo_on_current_page(self):
        self.image(
            self.logo,
            x=self.logo_x,
            y=self.logo_y,
            w=self.logo_w,
            h=self.logo_h,
            crop_images=False
        )

    def _create_page_style(self, bg_hex):
        style_name = self._next_style_id('dp')
        st = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): style_name,
            qn('style:family'): 'drawing-page'
        })
        ET.SubElement(st, qn('style:drawing-page-properties'), {
            qn('presentation:background-visible'): 'true',
            qn('presentation:background-objects-visible'): 'true',
            qn('draw:fill'): 'solid',
            qn('draw:fill-color'): bg_hex,
            qn('presentation:display-footer'): 'false',
            qn('presentation:display-page-number'): 'false',
            qn('presentation:display-date-time'): 'false',
        })
        return style_name

    def set_background_color(self, color):
        bg_hex = dec_to_hex_color(color)
        if self.current_page_el is not None:
            new_style = self._create_page_style(bg_hex)
            self.current_page_el.set(qn('draw:style-name'), new_style)
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
        if font_name and font_name.strip():
            self.override_font[category] = font_name
        if font_size is not None:
            self.override_font_size[category] = font_size
        return True

    def set_font_size(self, category, font_size):
        if font_size is not None:
            self.override_font_size[category] = font_size
        return True

    def set_title(self, title, *args, **kwargs):
        if title:
            self.doc_title = title
        return True

    def set_producer(self, *args, **kwargs):
        return True

    def set_creator(self, *args, **kwargs):
        if args:
            self.doc_creator = str(args[0])
        return True

    def set_creation_date(self, *args, **kwargs):
        if args:
            self.doc_date = str(args[0])
        return True

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def set_xy(self, x, y):
        self.x = x
        self.y = y
        return True

    def get_format(self):
        return 'odp'

    def get_string_width(self, text):
        return len(text) * 10

    def rect(self, x, y, w, h, round_corners=False, corner_radius=0, *args, **kwargs):
        gr_style = self._next_style_id('gr_rect')
        st = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): gr_style,
            qn('style:family'): 'graphic'
        })
        props = {
            qn('draw:stroke'): 'solid',
            qn('svg:stroke-width'): '0.25mm',
            qn('svg:stroke-color'): self.draw_color,
            qn('draw:fill'): 'solid',
            qn('draw:fill-color'): self.fill_color,
        }
        ET.SubElement(st, qn('style:graphic-properties'), props)

        attrs = {
            qn('draw:style-name'): gr_style,
            qn('svg:x'): self.odp_x(x),
            qn('svg:y'): self.odp_y(y),
            qn('svg:width'): self.odp_x(w),
            qn('svg:height'): self.odp_y(h),
        }
        if round_corners and corner_radius > 0:
            attrs[qn('draw:corner-radius')] = self.odp_x(corner_radius)
        ET.SubElement(self.current_page_el, qn('draw:rect'), attrs)
        return True

    def _create_frame_graphic_style(self, valign='top', fill='none', fill_color='#ffffff',
                                    fill_opacity=1.0, stroke='none', stroke_color='#000000',
                                    stroke_opacity=1.0, padding_mm='0mm', corner_radius_mm=None):
        gr_name = self._next_style_id('gr')
        st = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): gr_name,
            qn('style:family'): 'graphic'
        })
        odp_valign = {'top': 'top', 'center': 'middle', 'bottom': 'bottom', 'flex-end': 'bottom'}.get(valign, 'top')
        props = {
            qn('draw:fill'): fill,
            qn('draw:stroke'): stroke,
            qn('draw:textarea-vertical-align'): odp_valign,
            qn('fo:padding-top'): padding_mm,
            qn('fo:padding-bottom'): padding_mm,
            qn('fo:padding-left'): padding_mm,
            qn('fo:padding-right'): padding_mm,
        }
        if fill == 'solid':
            props[qn('draw:fill-color')] = fill_color
            if fill_opacity < 1.0:
                props[qn('draw:opacity')] = f"{int(fill_opacity * 100)}%"
        if stroke == 'solid':
            props[qn('svg:stroke-color')] = stroke_color
            props[qn('svg:stroke-width')] = '0.3mm'
            if stroke_opacity < 1.0:
                props[qn('svg:stroke-opacity')] = f"{int(stroke_opacity * 100)}%"
        if corner_radius_mm:
            props[qn('draw:corner-radius')] = corner_radius_mm
        ET.SubElement(st, qn('style:graphic-properties'), props)
        return gr_name

    def _create_paragraph_style(self, font_family, font_size_pt, color_hex, align='left', margin_bottom='1.5mm', bold=False):
        p_name = self._next_style_id('P')
        st = ET.SubElement(self.auto_styles, qn('style:style'), {
            qn('style:name'): p_name,
            qn('style:family'): 'paragraph'
        })
        fo_align = {'left': 'start', 'start': 'start', 'center': 'center', 'right': 'end', 'end': 'end'}.get(align, 'start')
        ET.SubElement(st, qn('style:paragraph-properties'), {
            qn('fo:text-align'): fo_align,
            qn('fo:margin-top'): '0mm',
            qn('fo:margin-bottom'): margin_bottom,
        })
        t_props = {
            qn('fo:font-family'): font_family,
            qn('fo:font-size'): font_size_pt,
            qn('style:font-size-asian'): font_size_pt,
            qn('style:font-size-complex'): font_size_pt,
            qn('fo:color'): color_hex,
        }
        if bold:
            t_props[qn('fo:font-weight')] = 'bold'
        ET.SubElement(st, qn('style:text-properties'), t_props)
        return p_name

    def _create_list_style(self, font_size_pt, color_hex):
        l_name = self._next_style_id('L')
        lst = ET.SubElement(self.auto_styles, qn('text:list-style'), {
            qn('style:name'): l_name
        })
        bullets = ['•', '◦', '▪']
        for level in range(1, 4):
            lvl_el = ET.SubElement(lst, qn('text:list-level-style-bullet'), {
                qn('text:level'): str(level),
                qn('text:bullet-char'): bullets[(level - 1) % len(bullets)]
            })
            ET.SubElement(lvl_el, qn('style:list-level-properties'), {
                qn('text:space-before'): f"{(level - 1) * 4.5:.1f}mm",
                qn('text:min-label-width'): "4.0mm"
            })
            ET.SubElement(lvl_el, qn('style:text-properties'), {
                qn('fo:font-size'): font_size_pt,
                qn('fo:color'): color_hex
            })
        return l_name

    def textbox(self, lines, x, y, w, h, headlines, h_level=None, align='left',
                markdown_format=True, text_color=None, text_vertical_align=None):
        color_hex = dec_to_hex_color(text_color) if text_color is not None else self.text_color
        valign = text_vertical_align if text_vertical_align else 'top'

        if h_level == 1:
            cat = 'title'
        elif h_level == 2:
            cat = 'subtitle'
        else:
            cat = 'standard'

        font_family = self.override_font.get(cat, self.font_names.get(cat, 'Arial'))
        raw_size = self.override_font_size.get(cat, self.font_sizes.get(cat, 34))
        font_size_pt = self.odp_pt(raw_size)

        gr_style = self._create_frame_graphic_style(valign=valign)
        p_style = self._create_paragraph_style(font_family, font_size_pt, color_hex, align=align)
        l_style = self._create_list_style(font_size_pt, color_hex)

        frame = ET.SubElement(self.current_page_el, qn('draw:frame'), {
            qn('draw:style-name'): gr_style,
            qn('svg:x'): self.odp_x(x),
            qn('svg:y'): self.odp_y(y),
            qn('svg:width'): self.odp_x(w),
            qn('svg:height'): self.odp_y(h),
        })
        tb = ET.SubElement(frame, qn('draw:text-box'))

        if markdown_format:
            new_lines = []
            for line in lines:
                if len(line) > 3 and all(c == '-' for c in line):
                    new_lines.append('')
                new_lines.append(line)
            html_str = md_to_html('\n'.join(new_lines))
            self._append_html_to_textbox(tb, html_str, p_style, l_style, font_family, raw_size, color_hex, align, headlines)
        else:
            p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
            p_el.text = '\n'.join(lines)

        self.x = x
        self.y = y + h
        return x, y + h

    def l4_box(self, lines, x, y, w, h, headlines, align='left', border_color=[0, 0, 0],
               border_opacity=0.75, background_color=[255, 255, 255], background_opacity=0.75,
               markdown_format=True, text_color=None, text_vertical_align=None):
        color_hex = dec_to_hex_color(text_color) if text_color is not None else self.text_color
        bg_hex = dec_to_hex_color(background_color)
        b_hex = dec_to_hex_color(border_color)
        valign = text_vertical_align if text_vertical_align else 'center'

        font_family = self.override_font.get('standard', self.font_names['standard'])
        raw_size = self.override_font_size.get('standard', self.font_sizes['standard'])
        font_size_pt = self.odp_pt(raw_size)

        gr_style = self._create_frame_graphic_style(
            valign=valign,
            fill='solid',
            fill_color=bg_hex,
            fill_opacity=background_opacity,
            stroke='solid',
            stroke_color=b_hex,
            stroke_opacity=border_opacity,
            padding_mm='2.5mm',
            corner_radius_mm='2.0mm'
        )
        p_style = self._create_paragraph_style(font_family, font_size_pt, color_hex, align=align)
        l_style = self._create_list_style(font_size_pt, color_hex)

        frame = ET.SubElement(self.current_page_el, qn('draw:frame'), {
            qn('draw:style-name'): gr_style,
            qn('svg:x'): self.odp_x(x),
            qn('svg:y'): self.odp_y(y),
            qn('svg:width'): self.odp_x(w),
            qn('svg:height'): self.odp_y(h),
        })
        tb = ET.SubElement(frame, qn('draw:text-box'))

        if markdown_format:
            html_str = md_to_html('\n'.join(lines))
            self._append_html_to_textbox(tb, html_str, p_style, l_style, font_family, raw_size, color_hex, align, headlines)
        else:
            p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
            p_el.text = '\n'.join(lines)

        self.x = x
        self.y = y + h
        return True

    def text(self, txt, x, y, headlines, h_level=None, em=10, footer=False, text_color=None, markdown_format=False):
        color_hex = dec_to_hex_color(text_color) if text_color is not None else self.text_color
        cat = 'footer' if footer else ('title' if h_level == 1 else ('subtitle' if h_level == 2 else 'standard'))
        font_family = self.override_font.get(cat, self.font_names.get(cat, 'Arial'))
        raw_size = self.override_font_size.get(cat, self.font_sizes.get(cat, 14 if footer else 34))
        font_size_pt = self.odp_pt(raw_size)

        gr_style = self._create_frame_graphic_style(valign='top')
        p_style = self._create_paragraph_style(font_family, font_size_pt, color_hex, align='left', margin_bottom='0.5mm')
        l_style = self._create_list_style(font_size_pt, color_hex)

        # Give footer/text full remaining width so it doesn't wrap prematurely
        w = self.page_width - x - self.formatting['dimensions']['margin_footer']
        line_count = max(1, txt.count('<br>') + txt.count('\n') + 1)
        h = max(em * line_count * 1.5, 12)

        frame = ET.SubElement(self.current_page_el, qn('draw:frame'), {
            qn('draw:style-name'): gr_style,
            qn('svg:x'): self.odp_x(x),
            qn('svg:y'): self.odp_y(y),
            qn('svg:width'): self.odp_x(w),
            qn('svg:height'): self.odp_y(h),
        })
        tb = ET.SubElement(frame, qn('draw:text-box'))

        if markdown_format:
            txt_clean = txt.replace('&nbsp;', '\u00a0')
            html_str = md_to_html(txt_clean)
            self._append_html_to_textbox(tb, html_str, p_style, l_style, font_family, raw_size, color_hex, 'left', headlines)
        else:
            p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
            p_el.text = txt.replace('&nbsp;', '\u00a0')

        self.x = x
        self.y = y + em
        return True

    def _append_html_to_textbox(self, tb, html_str, p_style, l_style, font_family, raw_size, color_hex, align, headlines):
        html_str = html_str.replace('&nbsp;', '\u00a0')
        tree = fromstring(html_str)
        for node in tree:
            tag = node.tag.lower() if isinstance(node.tag, str) else ''
            if tag == 'p':
                p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
                self._append_inline_nodes(p_el, node, headlines)
            elif tag in ('ul', 'ol'):
                self._append_list_node(tb, node, p_style, l_style, headlines, is_root=True)
            elif tag in ('h1', 'h2', 'h3', 'h4'):
                h_pt = self.odp_pt(raw_size * 1.15)
                h_p_style = self._create_paragraph_style(font_family, h_pt, color_hex, align=align, bold=True)
                p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): h_p_style})
                self._append_inline_nodes(p_el, node, headlines)
            elif tag == 'hr':
                hr_style = self._create_paragraph_style(font_family, self.odp_pt(raw_size * 0.5), '#aaaaaa', align='center')
                p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): hr_style})
                p_el.text = '────────────────────────────────────────'
            elif tag == 'table':
                # Fallback: render table rows as lines inside the text box
                for tr in node.xpath('.//tr'):
                    cells = [''.join(td.itertext()).strip() for td in tr.xpath('./th|./td')]
                    p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
                    p_el.text = '   |   '.join(cells)
            else:
                p_el = ET.SubElement(tb, qn('text:p'), {qn('text:style-name'): p_style})
                self._append_inline_nodes(p_el, node, headlines)

    def _append_list_node(self, parent_el, ul_node, p_style, l_style, headlines, is_root=False):
        attrs = {qn('text:style-name'): l_style} if is_root else {}
        list_el = ET.SubElement(parent_el, qn('text:list'), attrs)
        for li in ul_node:
            if not isinstance(li.tag, str) or li.tag.lower() != 'li':
                continue
            item_el = ET.SubElement(list_el, qn('text:list-item'))
            p_el = ET.SubElement(item_el, qn('text:p'), {qn('text:style-name'): p_style})
            if li.text and li.text.strip():
                p_el.text = li.text.strip()

            for child in li:
                ctag = child.tag.lower() if isinstance(child.tag, str) else ''
                if ctag in ('ul', 'ol'):
                    self._append_list_node(item_el, child, p_style, l_style, headlines, is_root=False)
                elif ctag == 'p':
                    self._append_inline_nodes(p_el, child, headlines)
                else:
                    self._append_single_inline(p_el, child, headlines)

    def _append_inline_nodes(self, target_el, src_node, headlines):
        if src_node.text:
            target_el.text = (target_el.text or '') + src_node.text
        for child in src_node:
            self._append_single_inline(target_el, child, headlines)

    def _append_single_inline(self, target_el, child, headlines):
        ctag = child.tag.lower() if isinstance(child.tag, str) else ''
        if ctag == 'br':
            br_el = ET.SubElement(target_el, qn('text:line-break'))
            if child.tail:
                br_el.tail = child.tail.lstrip('\n')
        elif ctag in ('strong', 'b'):
            span = ET.SubElement(target_el, qn('text:span'), {qn('text:style-name'): 'T_Bold'})
            self._append_inline_nodes(span, child, headlines)
            if child.tail:
                span.tail = child.tail
        elif ctag in ('em', 'i'):
            span = ET.SubElement(target_el, qn('text:span'), {qn('text:style-name'): 'T_Italic'})
            self._append_inline_nodes(span, child, headlines)
            if child.tail:
                span.tail = child.tail
        elif ctag == 'code':
            span = ET.SubElement(target_el, qn('text:span'), {qn('text:style-name'): 'T_Code'})
            self._append_inline_nodes(span, child, headlines)
            if child.tail:
                span.tail = child.tail
        elif ctag == 'a':
            href = child.get('href', '')
            if href.startswith('#') and headlines:
                target_title = href[1:].strip()
                if target_title in headlines:
                    page_no = headlines.index(target_title) + 1
                    href = f"#page-{page_no}"
            a_el = ET.SubElement(target_el, qn('text:a'), {
                qn('xlink:type'): 'simple',
                qn('xlink:href'): href
            })
            self._append_inline_nodes(a_el, child, headlines)
            if child.tail:
                a_el.tail = child.tail
        else:
            self._append_inline_nodes(target_el, child, headlines)
            if child.tail:
                if len(target_el) > 0:
                    target_el[-1].tail = (target_el[-1].tail or '') + child.tail
                else:
                    target_el.text = (target_el.text or '') + child.tail

    def image(self, file, x, y, w, h, crop_images=False, link=None):
        if w <= 0 or h <= 0:
            return False

        input_file = file.split('#')[0]
        page_no = file.split('#')[1] if '#' in file else '0'
        ext = os.path.splitext(input_file)[1][1:].lower()

        if not os.path.exists(input_file):
            print(f"Warning: Image file '{input_file}' not found for ODP.")
            return False

        # Rasterize PDF/EPS/SVG or WebP if needed so LibreOffice Impress displays it reliably
        usable_path = input_file
        if ext in ('pdf', 'eps', 'ps'):
            png_name = f"{os.path.splitext(os.path.basename(input_file))[0]}-{page_no}.png"
            usable_path = os.path.join(self.pictures_dir, png_name)
            if not os.path.exists(usable_path) or self.overwrite_images:
                os.system(f"magick -density 150 \"{input_file}[{page_no}]\" \"{usable_path}\"")
            ext = 'png'

        # Compute placement & optional cropping
        draw_x, draw_y, draw_w, draw_h = x, y, w, h
        if ext in ('svg',):
            # Copy SVG directly into Pictures/
            pic_filename = os.path.basename(usable_path)
            dest_path = os.path.join(self.pictures_dir, pic_filename)
            shutil.copyfile(usable_path, dest_path)
            mime_type = 'image/svg+xml'
        else:
            with Image.open(usable_path) as im:
                im = ImageOps.exif_transpose(im)
                im_w, im_h = im.size
                im_aspect = im_w / max(1, im_h)
                box_aspect = w / max(1, h)

                digest = hashlib.md5(f"{usable_path}_{w}_{h}_{crop_images}".encode()).hexdigest()[:8]
                pic_filename = f"{os.path.splitext(os.path.basename(usable_path))[0]}_{digest}.png"
                dest_path = os.path.join(self.pictures_dir, pic_filename)

                if crop_images:
                    # Center-crop to match exact box aspect ratio (object-fit: cover)
                    if im_aspect > box_aspect:
                        target_h = min(im_h, 2160)
                        target_w = max(1, round(target_h * box_aspect))
                    else:
                        target_w = min(im_w, 3840)
                        target_h = max(1, round(target_w / box_aspect))
                    if not os.path.exists(dest_path) or self.overwrite_images:
                        cropped = ImageOps.fit(im, (target_w, target_h), method=Image.Resampling.LANCZOS)
                        cropped.save(dest_path, format='PNG')
                else:
                    # Fit inside bounding box preserving aspect ratio (object-fit: contain)
                    if im_aspect > box_aspect:
                        draw_w = w
                        draw_h = w / im_aspect
                        draw_x = x
                        draw_y = y + (h - draw_h) / 2.0
                    else:
                        draw_h = h
                        draw_w = h * im_aspect
                        draw_x = x + (w - draw_w) / 2.0
                        draw_y = y
                    if not os.path.exists(dest_path) or self.overwrite_images:
                        im.save(dest_path, format='PNG')
                mime_type = 'image/png'

        rel_pic_path = f"Pictures/{pic_filename}"
        self.manifest_files[rel_pic_path] = mime_type

        gr_style = self._create_frame_graphic_style()
        frame = ET.SubElement(self.current_page_el, qn('draw:frame'), {
            qn('draw:style-name'): gr_style,
            qn('svg:x'): self.odp_x(draw_x),
            qn('svg:y'): self.odp_y(draw_y),
            qn('svg:width'): self.odp_x(draw_w),
            qn('svg:height'): self.odp_y(draw_h),
        })
        ET.SubElement(frame, qn('draw:image'), {
            qn('xlink:href'): rel_pic_path,
            qn('xlink:type'): 'simple',
            qn('xlink:show'): 'embed',
            qn('xlink:actuate'): 'onLoad'
        })

        self.set_xy(self.x, self.y + h)
        return True

    def add_link(self, *args, **kwargs):
        return self.pages_count

    def cell(self, *args, **kwargs):
        return True

    def line(self, *args, **kwargs):
        return False

    def table(self, *args, **kwargs):
        return None

    def set_line_width(self, *args, **kwargs):
        return False

    def will_page_break(self, *args, **kwargs):
        return False

    def _build_styles_xml(self):
        root = ET.Element(qn('office:document-styles'), {qn('office:version'): "1.2"})
        styles = ET.SubElement(root, qn('office:styles'))
        auto_styles = ET.SubElement(root, qn('office:automatic-styles'))
        master_styles = ET.SubElement(root, qn('office:master-styles'))

        page_layout = ET.SubElement(auto_styles, qn('style:page-layout'), {
            qn('style:name'): 'PM1'
        })
        ET.SubElement(page_layout, qn('style:page-layout-properties'), {
            qn('fo:margin-top'): '0mm',
            qn('fo:margin-bottom'): '0mm',
            qn('fo:margin-left'): '0mm',
            qn('fo:margin-right'): '0mm',
            qn('fo:page-width'): f"{self.slide_w_mm:.2f}mm",
            qn('fo:page-height'): f"{self.slide_h_mm:.2f}mm",
            qn('style:print-orientation'): 'landscape'
        })

        dp_default = ET.SubElement(styles, qn('style:style'), {
            qn('style:name'): 'dp_default',
            qn('style:family'): 'drawing-page'
        })
        ET.SubElement(dp_default, qn('style:drawing-page-properties'), {
            qn('presentation:background-visible'): 'true',
            qn('presentation:background-objects-visible'): 'true',
            qn('draw:fill'): 'solid',
            qn('draw:fill-color'): '#ffffff'
        })

        ET.SubElement(master_styles, qn('style:master-page'), {
            qn('style:name'): 'Default',
            qn('style:page-layout-name'): 'PM1',
            qn('draw:style-name'): 'dp_default'
        })
        return root

    def _build_meta_xml(self):
        root = ET.Element(qn('office:document-meta'), {qn('office:version'): "1.2"})
        meta = ET.SubElement(root, qn('office:meta'))
        title_el = ET.SubElement(meta, qn('dc:title'))
        title_el.text = self.doc_title
        gen_el = ET.SubElement(meta, qn('meta:generator'))
        gen_el.text = self.doc_creator
        if self.doc_date:
            date_el = ET.SubElement(meta, qn('dc:date'))
            date_el.text = self.doc_date
        return root

    def _build_manifest_xml(self):
        root = ET.Element(qn('manifest:manifest'), {qn('manifest:version'): "1.2"})
        ET.SubElement(root, qn('manifest:file-entry'), {
            qn('manifest:full-path'): '/',
            qn('manifest:version'): '1.2',
            qn('manifest:media-type'): 'application/vnd.oasis.opendocument.presentation'
        })
        for xml_file in ('content.xml', 'styles.xml', 'meta.xml'):
            ET.SubElement(root, qn('manifest:file-entry'), {
                qn('manifest:full-path'): xml_file,
                qn('manifest:media-type'): 'text/xml'
            })
        for rel_path, mime in self.manifest_files.items():
            ET.SubElement(root, qn('manifest:file-entry'), {
                qn('manifest:full-path'): rel_path,
                qn('manifest:media-type'): mime
            })
        return root

    def output(self):
        # Place logo on the final slide if present
        if self.current_page_el is not None and self.logo is not None:
            self._place_logo_on_current_page()

        styles_root = self._build_styles_xml()
        meta_root = self._build_meta_xml()
        manifest_root = self._build_manifest_xml()

        print('writing file', self.odp_output_filename)
        with zipfile.ZipFile(self.odp_output_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            # ODF specification requires 'mimetype' to be first and uncompressed
            zf.writestr('mimetype', 'application/vnd.oasis.opendocument.presentation', compress_type=zipfile.ZIP_STORED)

            zf.writestr('content.xml', ET.tostring(self.content_root, xml_declaration=True, encoding='UTF-8'))
            zf.writestr('styles.xml', ET.tostring(styles_root, xml_declaration=True, encoding='UTF-8'))
            zf.writestr('meta.xml', ET.tostring(meta_root, xml_declaration=True, encoding='UTF-8'))
            zf.writestr('META-INF/manifest.xml', ET.tostring(manifest_root, xml_declaration=True, encoding='UTF-8'))

            for rel_path in self.manifest_files:
                abs_path = os.path.join(self.work_dir, rel_path)
                if os.path.exists(abs_path):
                    zf.write(abs_path, rel_path)

        # Also copy to <deck_name>.odp in the current directory for convenience
        shutil.copyfile(self.odp_output_filename, self.odp_root_filename)
        print('copied odp file to', self.odp_root_filename)
        shutil.rmtree(self.work_dir, ignore_errors=True)
        return True


def md_to_html(md):
    md_, formulas_ = md_extract_formulas(md)
    html = markdown(md_, extras=['cuddled-lists', 'tables'])
    return md_reconstruct_math(html, formulas_)


def md_extract_formulas(md):
    md_sane_lines = []
    formulas = []
    number = 0
    for line in md.split('\n'):
        if '$' in line:
            formula_starts_ends = []
            formula_start = None
            for p in range(len(line)):
                if line[p] == '$' and (p == 0 or line[p - 1] != '\\'):
                    if formula_start is None:
                        formula_start = p
                    else:
                        formula_starts_ends.append((formula_start, p + 1))
                        formula_start = None
            new_line = ''
            pos = 0
            for (s, e) in formula_starts_ends:
                new_line += line[pos:s] + f'${number}$'
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
    for (n, f) in formulas:
        html = html.replace(f'${n}$', f)
    return html


def dec_to_hex_color(color):
    if isinstance(color, str):
        if color.startswith('#') and len(color) >= 7:
            return color[:7]
        if color.startswith('#') and len(color) == 4:
            return '#' + color[1]*2 + color[2]*2 + color[3]*2
        named = {
            'white': '#ffffff', 'grey': '#646464', 'black': '#000000',
            'orange': '#ffb400', 'red': '#ff0000', 'green': '#00ff00',
            'blue': '#0000ff', 'yellow': '#ffff00', 'darkred': '#640000',
            'darkgreen': '#006400', 'darkblue': '#000064'
        }
        return named.get(color, '#000000')
    elif isinstance(color, list):
        return '#' + ''.join(hex(c)[2:].rjust(2, '0') for c in color[:3])
    elif isinstance(color, int):
        h = hex(color)[2:].rjust(2, '0')
        return f'#{h}{h}{h}'
    return '#000000'


def font_file_to_font_name(filename):
    filename = os.path.basename(filename).split('.')[0]
    words = [w for w in filename.replace('-', ' ').split() if w]
    return ' '.join(words)


