'use strict';

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _reactDom = require('react-dom');

var React = require('react');
var ReactDOM = require('react-dom');
var assign = require('object-assign');
var Toolbar = require('react-simple-toolbar');
var Region = Toolbar.Region;
var normalize = require('react-style-normalizer');

var WHITESPACE = ' ';
function sortAsc(a, b) {
	return a - b;
}

function emptyFn() {}

function gotoPrev(props) {
	return React.createElement(
		'svg',
		_extends({ version: '1.1', viewBox: '0 0 2 3' }, props),
		React.createElement('polygon', { points: '2,0 2,3 0,1.5 ' })
	);
}

function gotoNext(props) {
	return React.createElement(
		'svg',
		_extends({ version: '1.1', viewBox: '0 0 2 3' }, props),
		React.createElement('polygon', { points: '0,0 2,1.5 0,3' })
	);
}

function gotoFirst(props) {
	return React.createElement(
		'svg',
		_extends({ version: '1.1', viewBox: '0 0 3 3' }, props),
		React.createElement('polygon', { points: '3,0 3,3 1,1.5' }),
		React.createElement('rect', { height: '3', width: '0.95', y: '0', x: '0' })
	);
}

function gotoLast(props) {
	return React.createElement(
		'svg',
		_extends({ version: '1.1', viewBox: '0 0 3 3' }, props),
		React.createElement('polygon', { points: '0,0 0,3 2,1.5' }),
		React.createElement('rect', { height: '3', width: '0.95', y: '0', x: '2' })
	);
}

function refresh(props) {
	return React.createElement(
		'svg',
		_extends({ version: '1.1', x: '0px', y: '0px', viewBox: '0 0 487.23 487.23' }, props),
		React.createElement(
			'g',
			null,
			React.createElement('path', { d: 'M55.323,203.641c15.664,0,29.813-9.405,35.872-23.854c25.017-59.604,83.842-101.61,152.42-101.61 c37.797,0,72.449,12.955,100.23,34.442l-21.775,3.371c-7.438,1.153-13.224,7.054-14.232,14.512 c-1.01,7.454,3.008,14.686,9.867,17.768l119.746,53.872c5.249,2.357,11.33,1.904,16.168-1.205 c4.83-3.114,7.764-8.458,7.796-14.208l0.621-131.943c0.042-7.506-4.851-14.144-12.024-16.332 c-7.185-2.188-14.947,0.589-19.104,6.837l-16.505,24.805C370.398,26.778,310.1,0,243.615,0C142.806,0,56.133,61.562,19.167,149.06 c-5.134,12.128-3.84,26.015,3.429,36.987C29.865,197.023,42.152,203.641,55.323,203.641z' }),
			React.createElement('path', { d: 'M464.635,301.184c-7.27-10.977-19.558-17.594-32.728-17.594c-15.664,0-29.813,9.405-35.872,23.854 c-25.018,59.604-83.843,101.61-152.42,101.61c-37.798,0-72.45-12.955-100.232-34.442l21.776-3.369 c7.437-1.153,13.223-7.055,14.233-14.514c1.009-7.453-3.008-14.686-9.867-17.768L49.779,285.089 c-5.25-2.356-11.33-1.905-16.169,1.205c-4.829,3.114-7.764,8.458-7.795,14.207l-0.622,131.943 c-0.042,7.506,4.85,14.144,12.024,16.332c7.185,2.188,14.948-0.59,19.104-6.839l16.505-24.805 c44.004,43.32,104.303,70.098,170.788,70.098c100.811,0,187.481-61.561,224.446-149.059 C473.197,326.043,471.903,312.157,464.635,301.184z' })
		)
	);
}

function separator(props) {

	if (props.showSeparators === false) {
		return;
	}

	var margin = 5;
	var width = 2;
	var color = props.iconProps.style.fill;

	var result;

	var sepProps = {
		width: 2,
		margin: 5,
		color: color
	};

	if (props.separatorFactory) {
		result = props.separatorFactory(sepProps);
	}

	if (result !== undefined) {
		return result;
	}

	var style = normalize({
		marginLeft: sepProps.margin,
		marginRight: sepProps.margin,
		width: sepProps.width,
		background: sepProps.color,
		display: 'inline-block',
		alignSelf: 'stretch'
	});

	return React.createElement('span', { style: style });
}

var ICON_MAP = {
	gotoFirst: gotoFirst,
	gotoLast: gotoLast,
	gotoPrev: gotoPrev,
	gotoNext: gotoNext,
	refresh: refresh
};

var defaultStyles = {
	// gotoPrev: { marginRight: 10},
	// gotoNext: { marginLeft: 10}
};

module.exports = React.createClass({

	displayName: 'PaginationToolbar',

	getDefaultProps: function getDefaultProps() {
		return {
			iconSize: 20,
			showRefreshIcon: true,
			showPageSize: true,
			defaultStyle: {
				color: 'inherit'
			},

			pageSizes: [10, 20, 50, 100, 200, 500, 1000],

			theme: '',

			defaultIconProps: {
				version: '1.2',
				style: {
					cursor: 'pointer',
					marginLeft: 3,
					marginRight: 3,
					fill: '#8E8E8E',
					verticalAlign: 'middle'
				},
				disabledStyle: {
					cursor: 'auto',
					fill: '#DFDCDC'
				},
				overStyle: {
					fill: 'gray'
				}
			}
		};
	},

	getInitialState: function getInitialState() {
		return {
			mouseOver: {}
		};
	},

	prepareProps: function prepareProps(thisProps) {
		var props = assign({}, thisProps);

		props.className = this.prepareClassName(props);
		props.iconProps = this.prepareIconProps(props);
		props.style = this.prepareStyle(props);
		props.pageSizes = this.preparePageSizes(props);
		delete props.defaultStyle;

		return props;
	},

	prepareClassName: function prepareClassName(props) {
		var className = props.className || '';

		className += ' react-datagrid-pagination-toolbar';

		return className;
	},

	preparePageSizes: function preparePageSizes(props) {
		var sizes = [].concat(props.pageSizes);

		if (sizes.indexOf(props.pageSize) == -1) {
			sizes.push(props.pageSize);
		}

		return sizes.sort(sortAsc);
	},

	prepareIconProps: function prepareIconProps(props) {
		var iconProps = assign({}, props.defaultIconProps);
		var defaultIconStyle = iconProps.style;
		var defaultIconOverStyle = iconProps.overStyle;
		var defaultIconDisabledStyle = iconProps.disabledStyle;

		assign(iconProps, props.iconProps);

		var iconSizeStyle = {};

		if (props.iconSize != null) {
			iconSizeStyle = { width: props.iconSize, height: props.iconSize };
		}

		if (props.iconHeight != null) {
			iconSizeStyle.height = props.iconHeight;
		}
		if (props.iconWidth != null) {
			iconSizeStyle.width = props.iconWidth;
		}

		iconProps.style = assign({}, defaultIconStyle, iconSizeStyle, iconProps.style);
		iconProps.overStyle = assign({}, defaultIconOverStyle, iconProps.overStyle);
		iconProps.disabledStyle = assign({}, defaultIconDisabledStyle, iconProps.disabledStyle);

		return iconProps;
	},

	prepareStyle: function prepareStyle(props) {
		var borderStyle = {};
		var borderName = 'borderTop';

		if (props.position == 'top') {
			borderName = 'borderBottom';
		}

		if (props.border) {
			borderStyle[borderName] = props.border;
		}

		return assign({}, props.defaultStyle, borderStyle, props.style);
	},

	handleInputChange: function handleInputChange(event) {
		var value = event.target.value * 1;

		if (!isNaN(value) && value >= this.props.minPage && value <= this.props.maxPage && value != this.props.page) {
			this.gotoPage(value);
		}
	},

	handleInputBlur: function handleInputBlur() {
		this.setState({
			inputFocused: false
		});
	},

	handleInputFocus: function handleInputFocus() {

		var page = this.props.page;
		this.setState({
			inputFocused: true
		}, function () {

			var domNode = (0, _reactDom.findDOMNode)(this.refs.input);
			domNode.value = page;
		}.bind(this));
	},

	onPageSizeChange: function onPageSizeChange(event) {
		this.props.onPageSizeChange(event.target.value * 1);
	},

	renderInput: function renderInput(props) {
		var otherProps = {};

		if (this.state.inputFocused) {
			otherProps.defaultValue = props.page;
		} else {
			otherProps.value = props.page;
		}

		var inputProps = assign({
			ref: 'input',
			onBlur: this.handleInputBlur,
			onFocus: this.handleInputFocus,
			style: normalize({
				marginLeft: 5,
				marginRight: 5,
				padding: 2,
				maxWidth: 60,
				textAlign: 'right',
				flex: 1,
				minWidth: 40
			}),
			page: props.page,
			onChange: this.handleInputChange
		}, otherProps);

		var defaultFactory = React.DOM.input;
		var factory = props.pageInputFactory || defaultFactory;

		var result = factory(inputProps);

		if (result === undefined) {
			result = defaultFactory(inputProps);
		}

		return result;
	},

	renderSelect: function renderSelect(props) {

		var options = props.pageSizes.map(function (value) {
			return React.createElement(
				'option',
				{ value: value },
				value
			);
		});

		var selectProps = {
			onChange: this.onPageSizeChange,
			value: props.pageSize,
			style: { marginLeft: 5, marginRight: 5, padding: 2, textAlign: 'right' },
			children: options
		};

		var defaultFactory = React.DOM.select;
		var factory = props.pageSizeSelectFactory || defaultFactory;

		var result = factory(selectProps);

		if (result === undefined) {
			result = defaultFactory(selectProps);
		}

		return result;
	},

	renderDisplaying: function renderDisplaying(props) {
		var start = (props.pageSize * (props.page - 1) || 0) + 1;
		var end = Math.min(props.pageSize * props.page, props.dataSourceCount) || 1;
		var refreshIcon = props.showRefreshIcon ? this.icon('refresh', props) : null;
		var sep = refreshIcon ? this.separator : null;

		var factory = props.displayingFactory;

		if (factory) {
			return factory({
				start: start,
				end: end,
				dataSourceCount: props.dataSourceCount,
				page: props.page,
				pageSize: props.pageSize,
				minPage: props.minPage,
				maxPage: props.maxPage,
				reload: this.reload,
				gotoPage: this.gotoPage,
				refreshIcon: refreshIcon
			});
		}

		var textStyle = { display: 'inline-block', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' };

		return React.createElement(
			'div',
			{ style: normalize({ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }) },
			React.createElement(
				'span',
				{ style: textStyle },
				'Displaying ',
				start,
				' - ',
				end,
				' of ',
				props.dataSourceCount || 1,
				'.'
			),
			sep,
			refreshIcon
		);
	},

	renderPageSize: function renderPageSize(props) {
		if (props.showPageSize) {
			return React.createElement(
				'div',
				null,
				'Page size ',
				this.renderSelect(props)
			);
		}
	},

	render: function render() {

		var props = this.prepareProps(this.props);

		this.separator = separator(props);

		var showPageSize = props.showPageSize;
		var pageSize = showPageSize ? this.renderPageSize(props) : null;

		var start = props.pageSize * (props.page - 1) + 1;
		var end = Math.min(props.pageSize * props.page, props.dataSourceCount);

		var displaying = this.renderDisplaying(props);
		var minWidth = 430;

		if (!showPageSize) {
			minWidth -= 100;
		}

		var sep = this.separator;

		return React.createElement(
			Toolbar,
			props,
			React.createElement(
				Region,
				{ flex: '1 1 auto', style: normalize({ display: 'flex', alignItems: 'center', minWidth: minWidth }) },
				this.icon('gotoFirst', props),
				this.icon('gotoPrev', props),
				sep,
				'Page ',
				this.renderInput(props),
				' of',
				WHITESPACE,
				props.maxPage,
				'.',
				sep,
				this.icon('gotoNext', props),
				this.icon('gotoLast', props),
				showPageSize ? sep : null,
				pageSize
			),
			React.createElement(
				Region,
				{ flex: '1 1 auto' },
				displaying
			)
		);
	},

	icon: function icon(iconName, props) {
		var icon = props[iconName + 'Icon'];

		if (!icon || typeof icon != 'function') {
			var MAP = {
				refresh: props.page,
				gotoFirst: props.minPage,
				gotoLast: props.maxPage,
				gotoPrev: Math.max(props.page - 1, props.minPage),
				gotoNext: Math.min(props.page + 1, props.maxPage)
			};

			var targetPage = MAP[iconName];
			var disabled = targetPage === props.page && iconName != 'refresh';
			var mouseOver = this.state.mouseOver[iconName];

			var iconProps = assign({
				mouseOver: mouseOver,
				name: iconName,
				disabled: disabled
			}, props.iconProps);

			var iconStyle = iconProps.style = assign({}, iconProps.style, defaultStyles[iconName], props.iconStyle, props[iconName + 'IconStyle']);

			if (mouseOver) {
				iconProps.style = assign({}, iconStyle, iconProps.overStyle, props.overIconStyle);
			}
			if (disabled) {
				iconProps.style = assign({}, iconStyle, iconProps.disabledStyle, props.disabledIconStyle);
			} else {
				iconProps.onClick = iconName == 'refresh' ? this.reload : this.gotoPage.bind(this, targetPage);
			}

			iconProps.onMouseEnter = this.onIconMouseEnter.bind(this, props, iconProps);
			iconProps.onMouseLeave = this.onIconMouseLeave.bind(this, props, iconProps);

			var defaultFactory = ICON_MAP[iconName];
			var factory = props[iconName + 'IconFactory'] || defaultFactory;
			icon = factory(iconProps);

			if (icon === undefined) {
				icon = defaultFactory(iconProps);
			}
		}

		return icon;
	},

	onIconMouseEnter: function onIconMouseEnter(props, iconProps) {
		var mouseOver = this.state.mouseOver;

		mouseOver[iconProps.name] = true;

		this.setState({});
	},

	onIconMouseLeave: function onIconMouseLeave(props, iconProps) {
		var mouseOver = this.state.mouseOver;

		mouseOver[iconProps.name] = false;

		this.setState({});
	},

	reload: function reload() {
		;(this.props.reload || emptyFn)();
	},

	gotoPage: function gotoPage(page) {
		this.props.onPageChange(page);
	}
});