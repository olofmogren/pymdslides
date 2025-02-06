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

#template_preface = '''<?xml version="1.0" encoding="UTF-8"?>
template_preface = '''<?xml version="1.0"?>
<office:document-content xmlns:anim="urn:oasis:names:tc:opendocument:xmlns:animation:1.0" xmlns:smil="urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0" xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" xmlns:css3t="http://www.w3.org/TR/css3-text/" xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xforms="http://www.w3.org/2002/xforms" xmlns:dom="http://www.w3.org/2001/xml-events" xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0" xmlns:math="http://www.w3.org/1998/Math/MathML" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:ooo="http://openoffice.org/2004/office" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:ooow="http://openoffice.org/2004/writer" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:drawooo="http://openoffice.org/2010/draw" xmlns:oooc="http://openoffice.org/2004/calc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:calcext="urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:tableooo="http://openoffice.org/2009/table" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" xmlns:rpt="http://openoffice.org/2005/report" xmlns:formx="urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:officeooo="http://openoffice.org/2009/office" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0" office:version="1.3">
  <office:scripts/>
  <office:font-face-decls>
    <style:font-face style:name="DejaVu Sans" svg:font-family="'DejaVu Sans'" style:font-family-generic="system" style:font-pitch="variable"/>
    <style:font-face style:name="Liberation Sans" svg:font-family="'Liberation Sans'" style:font-family-generic="roman" style:font-pitch="variable"/>
    <style:font-face style:name="Liberation Serif" svg:font-family="'Liberation Serif'" style:font-family-generic="roman" style:font-pitch="variable"/>
    <style:font-face style:name="Noto Sans" svg:font-family="'Noto Sans'" style:font-family-generic="roman" style:font-pitch="variable"/>
    <style:font-face style:name="Noto Sans CJK SC" svg:font-family="'Noto Sans CJK SC'" style:font-family-generic="system" style:font-pitch="variable"/>
    <style:font-face style:name="Noto Sans Devanagari" svg:font-family="'Noto Sans Devanagari'" style:font-family-generic="system" style:font-pitch="variable"/>
    <style:font-face style:name="Noto Sans1" svg:font-family="'Noto Sans'" style:font-family-generic="system" style:font-pitch="variable"/>
  </office:font-face-decls>
  <office:automatic-styles>
    <style:style style:name="dp1" style:family="drawing-page">
      <style:drawing-page-properties presentation:background-visible="true" presentation:background-objects-visible="true" presentation:display-footer="true" presentation:display-page-number="false" presentation:display-date-time="true"/>
    </style:style>
    <style:style style:name="dp2" style:family="drawing-page">
      <style:drawing-page-properties presentation:display-header="true" presentation:display-footer="true" presentation:display-page-number="false" presentation:display-date-time="true"/>
    </style:style>
    <style:style style:name="gr1" style:family="graphic">
      <style:graphic-properties style:protect="size" loext:decorative="false"/>
    </style:style>
    <style:style style:name="gr2" style:family="graphic" style:parent-style-name="Object_20_with_20_no_20_fill_20_and_20_no_20_line">
      <style:graphic-properties draw:textarea-horizontal-align="center" draw:textarea-vertical-align="middle" draw:color-mode="standard" draw:luminance="0%" draw:contrast="0%" draw:gamma="100%" draw:red="0%" draw:green="0%" draw:blue="0%" fo:clip="rect(0cm, 0cm, 0cm, 0cm)" draw:image-opacity="100%" style:mirror="none" loext:decorative="false"/>
    </style:style>
    <style:style style:name="pr1" style:family="presentation" style:parent-style-name="Default-title">
      <style:graphic-properties fo:min-height="2.629cm" loext:decorative="false"/>
      <style:paragraph-properties style:writing-mode="lr-tb"/>
    </style:style>
    <style:style style:name="pr2" style:family="presentation" style:parent-style-name="Default-subtitle">
      <style:graphic-properties draw:fill-color="#ffffff" fo:min-height="9.134cm" loext:decorative="false"/>
      <style:paragraph-properties style:writing-mode="lr-tb"/>
    </style:style>
    <style:style style:name="pr3" style:family="presentation" style:parent-style-name="Default-notes">
      <style:graphic-properties draw:fill-color="#ffffff" fo:min-height="13.364cm" loext:decorative="false"/>
      <style:paragraph-properties style:writing-mode="lr-tb"/>
    </style:style>
    <style:style style:name="pr4" style:family="presentation" style:parent-style-name="Default-outline1">
      <style:graphic-properties fo:min-height="8.884cm" loext:decorative="false"/>
      <style:paragraph-properties style:writing-mode="lr-tb"/>
    </style:style>
    <style:style style:name="P1" style:family="paragraph">
      <loext:graphic-properties draw:fill-color="#ffffff"/>
    </style:style>
    <style:style style:name="P2" style:family="paragraph">
      <style:paragraph-properties fo:margin-top="0.5cm" fo:margin-bottom="0cm"/>
    </style:style>
    <style:style style:name="P3" style:family="paragraph">
      <style:paragraph-properties fo:text-align="center"/>
    </style:style>
    <text:list-style style:name="L1">
      <text:list-level-style-bullet text:level="1" text:bullet-char="●">
        <style:list-level-properties text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="2" text:bullet-char="●">
        <style:list-level-properties text:space-before="0.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="3" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="4" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="5" text:bullet-char="●">
        <style:list-level-properties text:space-before="2.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="6" text:bullet-char="●">
        <style:list-level-properties text:space-before="3cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="7" text:bullet-char="●">
        <style:list-level-properties text:space-before="3.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="8" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="9" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="10" text:bullet-char="●">
        <style:list-level-properties text:space-before="5.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
    </text:list-style>
    <text:list-style style:name="L2">
      <text:list-level-style-bullet text:level="1" text:bullet-char="●">
        <style:list-level-properties text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="2" text:bullet-char="●">
        <style:list-level-properties text:space-before="0.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="3" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="4" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="5" text:bullet-char="●">
        <style:list-level-properties text:space-before="2.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="6" text:bullet-char="●">
        <style:list-level-properties text:space-before="3cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="7" text:bullet-char="●">
        <style:list-level-properties text:space-before="3.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="8" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="9" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="10" text:bullet-char="●">
        <style:list-level-properties text:space-before="5.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
    </text:list-style>
    <text:list-style style:name="L3">
      <text:list-level-style-bullet text:level="1" text:bullet-char="●">
        <style:list-level-properties text:space-before="0.3cm" text:min-label-width="0.9cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="2" text:bullet-char="–">
        <style:list-level-properties text:space-before="1.5cm" text:min-label-width="0.9cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="75%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="3" text:bullet-char="●">
        <style:list-level-properties text:space-before="2.8cm" text:min-label-width="0.8cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="4" text:bullet-char="–">
        <style:list-level-properties text:space-before="4.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="75%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="5" text:bullet-char="●">
        <style:list-level-properties text:space-before="5.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="6" text:bullet-char="●">
        <style:list-level-properties text:space-before="6.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="7" text:bullet-char="●">
        <style:list-level-properties text:space-before="7.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="8" text:bullet-char="●">
        <style:list-level-properties text:space-before="9cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="9" text:bullet-char="●">
        <style:list-level-properties text:space-before="10.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="10" text:bullet-char="●">
        <style:list-level-properties text:space-before="11.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
    </text:list-style>
    <text:list-style style:name="L4">
      <text:list-level-style-bullet text:level="1" text:bullet-char="●">
        <style:list-level-properties text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="2" text:bullet-char="●">
        <style:list-level-properties text:space-before="0.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="3" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="4" text:bullet-char="●">
        <style:list-level-properties text:space-before="1.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="5" text:bullet-char="●">
        <style:list-level-properties text:space-before="2.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="6" text:bullet-char="●">
        <style:list-level-properties text:space-before="3cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="7" text:bullet-char="●">
        <style:list-level-properties text:space-before="3.6cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="8" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.2cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="9" text:bullet-char="●">
        <style:list-level-properties text:space-before="4.8cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
      <text:list-level-style-bullet text:level="10" text:bullet-char="●">
        <style:list-level-properties text:space-before="5.4cm" text:min-label-width="0.6cm"/>
        <style:text-properties fo:font-family="OpenSymbol" style:use-window-font-color="true" fo:font-size="45%"/>
      </text:list-level-style-bullet>
    </text:list-style>
  </office:automatic-styles>
  <office:body>
'''
template_postface = '''
  </office:body>
</office:document-content>
'''
template_pages='''
    <office:presentation>
      <draw:page draw:name="page1" draw:style-name="dp1" draw:master-page-name="Default" presentation:presentation-page-layout-name="AL1T0">
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Main presentation title OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <draw:frame presentation:style-name="pr2" draw:text-style-name="P1" draw:layer="layout" svg:width="25.199cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="subtitle">
          <draw:text-box>
            <text:p>First slide text, OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <presentation:notes draw:style-name="dp2">
          <draw:page-thumbnail draw:style-name="gr1" draw:layer="layout" svg:width="19.798cm" svg:height="11.136cm" svg:x="0.6cm" svg:y="2.257cm" draw:page-number="1" presentation:class="page"/>
          <draw:frame presentation:style-name="pr3" draw:text-style-name="P1" draw:layer="layout" svg:width="16.799cm" svg:height="13.364cm" svg:x="2.1cm" svg:y="14.107cm" presentation:class="notes" presentation:placeholder="true">
            <draw:text-box/>
          </draw:frame>
        </presentation:notes>
      </draw:page>
      <draw:page draw:name="page2" draw:style-name="dp1" draw:master-page-name="Default" presentation:presentation-page-layout-name="AL2T1">
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Second slide title OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <draw:frame presentation:style-name="pr4" draw:layer="layout" svg:width="25.199cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="outline">
          <draw:text-box>
            <text:list text:style-name="L3">
              <text:list-item>
                <text:p>Second slide, first bullet, OLOF</text:p>
              </text:list-item>
              <text:list-item>
                <text:p text:style-name="P2">Second slide, second bullet, OLOF</text:p>
              </text:list-item>
            </text:list>
          </draw:text-box>
        </draw:frame>
        <presentation:notes draw:style-name="dp2">
          <draw:page-thumbnail draw:style-name="gr1" draw:layer="layout" svg:width="19.798cm" svg:height="11.136cm" svg:x="0.6cm" svg:y="2.257cm" draw:page-number="2" presentation:class="page"/>
          <draw:frame presentation:style-name="pr3" draw:text-style-name="P1" draw:layer="layout" svg:width="16.799cm" svg:height="13.364cm" svg:x="2.1cm" svg:y="14.107cm" presentation:class="notes" presentation:placeholder="true">
            <draw:text-box/>
          </draw:frame>
        </presentation:notes>
      </draw:page>
      <draw:page draw:name="page3" draw:style-name="dp1" draw:master-page-name="Default" presentation:presentation-page-layout-name="AL2T1">
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Third slide OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <draw:frame presentation:style-name="pr4" draw:layer="layout" svg:width="25.199cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="outline">
          <draw:text-box>
            <text:list text:style-name="L3">
              <text:list-item>
                <text:p>Third slide, first bullet OLOF</text:p>
              </text:list-item>
              <text:list-item>
                <text:p>Third slide, second bullet OLOF</text:p>
              </text:list-item>
            </text:list>
          </draw:text-box>
        </draw:frame>
        <presentation:notes draw:style-name="dp2">
          <draw:page-thumbnail draw:style-name="gr1" draw:layer="layout" svg:width="19.798cm" svg:height="11.136cm" svg:x="0.6cm" svg:y="2.257cm" draw:page-number="3" presentation:class="page"/>
          <draw:frame presentation:style-name="pr3" draw:text-style-name="P1" draw:layer="layout" svg:width="16.799cm" svg:height="13.364cm" svg:x="2.1cm" svg:y="14.107cm" presentation:class="notes" presentation:placeholder="true">
            <draw:text-box/>
          </draw:frame>
        </presentation:notes>
      </draw:page>
      <draw:page draw:name="page4" draw:style-name="dp1" draw:master-page-name="Default" presentation:presentation-page-layout-name="AL2T1">
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Fourth slide OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <draw:frame presentation:style-name="pr4" draw:layer="layout" svg:width="12.53cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="outline" presentation:user-transformed="true">
          <draw:text-box>
            <text:list text:style-name="L3">
              <text:list-item>
                <text:p>Fourth slide first bullet OLOF</text:p>
              </text:list-item>
            </text:list>
          </draw:text-box>
        </draw:frame>
        <draw:frame draw:style-name="gr2" draw:text-style-name="P3" draw:layer="layout" svg:width="7.796cm" svg:height="7.796cm" svg:x="16.964cm" svg:y="4.981cm">
          <draw:image xlink:href="Pictures/10000001000003EC000003EC334A6A99.png" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad" draw:mime-type="image/png">
            <text:p/>
          </draw:image>
        </draw:frame>
        <presentation:notes draw:style-name="dp2">
          <draw:page-thumbnail draw:style-name="gr1" draw:layer="layout" svg:width="19.798cm" svg:height="11.136cm" svg:x="0.6cm" svg:y="2.257cm" draw:page-number="4" presentation:class="page"/>
          <draw:frame presentation:style-name="pr3" draw:text-style-name="P1" draw:layer="layout" svg:width="16.799cm" svg:height="13.364cm" svg:x="2.1cm" svg:y="14.107cm" presentation:class="notes" presentation:placeholder="true">
            <draw:text-box/>
          </draw:frame>
        </presentation:notes>
      </draw:page>
      <presentation:settings presentation:mouse-visible="false"/>
    </office:presentation>
'''

class backend_odp:
  def __init__(self, input_file, formatting, script_home, overwrite_images=False):
    # (title_font_color='black', subtitle_font_color='#666666', background_image='', background_color='white', grad_start_color='', grad_end_color='', grad_angle_deg=0, grad_draw_style='linear', show_date=False, date_font_color='#666666', footer='', footer_font_color='#666666', show_page_numbers=True, page_number_font_color='#666666')

    self.html_output_filename = os.path.join(os.path.splitext(input_file)[0]+'-odp','content.xml')
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
      
    #self.et_root = ET.fromstring(template_preface+template_postface)
    #q = self.et_root.xpath('/office:document-content/office:body')
    #print(q)
    #self.et_body = q[0]
    #self.et_presentation = ET.Element(ET.QName("urn:oasis:names:tc:opendocument:xmlns:office:1.0", 'presentation'))
    #self.et_body.append(self.et_presentation)

    self.pages = []
    self.current_page = None

    #mathjax0 = ET.Element('script')
    #mathjax0.text = '''
#MathJax = {
#  tex: {
#    inlineMath: [['$', '$']]
#  },
#  svg: {
#    fontCache: 'global'
#  }
#};
#'''
    #self.head.append(mathjax0)
    #mathjax2 = ET.Element('script')
    #mathjax2.set('id', 'MathJax-script')
    #mathjax2.set('async', 'true')
    #mathjax2.set('src', mathjax_url)
    #mathjax2.text = ' '
    #self.head.append(mathjax2)

    self.current_page_div = None

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
    result = '{:.3f}cqw'.format(32*font_size/self.page_width)
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
    page_preamble='''
      <draw:page draw:name="PAGE_NAME" draw:style-name="dp1" draw:master-page-name="Default" presentation:presentation-page-layout-name="AL1T0">
    '''
    title_preamble='''
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Main presentation title OLOF</text:p>
    '''
    title_postamble='''
          </draw:text-box>
        </draw:frame>
    '''
    text_preamble='''
        <draw:frame presentation:style-name="pr2" draw:text-style-name="P1" draw:layer="layout" svg:width="25.199cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="subtitle">
          <draw:text-box>
            <text:p>First slide text, OLOF</text:p>
    '''
    text_postamble='''
          </draw:text-box>
        </draw:frame>
    '''
    page_postamble='''
        <presentation:notes draw:style-name="dp2">
          <draw:page-thumbnail draw:style-name="gr1" draw:layer="layout" svg:width="19.798cm" svg:height="11.136cm" svg:x="0.6cm" svg:y="2.257cm" draw:page-number="1" presentation:class="page"/>
          <draw:frame presentation:style-name="pr3" draw:text-style-name="P1" draw:layer="layout" svg:width="16.799cm" svg:height="13.364cm" svg:x="2.1cm" svg:y="14.107cm" presentation:class="notes" presentation:placeholder="true">
            <draw:text-box/>
          </draw:frame>
        </presentation:notes>
      </draw:page>
'''
    # onmouseup (onclick fires also with onmousedown, resulting in two events) on previous page will take us to this one
    self.override_font = {}
    self.override_font_size = {} # override fonts are per page.
    self.pages_count += 1

    self.current_page_div = ET.Element(ET.QName('urn:oasis:names:tc:opendocument:xmlns:drawing:1.0', 'page'))
    self.current_page_div.set('draw:name', 'page{}'.format(self.pages_count))
    self.current_page_div.set('draw:style-name', 'dp1')
    self.current_page_div.set('draw:master-page-name', 'Default')
    self.current_page_div.set('presentation:presentation-page-layout-name', 'AL1T0')
    self.et_presentation.append(self.current_page_div)

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

  def textbox(self, lines, x, y, w, h, headlines, h_level=None, align='left', markdown_format=True, text_color=None):
    '''
        <draw:frame presentation:style-name="pr1" draw:layer="layout" svg:width="25.199cm" svg:height="2.629cm" svg:x="1.4cm" svg:y="0.628cm" presentation:class="title">
          <draw:text-box>
            <text:p>Main presentation title OLOF</text:p>
          </draw:text-box>
        </draw:frame>
        <draw:frame presentation:style-name="pr2" draw:text-style-name="P1" draw:layer="layout" svg:width="25.199cm" svg:height="9.134cm" svg:x="1.4cm" svg:y="3.685cm" presentation:class="subtitle">
          <draw:text-box>
            <text:p>First slide text, OLOF</text:p>
          </draw:text-box>
        </draw:frame>
'''

    #self.current_page_div.set('draw:style-name', 'pr1')
    #self.current_page_div.set('draw:layer', 'layout')
    #self.current_page_div.set('svg:width', self.width)
    #self.current_page_div.set('svg:height', self.height)
    #self.current_page_div.set('svg:x', '1.4cm') # TODO magic number
    #self.current_page_div.set('svg:y', '0.628cm')
    #self.current_page_div.set('presentation:class', 'title')

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
    style = 'position: absolute; left: {}; top: {}; width: {}; height: {}; text-align: {}; overflow: hidden; padding-top: 0; /* text-wrap: nowrap; */ color: {}; '.format(self.html_x(x), self.html_y(y), self.html_x(w), self.html_y(h), align, text_color)
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


  def l4_box(self, lines, x, y, w, h, headlines, align='left', border_color=[0,0,0], border_opacity=0.75, background_color=[255,255,255], background_opacity=0.75, markdown_format=True, text_color=None):
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
    style = 'left: {}; top: {}; width: {}; text-align: {}; z-index: 4; margin: 0; padding: -1cqw .5cqw .5cqw .5cqw; background-color: {}; border: 1px {} solid; color: {}; '.format(self.html_x(x), self.html_y(y), self.html_x(w), align, bgcolor, bcolor, text_color)
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
          page_no = int(headlines.index(href[1:].strip()))+1
          print('found local link', page_no)
          child.set('href', '#')
          child.set('onclick', 'localPageLink("page-{}", event); return false;'.format(page_no))
          child.set('onmouseup', 'stopProp(event);')
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
      if is_vector_format(current_filename) and not current_ext in treat_as_raster_images:
        command_is_chosen = False
        #print(current_ext)
        if current_ext == 'pdf' and shutil.which('pdf2svg') is not None:
          target_extension = 'svg'
          target_filename = target_filename_no_ext+'.'+target_extension
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
          target_extension = 'png'
          target_filename = target_filename_no_ext+'.'+target_extension
          command = 'convert -density 150 '+input_file+'['+page_no+'] '+target_filename
          current_ext = target_extension
          command_is_chosen = True
        print('converting image:',command)
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
              command = 'convert -define webp:lossless=false '+current_filename+' '+target_filename
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
      loading_event_element.set('onload', 'gotoHash()')
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
