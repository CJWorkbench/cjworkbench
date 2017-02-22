# Purpose

Calling function constructors with an array of arguments is difficult. Until [spread](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Spread_operator) params are fully supported in all browsers, newify does the job.

For a given function constructor
```js
function Student(firstName, lastName, birthYear){
	this.firstName = firstName
	this.lastName = lastName
	this.birthYear = birthYear
}
```

We want to easily call the function constructor like

```js
var arr = ['john','scot', 1980]
var s = new Student(arr) //but this will obviously not work as expected.

//we need ES6 spread
var s = new Student(...arr)
```

But since we can't use spread in ES5 ...

NEWIFY to the rescue!

```js
var arr = ['john','scot', 1980]
var s = require('newify')(Student, arr)
```

# Installation

```
npm install newify
```

# Usage

As in the above example, just give `newify` a function and an array of args

```js
var arr = ['john','scot', 1980]
var s = require('newify')(Student, arr)
```

# Run tests

```
make test
```