'use strict';
var React    = require('react')
  , hasOwn   = Object.prototype.hasOwnProperty
  , version  = React.version.split('.').map(parseFloat)
  , RESERVED = {
      className:  resolve(joinClasses),
      children:   function(){},
      key:        function(){},
      ref:        function(){},
      style:      resolve(extend)
    };

module.exports = function cloneWithProps(child, props) {
  var newProps = mergeProps(props, child.props);

  if (!hasOwn.call(newProps, 'children') && hasOwn.call(child.props, 'children'))
    newProps.children = child.props.children;

  // < 0.11
  if (version[0] === 0 && version[1] < 11)
    return child.constructor.ConvenienceConstructor(newProps);
  
  // 0.11
  if (version[0] === 0 && version[1] === 11)
    return child.constructor(newProps);

  // 0.12
  else if (version[0] === 0 && version[1] === 12){
    MockLegacyFactory.isReactLegacyFactory = true
    MockLegacyFactory.type = child.type
    return React.createElement(MockLegacyFactory, newProps);
  }

  // 0.13+
  return React.createElement(child.type, newProps);

  function MockLegacyFactory(){}
}

function mergeProps(currentProps, childProps) {
  var newProps = extend(currentProps), key

  for (key in childProps) {
    if (hasOwn.call(RESERVED, key) )
      RESERVED[key](newProps, childProps[key], key)

    else if ( !hasOwn.call(newProps, key) )
      newProps[key] = childProps[key];
  }
  return newProps
}

function resolve(fn){
  return function(src, value, key){
    if( !hasOwn.call(src, key)) src[key] = value
    else src[key] = fn(src[key], value)
  }
}

function joinClasses(a, b){
  if ( !a ) return b || ''
  return a + (b ? ' ' + b : '')
}

function extend() {
  var target = {};
  for (var i = 0; i < arguments.length; i++) 
    for (var key in arguments[i]) if (hasOwn.call(arguments[i], key)) 
      target[key] = arguments[i][key]   
  return target
}