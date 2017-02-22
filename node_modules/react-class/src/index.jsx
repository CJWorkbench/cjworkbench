'use strict';

var React = require('react')
var assign = require('object-assign')

function autoBind(object){
  var proto = object.constructor.prototype;

  var names = Object.getOwnPropertyNames(proto).filter(function(key){
    return key != 'constructor' && key != 'render' && typeof proto[key] == 'function'
  })

  names.push('setState');
  names.forEach(function(key){
    object[key] = object[key].bind(object)
  })

  return object
}

class ReactClass extends React.Component {

  constructor(props){

    super(props)
    autoBind(this)
  }

  prepareProps(thisProps){

    var props = assign({}, thisProps)

    props.style = this.prepareStyle(props)
    props.className = this.prepareClassName(props)

    return props
  }

  prepareClassName(props){
    var className = props.className || ''

    var defaultProps = this.constructor.defaultProps

    if (defaultProps && defaultProps.defaultClassName != null){
      className += ' ' + defaultProps.defaultClassName
    }

    return className
  }

  prepareStyle(props){
    var defaultStyle

    if (this.constructor.defaultProps){
      defaultStyle = this.constructor.defaultProps.defaultStyle
    }

    return assign({}, defaultStyle, props.style)
  }
}

module.exports = ReactClass