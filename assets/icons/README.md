Icons
=====

Usage (from React code)
-----------------------

Import icons like this:

```jsx
import React from 'react'
import IconAddc from '../../../icons/addc.svg'

function MyComponent () {
  return <IconAddc />
}
```

Design (of SVGs)
----------------

Not _all_ SVGs need to be icons. But for the ones that do, let's be uniform.

If you break these rules, you must explain why:

### Height=32 (unitless)

Every SVG has width=32, height=32.

They are square because we show icons in grids: both horizontally (on a
toolbar) and vertically (in a menu).

The number is 32 because it leads to small file sizes at height=16px.

### Snap points to even-numbered gridlines (2, 4, 6, ...)

We typically render icons with height=16px. The top-left pixel on the user's
view of the icon spans (0, 0) to (2, 2) in SVG coordinates. So odd numbers in
SVG coordinates lie _in between_ monitor pixels.

A square with x=15, y=15, w=2, h=2 can appear blurry, because its corners are
"in between" the nearest pixel corners, which are at (14, 14) and (16, 16).
Between-pixel lines are "anti-aliased": they appear blurry and discolored.

In this example, prefer x=14, y=14, w=4, h=4. This aligns to the user's pixel
grid, so the icon is sharp and the user sees exactly what you designed. (If you
_want_ the blurry discoloration, align to the pixel grid and then choose a
low-contrast color. That way, all users see the same results.)

If you don't want to double the width of your square, you may instead
"un-center" your icon to snap it to the grid: use x=14, y=14, w=2, h=2.

(On a Retina display, (15, 15) is sharp. Most users don't have one.)

### Position icons consistently

We display up fonts next to each other: either horizontally
(on a toolbar), or vertically (in a menu).

Horizontally: the "body" of an icon should be centered around x=16. If this
would make break the rule about even-numbered points, then center around x=15.

Vertically: the "body" of an icon should lie between y=8 and y=24.

Full-size icons span from the bottom of text's descenders to the top of its
ascenders. But many typical icons -- e.g., a "plus" icon -- appear inline with
text. They should respect the text's baseline and X height. In our case,
keeping the 16-unit grid in mind, the "body" is between y=8 and y=24.

[Roboto Regular measurements](https://github.com/googlefonts/roboto/blob/master/src/v2/Roboto-Regular.ufo/fontinfo.plist):

|Measurement|Roboto (h=2048)|% from bottom|Y on 32-unit SVG grid|
|-----------|---------------|-------------|---------------------|
|Descent    |512            |25%          |24                   |
|Cap Height |1456 (plus 512)|96.09375%    |1.25                 |
|X Height   |1082 (plus 512)|77.83203125% |7.09375              |
|Ascent     |1692 (in `$`)  |107.6171875% |-2.4375 (not visible)|

### Don't use `stroke`

It's too hard to align stroke to the pixel grid.

### Colors are ignored

We set colors in CSS using the parent's `color` property.

If you want an SVG with colors, don't place it in this folder. This folder is
only for (monochrome) icons.
