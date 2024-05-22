from fpdf import FPDF

def __init__(self, formatting):
  self.pdf = FPDF(orientation = 'P', unit = 'mm', format = (formatting['dimensions']['page_width'], formatting['dimensions']['page_height']))
  self.pdf.set_font('Helvetica', '', formatting['dimensions']['font_size_standard'])
  if 'fonts' in formatting:
    print(formatting['fonts'])
    if formatting['fonts']['font_file_standard']:
      fname = formatting['fonts']['font_file_standard']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_standard', '', fname)
      self.pdf.set_font('font_standard', '', formatting['dimensions']['font_size_standard'])
    if formatting['fonts']['font_file_standard_italic']:
      fname = formatting['fonts']['font_file_standard_italic']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_standard', 'i', fname)
    if formatting['fonts']['font_file_standard_bold']:
      fname = formatting['fonts']['font_file_standard_bold']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_standard', 'b', fname)
    if formatting['fonts']['font_file_standard_bolditalic']:
      fname = formatting['fonts']['font_file_standard_bolditalic']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_standard', 'bi', fname)
    if formatting['fonts']['font_file_footer']:
      fname = formatting['fonts']['font_file_footer']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_footer', '', fname)
    if formatting['fonts']['font_file_title']:
      fname = formatting['fonts']['font_file_title']
      if os.path.exists(os.path.join(script_home, fname)):
        fname = os.path.join(script_home, fname)
      self.pdf.add_font('font_title', '', fname)
  self.pdf.set_text_color(0,0,0)
  #self.pdf.set_image_filter("FlatDecode")
  self.pdf.oversized_images = "DOWNSCALE"
  print('{}: self.pdf.oversized_images_ratio {}'.format(md_file_stripped, self.pdf.oversized_images_ratio))


