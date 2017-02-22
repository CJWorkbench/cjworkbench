'use strict';

var React = require('react');
var renderMenu = require('./renderMenu');
var renderRow = require('./renderRow');
var tableStyle = require('./tableStyle');
var slice = require('./slice');
var LoadMask = require('react-load-mask');

function getData(props) {

    if (!props.virtualRendering) {
        return props.data;
    }

    return slice(props.data, props);
}

module.exports = function (props, rows) {

    rows = rows || getData(props).map(function (data, index) {
        return renderRow.call(this, props, data, index + props.startIndex);
    }, this);

    // if (props.topLoader && props.scrollTop < (2 * props.rowHeight)){
    // rows.unshift(props.topLoader)
    // }

    return {
        className: 'z-table',
        style: tableStyle(props),
        children: rows
    };
};