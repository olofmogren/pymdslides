# Test doc

---
layout: center
packed_images: false
crop_images: false
footer: Nice footer about the author and event.
---

* layout: center
* Three images
* And the final bullet

![Neurons in space](neurons-in-space-explosion-detailed.jpg)
![Image alt text](testing_image.jpg)
![Neurons in space](neurons-in-space-explosion-detailed.jpg)

# Image left

---
layout: image_left_half
packed_images: true
---

* layout: image_left_half
* packed_images: true
* And the final bullet

![Mon Amie](monamie.jpg)
![Image alt text](testing_image.jpg)

# Image left small

---
layout: image_left_small
packed_images: true
crop_images: true
---

* layout: image_left_small
* Another bullet
* And the final bullet

![Image alt text](testing_image.jpg)

# Image right

---
layout: image_right_half
packed_images: true
---

* One bullet
* Another bullet
* And the final bullet

![Image alt text](testing_image.jpg)

# Image right small

---
layout: image_right_small
---

* One bullet
* Another bullet
* And the final bullet

![Image alt text](testing_image.jpg)

# Center again, not cropping

---
layout: center
crop_images: false
---

* One bullet
* Another bullet
* And the final bullet

![Image alt text](testing_image.jpg)


# Image center

---
layout: image_center
crop_images: true
---

* Default cropping
* Another bullet
* And the final bullet

![Image alt text](testing_image.jpg)

# Image fill

---
layout: image_fill
text_color:
  - 0
  - 0
  - 140
---

* The image_fill layout puts image as background, with or without text.
* Another bullet: $a = \frac{b}{c}$
* And the final bullet

![Image alt text](testing_image.jpg)

# Black slide

---
background_color:
  - 0
  - 0
  - 0
text_color:
  - 255
  - 255
  - 255
---
* Only bullet

# Latex and formatting

---
background_color:
- 255
- 255
- 255
layout: center
text_color:
- 0
- 0
- 0
---

A bit *of italic*

$a = \frac{b}{c}$

And **a bold thing**, too.

Testing [linking \(mogren.one\)](http://mogren.one/), too.

A text, following with a $\frac{formula}{divisor}$

# Some more strangeness

---
background_color:
- 255
- 255
- 255
layout: center
text_color:
- 0
- 0
- 140
---

$a = \left(\frac{\frac{\sum_i^N X_i^2}{y}}{c}\right)$
* [Link to page 1](#Test doc)

# Another formula

* A small one $a = b * c$ this time.

--------------------------

* Another bullet

# Two column layout

---
columns: 2
layout: center
---

* First bullet
* Second bullet

--------------------------

* Third bullet
* Fourth bullet

# Three column layout

---
columns: 3
crop_images: false
layout: center
---

![Neurons in space](neurons-in-space-explosion-detailed.jpg)
![Image alt text](testing_image.jpg)
![Neurons in space](neurons-in-space-explosion-detailed.jpg)

* First bullet
* Second bullet

--------------------------

* Third bullet
* Fourth bullet

--------------------------

* Fifth bullet
* Sixth bullet

# Thank you 

---
layout: image_right_half
---

# Level four headlines
## create boxes

---
layout: image_right_half
---
![Image alt text](testing_image.jpg)

&nbsp;

#### 

Writing a lot of cool things in a box.

Maths: $\mathbf{x} = \sum_{i=0}^N x_i$

#### 

We can fill a page with boxes.

#### Really fill.

# And a page can overflow

* But
* Then
* The
* OVerflow
* Will
* Not
* Fit
* On
* The
* Page
* Overflow line 1
* Overflow line 2
* Overflow line 3
* Overflow line 4

# Images side-by-side

---
layout: image_fill
text_color:
- 255
- 100
- 100
---

![](testing_image.jpg)
![](neurons-in-space-explosion-detailed.jpg)

&nbsp;

#  

---
layout: center
---

&nbsp;
[Thank you!](#Latex and formatting)

