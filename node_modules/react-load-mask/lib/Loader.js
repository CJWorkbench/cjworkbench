'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _objectAssign = require('object-assign');

var _objectAssign2 = _interopRequireDefault(_objectAssign);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var DEFAULT_CLASS_NAME = 'react-load-mask__loader';
var LOADBAR_CLASSNAME = DEFAULT_CLASS_NAME + '-loadbar';

var notEmpty = function notEmpty(s) {
  return !!s;
};

var Loader = function (_React$Component) {
  _inherits(Loader, _React$Component);

  function Loader() {
    _classCallCheck(this, Loader);

    return _possibleConstructorReturn(this, Object.getPrototypeOf(Loader).apply(this, arguments));
  }

  _createClass(Loader, [{
    key: 'render',
    value: function render() {
      var props = this.props;

      var style = (0, _objectAssign2.default)({}, props.style, {
        width: props.size,
        height: props.size
      });

      var className = [props.className, DEFAULT_CLASS_NAME, props.theme && DEFAULT_CLASS_NAME + '--theme-' + props.theme].filter(notEmpty).join(' ');

      return _react2.default.createElement(
        'div',
        _extends({}, props, { style: style, className: className }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--1' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--2' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--3' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--4' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--5' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--6' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--7' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--8' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--9' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--10' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--11' }),
        _react2.default.createElement('div', { className: LOADBAR_CLASSNAME + ' ' + LOADBAR_CLASSNAME + '--12' })
      );
    }
  }]);

  return Loader;
}(_react2.default.Component);

exports.default = Loader;


Loader.defaultProps = {
  size: 40
};