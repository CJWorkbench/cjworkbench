Clone With Props
=====================

Simple stand alone compatibility layer for the CloneWithProps util in React. Does not use any internal React methods, files, or functions

This is tested with React 0.9 to 0.12, and adds a trivial amount of code to get everything to work.

```javascript
var cloneWithProps = require('react-clonewithprops')

cloneWithProps(<MyComponent oldProp='hi'/> { newProp: 'hello' })
```