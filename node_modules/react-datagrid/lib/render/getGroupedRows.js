'use strict';

var React = require('react');

var Row = require('../Row');
var Cell = require('../Cell');
var CellFactory = React.createFactory(Cell);

var renderRow = require('./renderRow');

function renderData(props, data, depth) {

    return data.map(function (data, index) {

        return renderRow(props, data, index, function (config) {
            config.cellFactory = function (cellProps) {
                if (cellProps.index === 0) {
                    cellProps.style.paddingLeft = depth * props.groupNestingWidth;
                }

                return CellFactory(cellProps);
            };

            config.className += ' z-grouped';

            return config;
        });
    });
}

function renderGroupRow(props, groupData) {

    var cellStyle = {
        minWidth: props.totalColumnWidth,
        paddingLeft: (groupData.depth - 1) * props.groupNestingWidth
    };

    return React.createElement(
        Row,
        { className: 'z-group-row', key: 'group-' + groupData.valuePath, rowHeight: props.rowHeight },
        React.createElement(Cell, {
            className: 'z-group-cell',
            contentPadding: props.cellPadding,
            text: groupData.value,
            style: cellStyle
        })
    );
}

function renderGroup(props, groupData) {

    var result = [renderGroupRow(props, groupData)];

    if (groupData && groupData.leaf) {
        result.push.apply(result, renderData(props, groupData.data, groupData.depth));
    } else {
        groupData.keys.forEach(function (key) {
            var items = renderGroup(props, groupData.data[key]);
            result.push.apply(result, items);
        });
    }

    return result;
}

function renderGroups(props, groupsData) {
    var result = [];

    groupsData.keys.map(function (key) {
        result.push.apply(result, renderGroup(props, groupsData.data[key]));
    });

    return result;
}

module.exports = function (props, groupData) {
    return renderGroups(props, groupData);
};