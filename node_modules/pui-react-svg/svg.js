/*(c) Copyright 2015 Pivotal Software, Inc. All Rights Reserved.*/
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.Svg = undefined;

var _objectWithoutProperties2 = require('babel-runtime/helpers/objectWithoutProperties');

var _objectWithoutProperties3 = _interopRequireDefault(_objectWithoutProperties2);

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');

var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);

var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');

var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);

var _createClass2 = require('babel-runtime/helpers/createClass');

var _createClass3 = _interopRequireDefault(_createClass2);

var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');

var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);

var _inherits2 = require('babel-runtime/helpers/inherits');

var _inherits3 = _interopRequireDefault(_inherits2);

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var types = _react2.default.PropTypes;

var Svg = exports.Svg = function (_React$Component) {
  (0, _inherits3.default)(Svg, _React$Component);

  function Svg(props, context) {
    (0, _classCallCheck3.default)(this, Svg);

    var _this = (0, _possibleConstructorReturn3.default)(this, (Svg.__proto__ || (0, _getPrototypeOf2.default)(Svg)).call(this, props, context));

    _this.state = { Component: null };
    return _this;
  }

  (0, _createClass3.default)(Svg, [{
    key: 'componentDidMount',
    value: function componentDidMount() {
      var src = this.props.src;

      this.setState({ Component: this.svgPathLoader(src) });
    }
  }, {
    key: 'svgPathLoader',
    value: function svgPathLoader(src) {
      try {
        return require('!!babel!svg-react!../../app/svg/' + src + '.svg');
      } catch (e) {}
    }
  }, {
    key: 'render',
    value: function render() {
      var _props = this.props,
          src = _props.src,
          props = (0, _objectWithoutProperties3.default)(_props, ['src']);
      var Component = this.state.Component;

      if (Component) return _react2.default.createElement(Component, props);
      return _react2.default.createElement('svg', props);
    }
  }]);
  return Svg;
}(_react2.default.Component);

Svg.propTypes = {
  src: types.string.isRequired
};