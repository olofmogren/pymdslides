# pymdslides

Script to generate PDF slides from markdown input. Can be configured with custom fonts and has a number of built in layouts. Supports Latex formulas via matplotlib. pymdslides is built around pyfpdf. For other dependencies, look at dependencies.txt.

Level 1 headlines generates a new page. Each document can have a configuration inside a yaml section, and each page can have one specific configuration which is specified insida a yaml section after the headline.

See example documents and default_config.yaml for guidance on usage. The configuration should be put in a file called config.yaml in the same directory as pymdslides.py to be effective.

## Possible configuration

The config file, and the document preample, and each section preamble can all take the following commands. Some of them are only document-wide (such as the geometry, dimensions, and fonts) and those can only be specified in preamble or in the config file.

### Configuration allowed everywhere:

* layout: center|image_center|image_left_half|image_left_small|image_right_half|image_right_small|image_fill
* crop_images: true|false
* packed_images: true|false
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
* tiny_footer: Made with PYMDSLIDES
* tiny_footer_color:
  - 128
  - 128
  - 128
  -- colors are coded with RGB, 0-255.
* logo_path: logo_path.png
* columns: integer_value, the number of columns for content

### Document-wide configuration

* dimensions:
    - em: 18
    - em_title: 26
    - font_size_footer: 12
    - font_size_standard: 34
    - font_size_subtitle: 40
    - font_size_title: 72
    - internal_margin: 10
    - margin_tiny_footer: 4
    - page_height: 270
    - page_margins:
        - x0: 30
        - x1: 30
        - y0: 40
        - y1: 40
    - page_width: 480
    - pixel_per_mm: 0.15
      -- colors are coded with RGB, 0-255.
    - tiny_footer_em: 6

## Why another tool

Because it's fun. And because it helps me make slides in somewhat clean markdown that looks the way I need them to. **Why not Beamer with Markdown?** - Because, even though it was easy to create clean Markdown files for simple presentations, when you wanted images or other layout, the Markdown is soon cluttered with layout formatting, and sections of Latex syntax.
