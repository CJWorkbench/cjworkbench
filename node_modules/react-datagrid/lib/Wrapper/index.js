'use strict';

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var React = require('react');
var assign = require('object-assign');
var Scroller = require('react-virtual-scroller');

function emptyFn() {}

module.exports = React.createClass({

    displayName: 'ReactDataGrid.Wrapper',

    propTypes: {
        scrollLeft: React.PropTypes.number,
        scrollTop: React.PropTypes.number,
        scrollbarSize: React.PropTypes.number,
        rowHeight: React.PropTypes.any,
        renderCount: React.PropTypes.number
    },

    getDefaultProps: function getDefaultProps() {
        return {
            scrollLeft: 0,
            scrollTop: 0
        };
    },

    onMount: function onMount(scroller) {
        ;(this.props.onMount || emptyFn)(this, scroller);
    },

    render: function render() {

        var props = this.prepareProps(this.props);
        var rowsCount = props.renderCount;

        var groupsCount = 0;
        if (props.groupData) {
            groupsCount = props.groupData.groupsCount;
        }

        rowsCount += groupsCount;

        // var loadersSize = props.loadersSize
        var verticalScrollerSize = (props.totalLength + groupsCount) * props.rowHeight; // + loadersSize

        var content = props.empty ? React.createElement(
            'div',
            { className: 'z-empty-text', style: props.emptyTextStyle },
            props.emptyText
        ) : React.createElement('div', _extends({}, props.tableProps, { ref: 'table' }));

        return React.createElement(
            Scroller,
            {
                onMount: this.onMount,
                preventDefaultHorizontal: true,

                loadMask: !props.loadMaskOverHeader,
                loading: props.loading,

                scrollbarSize: props.scrollbarSize,

                minVerticalScrollStep: props.rowHeight,
                scrollTop: props.scrollTop,
                scrollLeft: props.scrollLeft,

                scrollHeight: verticalScrollerSize,
                scrollWidth: props.minRowWidth,

                onVerticalScroll: this.onVerticalScroll,
                onHorizontalScroll: this.onHorizontalScroll
            },
            content
        );
    },

    onVerticalScrollOverflow: function onVerticalScrollOverflow() {},

    onHorizontalScrollOverflow: function onHorizontalScrollOverflow() {},

    onHorizontalScroll: function onHorizontalScroll(scrollLeft) {
        this.props.onScrollLeft(scrollLeft);
    },

    onVerticalScroll: function onVerticalScroll(pos) {
        this.props.onScrollTop(pos);
    },

    prepareProps: function prepareProps(thisProps) {
        var props = {};

        assign(props, thisProps);

        return props;
    }
});