from lxml import etree
import os
from datetime import datetime

class BackendODP:
    def __init__(self, formatting):
        self.formatting = formatting
        self.pages = []
        self.meta = {
            "title": "Untitled",
            "producer": "Unknown",
            "creator": "Unknown",
            "creation_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def add_page(self):
        page = {
            "background_color": None,
            "elements": [],
        }
        self.pages.append(page)

    def set_background_color(self, color):
        if self.pages:
            self.pages[-1]["background_color"] = color

    def set_text_color(self, color):
        self.text_color = color

    def set_font(self, font):
        self.font = font

    def set_font_size(self, font_size):
        self.font_size = font_size

    def set_xy(self, x, y):
        self.current_x = x
        self.current_y = y

    def textbox(self, lines, x, y, width, height, h_level=None, align="left"):
        self._add_element("textbox", {
            "content": lines,
            "x": x, "y": y,
            "width": width, "height": height,
            "h_level": h_level,
            "align": align,
        })

    def text(self, txt, x, y, width, height, h_level=None, align="left"):
        self._add_element("text", {
            "content": txt,
            "x": x, "y": y,
            "width": width, "height": height,
            "h_level": h_level,
            "align": align,
        })

    def l4_box(self, lines, x, y, width, height):
        self._add_element("l4_box", {
            "content": lines,
            "x": x, "y": y,
            "width": width, "height": height,
        })

    def image(self, image_to_display, x, y, w, h, link=None, crop_images=False):
        self._add_element("image", {
            "path": image_to_display,
            "x": x, "y": y,
            "width": w, "height": h,
            "link": link,
            "crop": crop_images,
        })

    def set_logo(self, image, x, y, w, h):
        self.logo = {"path": image, "x": x, "y": y, "width": w, "height": h}

    def set_title(self, title):
        self.meta["title"] = title

    def set_producer(self, producer):
        self.meta["producer"] = producer

    def set_creator(self, creator):
        self.meta["creator"] = creator

    def set_creation_date(self, creation_date):
        self.meta["creation_date"] = creation_date

    def output(self, filename):
        presentation = etree.Element("office:document-content", {
            "xmlns:office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
            "xmlns:draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
            "xmlns:text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        })

        # Add presentation metadata
        meta = etree.SubElement(presentation, "office:meta")
        for key, value in self.meta.items():
            etree.SubElement(meta, f"meta:{key}").text = value

        # Add slides
        for page in self.pages:
            slide = etree.SubElement(presentation, "draw:page", {
                "draw:name": f"Slide {len(presentation)}",
                "draw:style-name": "dp1",
                "draw:master-page-name": "Default",
            })
            if page["background_color"]:
                slide.set("draw:background-color", page["background_color"])
            for element in page["elements"]:
                self._add_element_to_slide(slide, element)

        tree = etree.ElementTree(presentation)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        tree.write(filename, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    def _add_element(self, element_type, element_data):
        if self.pages:
            element = {"type": element_type, **element_data}
            self.pages[-1]["elements"].append(element)

    def _add_element_to_slide(self, slide, element):
        if element["type"] == "textbox":
            textbox = etree.SubElement(slide, "draw:text-box", {
                "svg:x": str(element["x"]),
                "svg:y": str(element["y"]),
                "svg:width": str(element["width"]),
                "svg:height": str(element["height"]),
                "text:align": element["align"],
            })
            etree.SubElement(textbox, "text:p").text = element["content"]

        elif element["type"] == "image":
            etree.SubElement(slide, "draw:image", {
                "xlink:href": element["path"],
                "svg:x": str(element["x"]),
                "svg:y": str(element["y"]),
                "svg:width": str(element["width"]),
                "svg:height": str(element["height"]),
                "xlink:type": "simple",
            })

        # Handle other element types as needed


