# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

import os
import io
import shutil
import re
from PIL import Image
from odf.opendocument import OpenDocumentPresentation
from odf.style import (Style, MasterPage, PageLayout, PageLayoutProperties, 
                       TextProperties, ParagraphProperties, GraphicProperties, 
                       DrawingPageProperties, FontFace)
from odf.text import P, H, Span, A
from odf.draw import Page, Frame, TextBox, Image as OdfImage, Rect
from odf import teletype

class backend_odp:
    def __init__(self, input_file, formatting, script_home, overwrite_images=False):
        self.doc = OpenDocumentPresentation()
        self.output_filename = os.path.join(os.path.splitext(input_file)[0], 'slides.odp')
        self.script_home = script_home
        self.formatting = formatting
        self.overwrite_images = overwrite_images
        
        # Dimensions setup
        self.input_width = formatting['dimensions']['page_width']
        self.input_height = formatting['dimensions']['page_height']
        
        # ODP Standard Screen is usually 28cm x 15.75cm (16:9)
        # We scale inputs to fit this physical size
        self.odp_width_cm = 28.0
        self.scale_factor = self.odp_width_cm / self.input_width
        self.odp_height_cm = self.input_height * self.scale_factor

        # State management
        self.pages = []
        self.current_page = None
        self.style_cache = {} # Cache for auto-generated styles to reduce file size
        self.master_page_name = "StandardMaster"
        self.font_decls = {}

        # Initialize Fonts
        self._setup_fonts()
        
        # Setup Standard Styles
        self._setup_standard_styles()

    def _setup_fonts(self):
        """Declare fonts in the ODP document based on config"""
        font_cats = ['title', 'standard', 'footer', 'subtitle']
        for cat in font_cats:
            # Check for font name in config
            font_name_key = f'font_name_{cat}'
            font_file_key = f'font_file_{cat}'
            
            font_name = None
            if 'fonts' in self.formatting:
                if font_name_key in self.formatting['fonts']:
                    font_name = self.formatting['fonts'][font_name_key]
                elif font_file_key in self.formatting['fonts']:
                    # Fallback: guess name from filename
                    fname = os.path.basename(self.formatting['fonts'][font_file_key])
                    font_name = os.path.splitext(fname)[0]
            
            if not font_name:
                font_name = "Arial" # Fallback

            if font_name not in self.font_decls:
                decl = FontFace(name=font_name, fontfamily=font_name)
                self.doc.fontfacedecls.addElement(decl)
                self.font_decls[cat] = font_name
            else:
                self.font_decls[cat] = font_name

    def _setup_standard_styles(self):
        """Create basic layout styles"""
        # 1. Page Layout (Geometry)
        pl = PageLayout(name="PL1")
        pl.addElement(PageLayoutProperties(pagewidth=f"{self.odp_width_cm}cm", 
                                           pageheight=f"{self.odp_height_cm}cm",
                                           margin="0cm",
                                           printorientation="landscape"))
        self.doc.automaticstyles.addElement(pl)

        # 2. Master Page
        self.master_page = MasterPage(name=self.master_page_name, pagelayoutname=pl)
        self.doc.masterstyles.addElement(self.master_page)

    def _get_style_name(self, family, properties):
        """
        Generates or retrieves a style based on a dictionary of properties.
        Key is a tuple of sorted items to ensure uniqueness.
        """
        key = (family, tuple(sorted(properties.items())))
        if key in self.style_cache:
            return self.style_cache[key]

        style_name = f"AutoStyle_{len(self.style_cache)}"
        style = Style(name=style_name, family=family)
        
        # Split properties into Text, Paragraph, and Graphic properties
        text_props_attr = {}
        para_props_attr = {}
        graphic_props_attr = {}

        for k, v in properties.items():
            if k.startswith("fo:") or k.startswith("style:font"):
                # Rough heuristic: font stuff goes to TextProperties
                # alignment goes to ParagraphProperties
                if "align" in k:
                    para_props_attr[k] = v
                else:
                    text_props_attr[k] = v
            elif k.startswith("svg:") or k.startswith("draw:"):
                graphic_props_attr[k] = v

        if text_props_attr:
            style.addElement(TextProperties(attributes=text_props_attr))
        if para_props_attr:
            style.addElement(ParagraphProperties(attributes=para_props_attr))
        if graphic_props_attr:
            style.addElement(GraphicProperties(attributes=graphic_props_attr))

        self.doc.automaticstyles.addElement(style)
        self.style_cache[key] = style_name
        return style_name

    def _cm(self, val):
        """Convert input unit (pixels/layout units) to cm string"""
        return f"{val * self.scale_factor:.3f}cm"

    def _hex_color(self, color, alpha=1.0):
        """Convert list/name/int color to Hex string"""
        # Reuse logic from backend_html but return simple hex for ODP
        if isinstance(color, str):
            if color.startswith("#"):
                return color[:7] # ODP mostly handles 6-char hex
            map_c = {
                'white': '#ffffff', 'black': '#000000', 'grey': '#646464',
                'red': '#ff0000', 'blue': '#0000ff', 'green': '#00ff00',
                # Add others if needed
            }
            return map_c.get(color, '#000000')
        elif isinstance(color, list):
            return '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
        return '#000000'

    def unbreakable(self):
        class Context:
            def __enter__(self_ctx): pass
            def __exit__(self_ctx, *args): pass
        return Context()

    def local_context(self, *args, **kwargs):
        # ODP doesn't really have a context stack for drawing attributes in the same way
        # We will just pass these kwargs to the specific drawing methods
        class Context:
            def __enter__(self_ctx): pass
            def __exit__(self_ctx, *args): pass
        return Context()

    def add_page(self):
        self.current_page = Page(stylename=self.master_page_name, masterpagename=self.master_page_name)
        self.doc.presentation.addElement(self.current_page)
        
        # Reset overrides per page
        self.override_font = {}
        self.override_font_size = {}
        return True

    def set_background_color(self, color):
        hex_c = self._hex_color(color)
        # To set background, we need a style on the DrawingPageProperties of the page (or master page)
        # Since pymdslides calls this per page, we create a specific style for this page
        props = {'draw:fill': 'solid', 'draw:fill-color': hex_c}
        style_name = self._get_style_name("drawing-page", props)
        # We update the current page's stylename. 
        # Note: In ODF, a page refers to a masterpage, but can also have its own layout style.
        # Actually, 'draw:page' attribute 'draw:style-name' points to a style with 'drawing-page' family.
        self.current_page.setAttribute('stylename', style_name)

    def set_text_color(self, color):
        self.current_text_color = self._hex_color(color)

    def set_font_size(self, category, size):
        self.override_font_size[category] = size

    def set_font(self, category, name, size):
        if name: self.override_font[category] = name
        if size: self.override_font_size[category] = size

    def _get_font_props(self, category, h_level=None):
        """Calculate font properties based on defaults + overrides"""
        
        # 1. Determine Font Family
        font_name = self.font_decls.get('standard', 'Arial')
        if category in self.font_decls:
            font_name = self.font_decls[category]
        if category in self.override_font:
            font_name = self.override_font[category]

        # 2. Determine Size
        size = 24 # Default
        
        # Get from config dimensions if available
        dim_key = f'font_size_{category}'
        if 'dimensions' in self.formatting and dim_key in self.formatting['dimensions']:
             size = self.formatting['dimensions'][dim_key]
        
        # H-level scaling overrides
        if h_level == 1:
            if 'dimensions' in self.formatting and 'font_size_title' in self.formatting['dimensions']:
                size = self.formatting['dimensions']['font_size_title']
        elif h_level == 2:
            if 'dimensions' in self.formatting and 'font_size_subtitle' in self.formatting['dimensions']:
                size = self.formatting['dimensions']['font_size_subtitle']

        # Manual overrides
        if category in self.override_font_size:
            size = self.override_font_size[category]

        # Convert to points (approximate conversion from pymdslides arbitrary units)
        # Pymdslides assumes 480 width. ODP is 28cm.
        # Ratio is handled by scale_factor.
        # If input size is 34 (standard), output should be legible.
        # Let's assume input units map roughly linearly to ODP points via the scale factor * some constant.
        # Empirically: input 34 -> ~18pt on a 16:9 slide. 
        # Let's try direct scaling: size * scale_factor * 0.7 
        # (34 * 0.058 * constant... needs tuning).
        # Better approach: 
        # Standard input height is 270. ODP height 15.75cm.
        # Font size 34 is 34/270 = 12.5% of height.
        # 12.5% of 15.75cm = 1.96cm. 1.96cm is ~55pt. That's HUGE.
        # Let's look at config pixel_per_mm = 0.15.
        # Size 34 corresponds to .15. 
        # This implies size is in pixels. 
        # ODP uses points. 1 px approx 0.75 pt.
        pt_size = size * 0.75 
        
        props = {
            'style:font-name': font_name,
            'fo:font-size': f"{pt_size}pt",
            'fo:color': self.current_text_color if hasattr(self, 'current_text_color') else '#000000'
        }
        return props

    def _render_markdown_text(self, parent_element, text, style_name):
        """Parses basic Markdown (bold/italic) and adds spans to parent"""
        # Very basic parser: split by ** then *
        # Note: This doesn't handle overlapping nested styles perfectly, but suffices for slides.
        
        # Create a Paragraph
        p = P(stylename=style_name)
        parent_element.addElement(p)

        # Regex for bold: **text**
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                content = part[2:-2]
                # Handle Italic inside Bold
                sub_parts = re.split(r'(\*.*?\*)', content)
                for sub in sub_parts:
                    if sub.startswith('*') and sub.endswith('*'):
                        # Bold + Italic
                        span = Span(text=sub[1:-1])
                        # We need a style that combines bold and italic of the parent
                        # For simplicity, let's just use a bold-italic style or nested spans
                        # ODF handles nested spans poorly visually if styles conflict, 
                        # but we need a style with fo:font-weight="bold" and fo:font-style="italic"
                        # Create specific style on fly?
                        bi_props = {'fo:font-weight': 'bold', 'fo:font-style': 'italic'}
                        bi_style = self._get_style_name('text', bi_props)
                        span.setAttribute('stylename', bi_style)
                        p.addElement(span)
                    elif sub:
                        # Bold only
                        span = Span(text=sub)
                        b_props = {'fo:font-weight': 'bold'}
                        b_style = self._get_style_name('text', b_props)
                        span.setAttribute('stylename', b_style)
                        p.addElement(span)
            else:
                # Handle Italic outside Bold
                sub_parts = re.split(r'(\*.*?\*)', part)
                for sub in sub_parts:
                    if sub.startswith('*') and sub.endswith('*'):
                        span = Span(text=sub[1:-1])
                        i_props = {'fo:font-style': 'italic'}
                        i_style = self._get_style_name('text', i_props)
                        span.setAttribute('stylename', i_style)
                        p.addElement(span)
                    elif sub:
                        # Plain text
                        teletype.addTextToElement(p, sub)

    def textbox(self, lines, x, y, w, h, headlines, h_level=None, align='left', markdown_format=True, text_color=None, text_vertical_align=None):
        # 1. Create Frame
        frame_style_props = {
            'svg:stroke': 'none',
            'svg:fill': 'none',
        }
        
        # Vertical alignment in ODP is a property of the Draw Frame's text box options
        if text_vertical_align:
            map_v = {'top': 'top', 'center': 'middle', 'bottom': 'bottom'}
            frame_style_props['draw:textarea-vertical-align'] = map_v.get(text_vertical_align, 'top')

        frame_style = self._get_style_name("graphic", frame_style_props)

        frame = Frame(stylename=frame_style, 
                      x=self._cm(x), y=self._cm(y), 
                      width=self._cm(w), height=self._cm(h))
        self.current_page.addElement(frame)

        # 2. Create TextBox
        textbox = TextBox()
        frame.addElement(textbox)

        # 3. Determine Styles
        cat = 'standard'
        if h_level == 1: cat = 'title'
        elif h_level == 2: cat = 'subtitle'
        
        font_props = self._get_font_props(cat, h_level)
        
        if text_color:
            font_props['fo:color'] = self._hex_color(text_color)
        
        # Paragraph Alignment
        map_a = {'left': 'start', 'right': 'end', 'center': 'center', 'justify': 'justify'}
        font_props['fo:text-align'] = map_a.get(align, 'start')

        # Create the style name for paragraphs in this box
        p_style = self._get_style_name("paragraph", font_props)

        # 4. Add Content
        for line in lines:
            if not line.strip():
                # Empty paragraph
                textbox.addElement(P(stylename=p_style))
                continue
            
            if markdown_format:
                self._render_markdown_text(textbox, line, p_style)
            else:
                p = P(stylename=p_style, text=line)
                textbox.addElement(p)
        
        return x, y+h

    def text(self, txt, x, y, headlines, h_level=None, em=10, footer=False, text_color=None, markdown_format=False):
        # Similar to textbox but usually single line, specific position
        # Reuse textbox logic with calculated width (ODP needs width)
        # We give it the full remaining width to avoid wrapping eagerly
        w = self.input_width - x - 10 
        h = em * 2 # Height estimate
        
        if footer:
            # Footer usually goes to 'footer' category
            # We call textbox but force category logic via overrides if needed
            # But textbox logic uses h_level to pick category. 
            # We need to ensure correct font.
            self.set_xy(x, y)
            return self.textbox([txt], x, y, w, h, headlines, h_level=h_level, align='left', markdown_format=markdown_format, text_color=text_color)
        
        return self.textbox([txt], x, y, w, h, headlines, h_level=h_level, align='left', markdown_format=markdown_format, text_color=text_color)

    def image(self, file, x, y, w, h, crop_images=False, link=None):
        # 1. Process Image (Crop/Resize) using PIL
        # ODP Frame crops are complex (requires clip-path). 
        # Easier to crop the bitmap itself before embedding.
        
        if not os.path.exists(file):
            print(f"Image not found: {file}")
            return False

        try:
            img = Image.open(file)
            
            if crop_images:
                # Calculate target aspect ratio
                target_ratio = w / h
                img_ratio = img.width / img.height
                
                if img_ratio > target_ratio:
                    # Image is wider than box: crop sides
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) / 2
                    img = img.crop((left, 0, left + new_width, img.height))
                else:
                    # Image is taller than box: crop top/bottom
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) / 2
                    img = img.crop((0, top, img.width, top + new_height))
            
            # Save to BytesIO to add to ODP
            img_buffer = io.BytesIO()
            # Convert to RGB if necessary (e.g. RGBA to JPEG)
            fmt = 'PNG' 
            if file.lower().endswith('.jpg') or file.lower().endswith('.jpeg'):
                fmt = 'JPEG'
                if img.mode == 'P': img = img.convert('RGB')
            
            img.save(img_buffer, format=fmt)
            img_buffer.seek(0)
            
            # 2. Add Picture to internal manifest
            image_ref = self.doc.addPicture(file, mediatype=f"image/{fmt.lower()}", content=img_buffer.read())
            
            # 3. Create Frame
            # Images in ODP are Frames containing an Image element
            frame = Frame(x=self._cm(x), y=self._cm(y), 
                          width=self._cm(w), height=self._cm(h))
            
            odf_img = OdfImage(href=image_ref)
            frame.addElement(odf_img)
            self.current_page.addElement(frame)
            
        except Exception as e:
            print(f"Error processing image {file}: {e}")
            return False

        return True

    def l4_box(self, lines, x, y, w, h, headlines, align='left', 
               border_color=[0,0,0], border_opacity=0.75, 
               background_color=[255,255,255], background_opacity=0.75, 
               markdown_format=True, text_color=None, text_vertical_align=None):
        
        # l4_box is a rectangle with background and border, and text inside.
        
        # 1. Define Graphic Style for the Box (Fill + Stroke)
        fill_c = self._hex_color(background_color)
        stroke_c = self._hex_color(border_color)
        
        # ODF transparency is handled via 'draw:opacity' (0% to 100%)
        # But colors take hex. 
        # Note: 'draw:fill-color' takes hex. 'draw:opacity' applies to whole object usually.
        # Ideally we use styles.
        
        box_props = {
            'draw:fill': 'solid',
            'draw:fill-color': fill_c,
            'svg:stroke-color': stroke_c,
            'svg:stroke-width': '0.05cm',
            'draw:opacity': f"{background_opacity * 100}%"
        }
        
        # Text alignment vertical
        if text_vertical_align:
             map_v = {'top': 'top', 'center': 'middle', 'bottom': 'bottom'}
             box_props['draw:textarea-vertical-align'] = map_v.get(text_vertical_align, 'top')
        
        style_name = self._get_style_name("graphic", box_props)
        
        # 2. Create Frame + Textbox
        frame = Frame(stylename=style_name, 
                      x=self._cm(x), y=self._cm(y), 
                      width=self._cm(w), height=self._cm(h))
        self.current_page.addElement(frame)
        
        textbox = TextBox()
        frame.addElement(textbox)
        
        # 3. Add Text (Similar to textbox method)
        # Need paragraph style
        font_props = self._get_font_props('standard')
        if text_color: font_props['fo:color'] = self._hex_color(text_color)
        
        map_a = {'left': 'start', 'right': 'end', 'center': 'center', 'justify': 'justify'}
        font_props['fo:text-align'] = map_a.get(align, 'start')
        
        p_style = self._get_style_name("paragraph", font_props)
        
        for line in lines:
            if markdown_format:
                self._render_markdown_text(textbox, line, p_style)
            else:
                textbox.addElement(P(stylename=p_style, text=line))

        return True

    def set_xy(self, x, y):
        self.x = x
        self.y = y

    def get_string_width(self, text):
        # Hard to calculate exactly without font metrics libraries.
        # Return a rough estimate based on character count and current font size.
        # This is used for centering footers in main script.
        return len(text) * 10 

    def unbreakable(self):
        return self.local_context()

    def set_logo(self, logo_path, x, y, w, h):
        # We can add the logo to the Master Page so it appears on all slides
        # Or add it to every page manually.
        # Since pymdslides calls set_logo once, but the HTML backend adds it in `add_page` check?
        # Actually HTML backend stores logo info and adds it in `add_page`.
        # We will do the same logic: add to every page manually for simplicity vs Master Page editing.
        self.logo_info = {'path': logo_path, 'x': x, 'y': y, 'w': w, 'h': h}
        # Immediately add to current page if exists
        if self.current_page:
             self.image(logo_path, x, y, w, h)

    def set_title(self, title):
        # Metadata
        pass 

    def set_producer(self, producer):
        pass

    def set_creator(self, creator):
        pass

    def set_creation_date(self, date):
        pass

    def output(self):
        print(f"Saving ODP to {self.output_filename}...")
        self.doc.save(self.output_filename)
        return True

