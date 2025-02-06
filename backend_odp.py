import os
from lxml import etree
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
from datetime import datetime
import shutil


class backend_odp:
    def __init__(self, input_file, formatting, script_home, overwrite_images=True):
        self.formatting = formatting
        self.pages = []
        self.meta = {
            "title": "Untitled",
            "producer": "Unknown",
            "creator": "Unknown",
            "creation_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.images = []
        self.temp_dir = "odp_temp"
        self.input_dir = os.path.dirname(input_file)
        self.odp_output_filename = os.path.splitext(input_file)[0]+'.odp'

    def add_page(self):
        page = {
            "background_color": None,
            "elements": [],
        }
        self.pages.append(page)

    def set_background_color(self, color):
        if self.pages:
            self.pages[-1]["background_color"] = dec_to_hex_color(color)

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




    def set_text_color(self, color):
        self.text_color = dec_to_hex_color(color)

    def set_font(self, title, font, font_size):
        self.font = font
        self.font_size = font_size

    def set_font_size(self, category, font_size):
        self.font_size = font_size

    def set_xy(self, x, y):
        self.current_x = x
        self.current_y = y

    def textbox(self, lines, x, y, w, h, h_level, headlines, text_color, align="left", markdown_format=False):
        self._add_element("textbox", {
            "content": '\n'.join(lines),
            "x": x, "y": y,
            "width": w, "height": h,
            "h_level": h_level,
            "align": align,
        })

    def text(self, txt, x, y, headlines, em, footer, markdown_format, align="left"):
        self._add_element("text", {
            "content": txt,
            "x": x, "y": y,
            "width": 100, "height": 100, # TODO: hard coded width, height
            "h_level": None,
            "align": align,
        })

    def l4_box(
        self, lines, x, y, width, height, headlines, align, border_color,
        border_opacity, background_color, background_opacity,
        markdown_format, text_color
    ):
        self._add_element("l4_box", {
            "content": '\n'.join(lines),
            "x": x, "y": y,
            "width": width, "height": height,
            "headlines": headlines,
            "align": align,
            "border_color": border_color,
            "border_opacity": border_opacity,
            "background_color": background_color,
            "background_opacity": background_opacity,
            "markdown_format": markdown_format,
            "text_color": dec_to_hex_color(text_color),
        })

    def image(self, image_to_display, x, y, w, h, link=None, crop_images=False):
        self.images.append(image_to_display)
        self._add_element("image", {
            "path": os.path.basename(image_to_display),
            "x": x, "y": y,
            "width": w, "height": h,
            "link": link,
            "crop": crop_images,
        })

    def set_logo(self, image, x, y, w, h):
        self.logo = {"path": os.path.basename(image), "x": x, "y": y, "width": w, "height": h}
        self.images.append(image)

    def set_title(self, title):
        self.meta["title"] = title

    def set_producer(self, producer):
        self.meta["producer"] = producer

    def set_creator(self, creator):
        self.meta["creator"] = creator

    def set_creation_date(self, creation_date):
        self.meta["creation_date"] = creation_date

    def output(self):
        if not self.odp_output_filename.endswith(".odp"):
            self.odp_output_filename += ".odp"

        self._prepare_temp_dir()
        self._create_meta_file()
        self._create_manifest_file()
        self._create_content_file()
        self._create_styles_file()

        # Write the mimetype file
        mimetype_path = os.path.join(self.temp_dir, "mimetype")
        with open(mimetype_path, "w") as mimetype_file:
            mimetype_file.write("application/vnd.oasis.opendocument.presentation")

        # Create the zip archive for ODP
        with ZipFile(self.odp_output_filename, "w", ZIP_DEFLATED) as odp_file:
            # Add mimetype as the first file, uncompressed
            with open(mimetype_path, "rb") as mimetype_file:
                odp_file.writestr("mimetype", mimetype_file.read(), compress_type=ZIP_STORED)


            for root, _, files in os.walk(self.temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, self.temp_dir)
                    if arcname != "mimetype":  # Avoid adding the mimetype file again
                        odp_file.write(full_path, arcname)

        # Cleanup temporary files
        shutil.rmtree(self.temp_dir)

    def _prepare_temp_dir(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        # Create directories for required structure
        os.makedirs(os.path.join(self.temp_dir, "Thumbnails"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "Pictures"), exist_ok=True)

        # Copy images to Pictures directory
        for image in self.images:
            shutil.copy(os.path.join(self.input_dir, image), os.path.join(self.temp_dir, "Pictures"))

    def _create_meta_file(self):
        meta_xml = etree.Element(
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}document-meta",
            nsmap={
                "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
                "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
            }
        )

        meta = etree.SubElement(meta_xml, "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}meta")
        etree.SubElement(meta, "{urn:oasis:names:tc:opendocument:xmlns:meta:1.0}title").text = self.meta["title"]
        etree.SubElement(meta, "{urn:oasis:names:tc:opendocument:xmlns:meta:1.0}creator").text = self.meta["creator"]
        etree.SubElement(meta, "{urn:oasis:names:tc:opendocument:xmlns:meta:1.0}creation-date").text = str(self.meta["creation_date"])
        etree.SubElement(meta, "{urn:oasis:names:tc:opendocument:xmlns:meta:1.0}generator").text = self.meta["producer"]

        meta_tree = etree.ElementTree(meta_xml)
        meta_tree.write(os.path.join(self.temp_dir, "meta.xml"), pretty_print=True, xml_declaration=True, encoding="UTF-8")

    def _create_styles_file(self, slide_width="28cm", slide_height="21cm"):
        """
        Generate the styles.xml file with custom page dimensions.

        Parameters:
            slide_width (str): Width of the slides (default is "28cm").
            slide_height (str): Height of the slides (default is "21cm").
        """
        # Create the root element for styles.xml
        styles_xml = etree.Element(
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}document-styles",
            nsmap={
                "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
                "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
                "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
                "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
                "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
            }
        )

        # Add automatic styles for page layout
        automatic_styles = etree.SubElement(styles_xml, "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}automatic-styles")

        # Define the page layout
        page_layout = etree.SubElement(automatic_styles, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "page-layout",
        })
        etree.SubElement(page_layout, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout-properties", {
            "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}page-width": "{}mm".format(str(self.formatting['dimensions']['page_width'])),
            "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}page-height": "{}mm".format(str(self.formatting['dimensions']["page_height"])),
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}print-orientation": "landscape",
        })

        # Define the master page
        master_page = etree.SubElement(styles_xml, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}master-page", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "Default",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout-name": "page-layout",
        })

        # Write styles.xml
        styles_tree = etree.ElementTree(styles_xml)
        styles_tree.write(
            os.path.join(self.temp_dir, "styles.xml"),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def _create_manifest_file(self):
        # Create the root element with namespaces
        manifest_xml = etree.Element(
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}manifest",
            nsmap={
                "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
            }
        )

        # Add the root file entry for the presentation
        etree.SubElement(manifest_xml, "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}file-entry", {
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path": "/",
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}media-type": "application/vnd.oasis.opendocument.presentation",
        })

        # Add file entries for content and metadata files
        etree.SubElement(manifest_xml, "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}file-entry", {
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path": "content.xml",
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}media-type": "text/xml",
        })
        etree.SubElement(manifest_xml, "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}file-entry", {
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path": "meta.xml",
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}media-type": "text/xml",
        })


        # Entry for styles.xml
        etree.SubElement(manifest_xml, "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}file-entry", {
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path": "styles.xml",
            "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}media-type": "text/xml",
        })

        # Add file entries for images in the Pictures directory
        for image in self.images:
            etree.SubElement(manifest_xml, "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}file-entry", {
                "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path": f"Pictures/{os.path.basename(image)}",
                "{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}media-type": "image/png",  # Adjust media type as needed
            })


        # Write the manifest.xml file
        meta_inf_dir = os.path.join(self.temp_dir, "META-INF")
        os.makedirs(meta_inf_dir, exist_ok=True)

        manifest_tree = etree.ElementTree(manifest_xml)
        manifest_tree.write(
            os.path.join(meta_inf_dir, "manifest.xml"),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def _create_content_file(self):
        # Create the root element with namespaces
        content_xml = etree.Element(
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}document-content",
            nsmap={
                "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
                "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
                "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
                "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
                "xlink": "http://www.w3.org/1999/xlink",
                "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
                "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
                "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
            },
            attrib={
                "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}version": "1.3"
            },
        )

        # Add scripts: TODO: this is an empty tag at the moment.
        font_decls = etree.SubElement(content_xml, "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}scripts")

        # Add font-face-decls
        font_decls = etree.SubElement(content_xml, "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}font-face-decls")

        # Add font faces
        font1 = etree.SubElement(font_decls, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-face", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "Liberation Serif",
            "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}font-family": "'Liberation Serif'",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-family-generic": "roman",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-pitch": "variable",
        })

        font2 = etree.SubElement(font_decls, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-face", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "Liberation Sans",
            "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}font-family": "'Liberation Sans'",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-family-generic": "swiss",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}font-pitch": "variable",
        })

        # Add automatic styles
        automatic_styles = etree.SubElement(content_xml, "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}automatic-styles")

        # Define the page layout style
        #page_layout = etree.SubElement(automatic_styles, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout", {
        #    "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "page-layout",
        #})
        #etree.SubElement(page_layout, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout-properties", {
        #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}width": "{}mm".format(str(self.formatting['dimensions']['page_width'])),
        #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}height": "{}mm".format(str(self.formatting['dimensions']["page_height"])),
        #    "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}print-orientation": "landscape",
        #})
        # did not work to specify page size

        # Add a style for slides (drawing pages)
        slide_style = etree.SubElement(automatic_styles, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}style", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "dp1",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}family": "drawing-page",
        })
        etree.SubElement(slide_style, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}drawing-page-properties", {
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}background-size": "border"
        })

        # Add a style for shapes or graphics
        graphic_style = etree.SubElement(automatic_styles, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}style", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "gr1",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}family": "graphic",
        })
        etree.SubElement(graphic_style, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}graphic-properties", {
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}stroke": "none",
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}fill": "solid",
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}fill-color": "#ffffff"
        })

        # Add a style for the slide background
        slide_bg_style = etree.SubElement(automatic_styles, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}style", {
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name": "slide-bg",
            "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}family": "drawing-page",
        })
        etree.SubElement(slide_bg_style, "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}drawing-page-properties", {
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}fill": "solid",
            "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}fill-color": "#ffffff",  # Green background
        })


        # Add presentation body
        body = etree.SubElement(
            content_xml,
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}body"
        )
        presentation = etree.SubElement(
            body,
            "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}presentation"
        )

        # Define the master page
        #master_page = etree.SubElement(presentation, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}master-page", {
        #    "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}name": "Default",
        #    "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}page-layout-name": "page-layout",
        #})

        # add font-declarations. TODO: needs to be properly handled!

        # Add slides to the presentation
        for i, page in enumerate(self.pages):
            # TODO: use the correct background color from page["background_color"]
            slide = etree.SubElement(presentation, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}page", {
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}name": f"Slide {i + 1}",
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}style-name": "slide-bg",  # Reference the background style
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}master-page-name": "Default",
            })
            #if page["background_color"]:
            #    slide.set("{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}background-color", page["background_color"])

            for element in page["elements"]:
                self._add_element_to_slide(slide, element)

        # Write the content.xml file
        content_tree = etree.ElementTree(content_xml)
        content_tree.write(
            os.path.join(self.temp_dir, "content.xml"),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )


    def _add_element(self, element_type, element_data):
        if self.pages:
            element = {"type": element_type, **element_data}
            self.pages[-1]["elements"].append(element)

    def _add_element_to_slide(self, slide, element):
        if element["type"] == "textbox":
            # Create a frame to hold the text box
            frame = etree.SubElement(slide, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}frame", {
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}name": element.get("name", "Text Frame"),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}x": "{}mm".format(str(element["x"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}y": "{}mm".format(str(element["y"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}width": "{}mm".format(str(element["width"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}height": "{}mm".format(str(element["height"])),
            })

            # Create the text box inside the frame
            text_box = etree.SubElement(frame, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}text-box")
            paragraph = etree.SubElement(text_box, "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p")
            paragraph.text = element["content"]

        elif element["type"] == "image":
            # Create a frame to position the image
            frame = etree.SubElement(slide, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}frame", {
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}name": element.get("name", "Image Frame"),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}x": "{}mm".format(str(element["x"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}y": "{}mm".format(str(element["y"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}width": "{}mm".format(str(element["width"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}height": "{}mm".format(str(element["height"])),
            })

            # Add the image inside the frame
            etree.SubElement(frame, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}image", {
                "{http://www.w3.org/1999/xlink}href": f"Pictures/{element['path']}",
                "{http://www.w3.org/1999/xlink}type": "simple",
                "{http://www.w3.org/1999/xlink}show": "embed",
                "{http://www.w3.org/1999/xlink}actuate": "onLoad",
            })

        elif element["type"] == "l4_box":
            # Create a frame to hold the text box
            frame = etree.SubElement(slide, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}frame", {
                "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}name": element.get("name", "Text Frame"),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}x": "{}mm".format(str(element["x"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}y": "{}mm".format(str(element["y"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}width": "{}mm".format(str(element["width"])),
                "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}height": "{}mm".format(str(element["height"])),
            })

            # Create the text box inside the frame
            text_box = etree.SubElement(frame, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}text-box")
            paragraph = etree.SubElement(text_box, "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p")
            paragraph.text = element["content"]

            # Rounded rectangle for l4_box
            #frame = etree.SubElement(slide, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}frame", {
            #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}x": str(element["x"]),
            #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}y": str(element["y"]),
            #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}width": str(element["width"]),
            #    "{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}height": str(element["height"]),
            #})
            #shape = etree.SubElement(frame, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}custom-shape", {})
            #etree.SubElement(shape, "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}enhanced-geometry", {
            #    "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}type": "rectangle",
            #    "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}corner-radius": "0.2in",  # Example radius
            #})
            #paragraph = etree.SubElement(shape, "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p", {
            #    "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}align": element["align"]
            #})
            #paragraph.text = element["content"]


def dec_to_hex_color(color, alpha=1.0):
  a = 'ff'
  if type(color) == str:
    if color == 'white':
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



