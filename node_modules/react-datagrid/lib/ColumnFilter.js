'use strict';

var React = require('react');
var assign = require('object-assign');
var ReactMenu = require('react-menus');
var findDOMNode = require('react-dom').findDOMNode;

function stopPropagation(event) {
    event.stopPropagation();
}

function emptyFn() {}

var FILTER_FIELDS = {};

module.exports = {

    getColumnFilterFieldFactory: function getColumnFilterFieldFactory(column) {

        var type = column.type || 'string';

        return FILTER_FIELDS[type] || React.DOM.input;
    },

    getFilterField: function getFilterField(props) {
        var column = props.column;
        var filterValue = this.filterValues ? this.filterValues[column.name] : '';

        var fieldProps = {
            autoFocus: true,
            defaultValue: filterValue,
            column: column,
            onChange: this.onFilterChange.bind(this, column),
            onKeyUp: this.onFilterKeyUp.bind(this, column)
        };

        var fieldFactory = column.renderFilterField || this.props.renderFilterField;
        var field;

        if (fieldFactory) {
            field = fieldFactory(fieldProps);
        }

        if (field === undefined) {
            field = this.getColumnFilterFieldFactory(column)(fieldProps);
        }

        return field;
    },

    onFilterKeyUp: function onFilterKeyUp(column, event) {
        if (event.key == 'Enter') {
            this.onFilterClick(column, event);
        }
    },

    onFilterChange: function onFilterChange(column, eventOrValue) {

        var value = eventOrValue;

        if (eventOrValue && eventOrValue.target) {
            value = eventOrValue.target.value;
        }

        this.filterValues = this.filterValues || {};
        this.filterValues[column.name] = value;

        if (this.props.liveFilter) {
            this.filterBy(column, value);
        }
    },

    filterBy: function filterBy(column, value, event) {
        ;(this.props.onFilter || emptyFn)(column, value, this.filterValues, event);
    },

    onFilterClick: function onFilterClick(column, event) {
        this.showMenu(null);

        var value = this.filterValues ? this.filterValues[column.name] : '';

        this.filterBy(column, value, event);
    },

    onFilterClear: function onFilterClear(column) {
        this.showMenu(null);

        if (this.filterValues) {
            this.filterValues[column.name] = '';
        }

        this.filterBy(column, '');(this.props.onClearFilter || emptyFn).apply(null, arguments);
    },

    getFilterButtons: function getFilterButtons(props) {

        var column = props.column;
        var factory = column.renderFilterButtons || this.props.renderFilterButtons;

        var result;

        if (factory) {
            result = factory(props);
        }

        if (result !== undefined) {
            return result;
        }

        var doFilter = this.onFilterClick.bind(this, column);
        var doClear = this.onFilterClear.bind(this, column);

        return React.createElement(
            'div',
            { style: { textAlign: 'center' } },
            React.createElement(
                'button',
                { onClick: doFilter },
                'Filter'
            ),
            React.createElement(
                'button',
                { onClick: doClear, style: { marginLeft: 5 } },
                'Clear'
            )
        );
    },

    filterMenuFactory: function filterMenuFactory(props) {

        var overStyle = {
            background: 'white',
            color: 'auto'
        };

        var column = props.column;
        var field = this.getFilterField(props);
        var buttons = this.getFilterButtons({
            column: column
        });

        var children = [field, buttons].map(function (x, index) {
            return React.createElement(
                ReactMenu.Item,
                { key: index },
                React.createElement(
                    ReactMenu.Item.Cell,
                    null,
                    x
                )
            );
        });

        props.itemOverStyle = props.itemOverStyle || overStyle;
        props.itemActiveStyle = props.itemActiveStyle || overStyle;
        props.onClick = props.onClick || stopPropagation;

        var factory = this.props.filterMenuFactory;
        var result;

        if (factory) {
            result = factory(props);

            if (result !== undefined) {
                return result;
            }
        }

        props.onMount = this.onFilterMenuMount;

        return React.createElement(
            ReactMenu,
            props,
            children
        );
    },

    onFilterMenuMount: function onFilterMenuMount(menu) {
        var dom = findDOMNode(menu);

        if (dom) {
            var input = dom.querySelector('input');

            if (input) {
                setTimeout(function () {
                    input.focus();
                }, 10);
            }
        }
    }
};