# point-in-triangle

[![stable](http://badges.github.io/stability-badges/dist/stable.svg)](http://github.com/badges/stability-badges)

Test whether a point is inside a triangle, using barycentric coordinates and [this algorithm from BlackPawn](http://www.blackpawn.com/texts/pointinpoly/).

```js
var inside = require('point-in-triangle')

var triangle = [ [25, 10], [100, 250], [40, 40] ]
console.log(inside([25, 25], triangle))
```

You may also be interested in:

- [triangle-circle-collision](https://www.npmjs.org/package/triangle-circle-collision)
- [line-circle-collision](https://www.npmjs.org/package/line-circle-collision)
- [point-circle-collision](https://www.npmjs.org/package/point-circle-collision)
- [is-clockwise](https://www.npmjs.org/package/is-clockwise)

## Usage

[![NPM](https://nodei.co/npm/point-in-triangle.png)](https://nodei.co/npm/point-in-triangle/)

#### `inside(point, triangle)`

Returns true if the point `[x, y]` is inside the triangle `[ [x1,y1], [x2,y2], [x3,y3] ]`, false otherwise.

## License

MIT, see [LICENSE.md](http://github.com/mattdesl/point-in-triangle/blob/master/LICENSE.md) for details.
