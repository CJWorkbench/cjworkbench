(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory(require("React"));
	else if(typeof define === 'function' && define.amd)
		define(["React"], factory);
	else if(typeof exports === 'object')
		exports["LoadMask"] = factory(require("React"));
	else
		root["LoadMask"] = factory(root["React"]);
})(this, function(__WEBPACK_EXTERNAL_MODULE_1__) {
return /******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};

/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {

/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;

/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};

/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);

/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;

/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}


/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;

/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;

/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";

/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var React = __webpack_require__(1);
	var assign = __webpack_require__(2);
	var Loader = __webpack_require__(3);

	module.exports = React.createClass({

	    displayName: 'LoadMask',

	    getDefaultProps: function getDefaultProps() {

	        return {
	            visible: false,
	            visibleDisplayValue: 'block',
	            defaultStyle: {
	                background: 'rgba(128, 128, 128, 0.5)',
	                position: 'absolute',
	                width: '100%',
	                height: '100%',
	                display: 'none',
	                top: 0,
	                left: 0
	            }
	        };
	    },

	    render: function render() {
	        var props = assign({}, this.props);

	        props.style = this.prepareStyle(props);

	        props.className = props.className || '';
	        props.className += ' loadmask';

	        return React.createElement(
	            'div',
	            props,
	            React.createElement(Loader, { size: props.size })
	        );
	    },

	    prepareStyle: function prepareStyle(props) {

	        var style = assign({}, props.defaultStyle, props.style);

	        style.display = props.visible ? props.visibleDisplayValue : 'none';

	        return style;
	    }
	});

/***/ },
/* 1 */
/***/ function(module, exports) {

	module.exports = __WEBPACK_EXTERNAL_MODULE_1__;

/***/ },
/* 2 */
/***/ function(module, exports) {

	'use strict';

	function ToObject(val) {
		if (val == null) {
			throw new TypeError('Object.assign cannot be called with null or undefined');
		}

		return Object(val);
	}

	module.exports = Object.assign || function (target, source) {
		var from;
		var keys;
		var to = ToObject(target);

		for (var s = 1; s < arguments.length; s++) {
			from = arguments[s];
			keys = Object.keys(Object(from));

			for (var i = 0; i < keys.length; i++) {
				to[keys[i]] = from[keys[i]];
			}
		}

		return to;
	};


/***/ },
/* 3 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var React = __webpack_require__(1);
	var assign = __webpack_require__(2);

	module.exports = React.createClass({

	    displayName: 'Loader',

	    getDefaultProps: function getDefaultProps() {
	        return {
	            defaultStyle: {
	                margin: 'auto',
	                position: 'absolute',
	                top: 0,
	                left: 0,
	                bottom: 0,
	                right: 0
	            },
	            defaultClassName: 'loader',
	            size: 40
	        };
	    },

	    render: function render() {
	        var props = assign({}, this.props);

	        this.prepareStyle(props);

	        props.className = props.className || '';
	        props.className += ' ' + props.defaultClassName;

	        return React.DOM.div(props, React.createElement('div', { className: 'loadbar loadbar-1' }), React.createElement('div', { className: 'loadbar loadbar-2' }), React.createElement('div', { className: 'loadbar loadbar-3' }), React.createElement('div', { className: 'loadbar loadbar-4' }), React.createElement('div', { className: 'loadbar loadbar-5' }), React.createElement('div', { className: 'loadbar loadbar-6' }), React.createElement('div', { className: 'loadbar loadbar-7' }), React.createElement('div', { className: 'loadbar loadbar-8' }), React.createElement('div', { className: 'loadbar loadbar-9' }), React.createElement('div', { className: 'loadbar loadbar-10' }), React.createElement('div', { className: 'loadbar loadbar-11' }), React.createElement('div', { className: 'loadbar loadbar-12' }));
	    },

	    prepareStyle: function prepareStyle(props) {

	        var style = {};

	        assign(style, props.defaultStyle);
	        assign(style, props.style);

	        style.width = props.size;
	        style.height = props.size;

	        props.style = style;
	    }
	});

/***/ }
/******/ ])
});
;