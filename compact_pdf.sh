#!/bin/bash

gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/default -dQUIET -dDetectDuplicateImages -dCompressFonts=true -r150 -o $1-compact.pdf $1

