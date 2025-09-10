# pymdslides

Script to generate slides in html from markdown input. Can be configured with custom fonts and has a number of built in layouts. Supports Latex formulas via mathjax or matplotlib. pymdslides is built with lxml as backend. For other dependencies, look at dependencies.txt. The option to output pdf using a pyfpdf backend exists but is not actively maintained.

Level 1 headlines generates a new page. Each document can have a configuration inside a yaml section, and each page can have one specific configuration which is specified insida a yaml section after the headline.

See example documents and default_config.yaml for guidance on usage. The configuration should be put in a file called config.yaml in the same directory as pymdslides.py to be effective.

## Possible configuration

The config file, and the document preample, and each section preamble can all take the following commands. Some of them are only document-wide (such as the geometry, dimensions, and fonts) and those can only be specified in preamble or in the config file.

### Configuration allowed everywhere:

* layout: **image_center**|image_left_half|image_left_small|image_right_half|image_right_small|image_fill
* text_align: **left**|center
* title_align: **left**|center
* page_numbering: true|**false**
* title_vertical_center: true|**false**
* text_vertical_align: **top**|center|bottom
* crop_images: **true**|false
* packed_images: **true**|false
* text_color:
    - 0
    - 0
    - 0
    -- colors are coded with RGB, 0-255.
* background_color:
    - 255
    - 255
    - 255
    -- colors are coded with RGB, 0-255.
* background_image: path_to_background_image_file.png
* footer: Made with PYMDSLIDES
* footer_color:
    - 128
    - 128
    - 128
    -- colors are coded with RGB, 0-255.
* logo_path: logo_path.png
* columns: integer_value, the number of columns for content
* incremental_bullets: true|**false**
* l4_box_fill_color:
    - 230
    - 240
    - 255
    -- colors are coded with RGB, 0-255.
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
        - x0: 30
        - x1: 30
        - y0: 40
        - y1: 40
    - page_width: 480
    - pixel_per_mm: 0.15
    - footer_em: 6

### Colors

All colors can also take color shorthands in place of the RGB list mentioned above:

* white|grey|black|orange|red|green|blue|yellow|darkred|darkgreen|darkblue

Also supported is html hex syntax: "#ffffff" (quotes required; forgetting them leads to cryptic error message).

## Usage

* --overwrite-images
* --raster_images
* --pdf currently unsupported

## Dependencies

* You will want the convert tool from Imagemagick
* For eps support with html output: svg2eps in the geg package (without it, eps images will be converted to png)
* For pdf support with html output: svg2eps in the pdf2svg package (without it, pdf pages will be converted to png)
* For animated gifs etc with html output, you should install the webp package.

## Why another tool

Because it's fun. And because it helps me make slides in somewhat clean markdown that looks the way I need them to. **Why not Beamer with Markdown?** - Because, even though it was easy to create clean Markdown files for simple presentations, when you wanted images or other layout, the Markdown is soon cluttered with layout formatting, and sections of Latex syntax.
