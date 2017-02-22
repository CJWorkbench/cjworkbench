# react-class

> A carefully crafted base class for all your React components

## Features

 * auto-bind methods
 * avoid boilerplate with default style and default class name

## Install

```sh
$ npm install react-class --save
```

## Usage

Instead of extending `React.Component` you have to extend the class exported by `react-class`.

```jsx
import Component from 'react-class'

class MyApp extends Component {

  render(){
    // you have to call prepareProps in order to get defaultClassName
    // and defaultStyle applied to props
    var props = this.prepareProps(this.props)

    return <div {...props} onClick={this.onClick}>
      //onClick is auto-bound to "this", so you can keep your code dry
    </div>
  }

  onClick(){
    console.log(this)
  }
}

MyApp.defaultProps = {
  defaultStyle: {
    border: '2px solid red'
  },
  defaultClassName: 'myapp'
}
```

So you can use `<MyApp style={{color: 'blue'}} className="main" />` and get `defaultProps.defaultClassName` always applied to your component and `defaultProps.defaultStyle` merged into `props.style`. Of course, any colliding style you specify in `props.style` will override the one in `defaultProps.defaultStyle`

The result of

```jsx
<MyApp style={{color: 'blue'}} className="main" />
```
is a div with the following:
```html
<div style="color: blue; border: 2px solid red" class="myapp main">
</div>
```

## prepareProps

To get `defaultProps.defaultStyle` and `defaultProps.defaultClassName` applied on the props object, remember to call **prepareProps**

```js
var props = this.prepareProps(this.props)
```

All it does is the following:

```jsx
function prepareProps(thisProps){
  var props = assign({}, thisProps)

  props.style = assign({},
                this.contructor.defaultProps.defaultStyle, props.style
              )
  props.className = (props.className || '') + ' ' +
                (this.constructor.defaultProps.defaultClassName || '')

  return props
}
```

## auto-binding

In order to get autobinding, just extend the class exported by `react-class`

```jsx

var ReactClass = require('react-class');

class App extends ReactClass { ... }
```


## FAQ

### What problems does it solve?

Generally you want your components to have a default style (of course, which can be overriden).

Very often you also want a default `className` to be applied all the time to your components, no matter if the user of your components passes a `className` attribute or not in the props.

Also, autobinding is a nice feature!

### What if I want to remove it in the future?

`react-class` is a very thin layer around `React.Component`, so just in case you decide removing it in the future, you'll be safe and will only have to do very minor code changes.

We're not doing anything magical!


## LICENSE

#### MIT
