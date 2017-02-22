'use strict';

var _createClass = (function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ('value' in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; })();

var _get = function get(_x, _x2, _x3) { var _again = true; _function: while (_again) { var object = _x, property = _x2, receiver = _x3; _again = false; if (object === null) object = Function.prototype; var desc = Object.getOwnPropertyDescriptor(object, property); if (desc === undefined) { var parent = Object.getPrototypeOf(object); if (parent === null) { return undefined; } else { _x = parent; _x2 = property; _x3 = receiver; _again = true; desc = parent = undefined; continue _function; } } else if ('value' in desc) { return desc.value; } else { var getter = desc.get; if (getter === undefined) { return undefined; } return getter.call(receiver); } } };

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError('Cannot call a class as a function'); } }

function _inherits(subClass, superClass) { if (typeof superClass !== 'function' && superClass !== null) { throw new TypeError('Super expression must either be null or a function, not ' + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var React = require('react');
var assign = require('object-assign');

function autoBind(object) {
  var proto = object.constructor.prototype;

  var names = Object.getOwnPropertyNames(proto).filter(function (key) {
    return key != 'constructor' && key != 'render' && typeof proto[key] == 'function';
  });

  names.push('setState');
  names.forEach(function (key) {
    object[key] = object[key].bind(object);
  });

  return object;
}

var ReactClass = (function (_React$Component) {
  _inherits(ReactClass, _React$Component);

  function ReactClass(props) {
    _classCallCheck(this, ReactClass);

    _get(Object.getPrototypeOf(ReactClass.prototype), 'constructor', this).call(this, props);
    autoBind(this);
  }

  _createClass(ReactClass, [{
    key: 'prepareProps',
    value: function prepareProps(thisProps) {

      var props = assign({}, thisProps);

      props.style = this.prepareStyle(props);
      props.className = this.prepareClassName(props);

      return props;
    }
  }, {
    key: 'prepareClassName',
    value: function prepareClassName(props) {
      var className = props.className || '';

      var defaultProps = this.constructor.defaultProps;

      if (defaultProps && defaultProps.defaultClassName != null) {
        className += ' ' + defaultProps.defaultClassName;
      }

      return className;
    }
  }, {
    key: 'prepareStyle',
    value: function prepareStyle(props) {
      var defaultStyle;

      if (this.constructor.defaultProps) {
        defaultStyle = this.constructor.defaultProps.defaultStyle;
      }

      return assign({}, defaultStyle, props.style);
    }
  }]);

  return ReactClass;
})(React.Component);

module.exports = ReactClass;