region
======

A helper to work with rectangular regions in the DOM

## Install

```sh
$ npm install region --save
```

## Usage

```js
var Region = require('region')

var region = Region({
    top: 10,
    left: 10,
    width: 50,
    height: 60
})

region.getRight() == 60
region.getBottom() == 70
```

## API

### Instantiation

You can create a new Region by calling the function returned by ```require('region')```. You can call it as a constructor if you want.

```js
var Region = require('region')

new Region({
    top: 10,
    left: 10
    //either width,height
    //or right, bottom
    width: 10,
    height: 10
})
```

or

```js
var Region = require('region')
var r = Region({
    top: 10,
    left: 10,
    right: 20,
    bottom: 20
})
```

You can instantiate a ```Region``` from a DOM node, using Region.fromDOM (NOTE: uses dom.offsetWidth/Height/Left/Top for getting coordinates)

```js
var r = Region.fromDOM(document.body)
```

### Getters

 * get - returns an object with {top, left, bottom, right}
 * getWidth
 * getHeight
 * getLeft
 * getTop
 * getRight
 * getBottom
 * getPosition - returns an object with {left, top}
 * getSize - returns an object with {width, height}

### containsPoint(x,y) or containsPoint({x,y}) : Boolean

```js
var r = Region({
    top: 10,
    left: 10,
    width: 10,
    height: 10
})

r.containsPoint(15, 10) == true
r.containsPoint({x: 10, y: 10}) == true
```

### equals(r): Boolean

Returns true if this region equals the region (or the object) given as the first param
var r = Region({top: 10, left: 10, bottom: 20, right: 20 })

r.equals({top: 10, left: 10, bottom: 20, right: 20 }) == true

### equalsPosition({top, left}): Boolean
Returns true if this region has top, left equal to the given coordinates

### equalsSize({width, height}): Boolean

Returns true if this region has the same size as the given region or object

```js
var coords = { top: 10, left: 10, width: 100, height: 100 }
var r = Region(coords)
r.equalsSize(coords) == true
r.equalsSize(r.clone()) == true
```
### getIntersection(Region): Region/false

Returns the region resulted by intersecting this region with the given region. If no intersection, returns false

### clone: Region

Returns a new region instance with the same coordinates
```js
var r = new Region({left: 10, right: 10, width: 10, height: 20})
r.clone().equals(r)
```

## Tests

```sh
$ make
```

Watch mode

```sh
$ make test-w
```

## License

```
MIT
```