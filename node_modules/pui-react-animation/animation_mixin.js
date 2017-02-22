//(c) Copyright 2015 Pivotal Software, Inc. All Rights Reserved.
'use strict';

var _map = require('babel-runtime/core-js/map');

var _map2 = _interopRequireDefault(_map);

var _extends2 = require('babel-runtime/helpers/extends');

var _extends3 = _interopRequireDefault(_extends2);

var _getIterator2 = require('babel-runtime/core-js/get-iterator');

var _getIterator3 = _interopRequireDefault(_getIterator2);

var _isNan = require('babel-runtime/core-js/number/is-nan');

var _isNan2 = _interopRequireDefault(_isNan);

var _weakMap = require('babel-runtime/core-js/weak-map');

var _weakMap2 = _interopRequireDefault(_weakMap);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var Easing = require('easing-js');

var privates = new _weakMap2.default();

function isNumber(obj) {
  return typeof obj === 'number' && !(0, _isNan2.default)(obj);
}

function strip(number) {
  return parseFloat(number.toPrecision(12));
}

function someAnimating(animations) {
  for (var _iterator = animations, _isArray = Array.isArray(_iterator), _i = 0, _iterator = _isArray ? _iterator : (0, _getIterator3.default)(_iterator);;) {
    var _ref;

    if (_isArray) {
      if (_i >= _iterator.length) break;
      _ref = _iterator[_i++];
    } else {
      _i = _iterator.next();
      if (_i.done) break;
      _ref = _i.value;
    }

    var _ref2 = _ref,
        animation = _ref2[1];

    if (animation.isAnimating) return true;
  }
  return false;
}

function scheduleAnimation(context) {
  AnimationMixin.raf(function () {
    var animations = privates.get(context);
    var currentTime = AnimationMixin.now();
    var shouldUpdate = false;
    animations && animations.forEach(function (animation, name) {
      var isFunction = typeof name === 'function';
      if (!animation.isAnimating) return;

      var duration = animation.duration,
          easing = animation.easing,
          endValue = animation.endValue,
          startTime = animation.startTime,
          startValue = animation.startValue;


      var deltaTime = currentTime - startTime;
      if (deltaTime >= duration) {
        (0, _extends3.default)(animation, { isAnimating: false, startTime: currentTime, value: endValue });
      } else {
        animation.value = strip(Easing[easing](deltaTime, startValue, endValue - startValue, duration));
      }

      shouldUpdate = shouldUpdate || !isFunction;
      if (isFunction) name(animation.value);
    });

    if (animations && someAnimating(animations)) scheduleAnimation(context);
    if (shouldUpdate) context.forceUpdate();
  });
}

var AnimationMixin = {
  componentWillUnmount: function componentWillUnmount() {
    privates.delete(this);
  },
  shouldAnimate: function shouldAnimate() {
    return true;
  },


  raf: require('raf'),

  now: require('performance-now'),

  animate: function animate(name, endValue, duration) {
    var options = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : {};

    var animations = privates.get(this);
    if (!animations) {
      privates.set(this, animations = new _map2.default());
    }

    var animation = animations.get(name);
    var shouldAnimate = this.shouldAnimate() && options.animation !== false;
    if (!animation || !shouldAnimate || !isNumber(endValue)) {
      var easing = options.easing || 'linear';
      var startValue = isNumber(options.startValue) && shouldAnimate ? options.startValue : endValue;
      animation = { duration: duration, easing: easing, endValue: endValue, isAnimating: false, startValue: startValue, value: startValue };
      animations.set(name, animation);
    }

    if (!duration) {
      (0, _extends3.default)(animation, { endValue: endValue, value: endValue });
      animations.set(name, animation);
    }

    if (animation.value !== endValue && !animation.isAnimating) {
      if (!someAnimating(animations)) scheduleAnimation(this);
      var startTime = 'startTime' in options ? options.startTime : AnimationMixin.now();
      duration = duration || animation.duration;
      var _easing = options.easing || animation.easing;
      var _startValue = animation.value;
      (0, _extends3.default)(animation, { isAnimating: true, endValue: endValue, startValue: _startValue, startTime: startTime, duration: duration, easing: _easing });
    }

    return animation.value;
  }
};

module.exports = AnimationMixin;