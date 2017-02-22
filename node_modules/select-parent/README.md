select-parent
=============

querySelector but for parent nodes. Given a node, selects the parent/ancestor that matches the given selector.

## Install

```sh
$ npm install --save select-parent
```

## Usage

```js
var selectParent = require('select-parent')

var redDiv = selectParent('div.red', document.getElementById('inner-div'))

```

Or you can use the curried form as well.
```js

var selectParent = require('select-parent')

var selectRed = selectParent('div.red')

var redDiv = selectRed(document.getElementById('nested-div'))
```
