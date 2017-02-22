/*(c) Copyright 2015 Pivotal Software, Inc. All Rights Reserved.*/
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.Icon = undefined;

var _objectWithoutProperties2 = require('babel-runtime/helpers/objectWithoutProperties');

var _objectWithoutProperties3 = _interopRequireDefault(_objectWithoutProperties2);

var _createClass2 = require('babel-runtime/helpers/createClass');

var _createClass3 = _interopRequireDefault(_createClass2);

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');

var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);

var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');

var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);

var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');

var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);

var _inherits2 = require('babel-runtime/helpers/inherits');

var _inherits3 = _interopRequireDefault(_inherits2);

var _puiReactHelpers = require('pui-react-helpers');

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _puiReactSvg = require('pui-react-svg');

require('pui-css-iconography');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var types = _react2.default.PropTypes;

var SvgIcon = function (_Svg) {
  (0, _inherits3.default)(SvgIcon, _Svg);

  function SvgIcon() {
    var _ref;

    var _temp, _this, _ret;

    (0, _classCallCheck3.default)(this, SvgIcon);

    for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
      args[_key] = arguments[_key];
    }

    return _ret = (_temp = (_this = (0, _possibleConstructorReturn3.default)(this, (_ref = SvgIcon.__proto__ || (0, _getPrototypeOf2.default)(SvgIcon)).call.apply(_ref, [this].concat(args))), _this), _this.svgPathLoader = function (src) {
      return require('!!babel-loader!svg-react-loader!pui-css-iconography/svgs/' + src + '.svg');
    }, _temp), (0, _possibleConstructorReturn3.default)(_this, _ret);
  }

  return SvgIcon;
}(_puiReactSvg.Svg);

var Icon = exports.Icon = function (_React$Component) {
  (0, _inherits3.default)(Icon, _React$Component);

  function Icon() {
    (0, _classCallCheck3.default)(this, Icon);
    return (0, _possibleConstructorReturn3.default)(this, (Icon.__proto__ || (0, _getPrototypeOf2.default)(Icon)).apply(this, arguments));
  }

  (0, _createClass3.default)(Icon, [{
    key: 'render',
    value: function render() {
      var _props = this.props,
          src = _props.src,
          verticalAlign = _props.verticalAlign,
          others = (0, _objectWithoutProperties3.default)(_props, ['src', 'verticalAlign']);

      var props = (0, _puiReactHelpers.mergeProps)(others, { className: 'svgicon svg-' + verticalAlign });

      return _react2.default.createElement(
        'span',
        props,
        _react2.default.createElement(SvgIcon, { src: src, className: 'icon-' + src, key: src })
      );
    }
  }]);
  return Icon;
}(_react2.default.Component);

Icon.propTypes = {
  src: types.string.isRequired,
  style: types.object,
  verticalAlign: types.oneOf(['middle', 'baseline'])
};
Icon.defaultProps = {
  size: 'inherit',
  style: {},
  verticalAlign: 'middle'
};