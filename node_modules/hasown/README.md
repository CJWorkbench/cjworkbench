hasown
=======

JavaScript curried hasOwn helper.

## Install

```sh
$ npm install hasown
```

## Usage

#### Simple usage

```js
var hasOwn = require('hasown')
var person = { name: 'bob' }

hasOwn(person, 'name') == true
```

#### Curried usage

```js
var hasOwn = require('hasown')
var person = { lastName: 'willson' }
var child = Object.create(person)
child.age = 1
child.firstName = 'bob'

var childHasOwn = hasOwn(child)

for (var k in child) if (childHasOwn(k)){
    console.log(k, ' = ', child[k])
}
```

## Test

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