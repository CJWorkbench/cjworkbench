'use strict';

var React  = require('react')
var assign = require('object-assign')
var normalize = require('react-style-normalizer')

var TEXT_ALIGN_2_JUSTIFY = {
    right : 'flex-end',
    center: 'center'
}

function copyProps(target, source, list){

    list.forEach(function(name){
        if (name in source){
            target[name] = source[name]
        }
    })

}

var PropTypes = React.PropTypes

var Cell = React.createClass({

    displayName: 'ReactDataGrid.Cell',

    propTypes: {
        className     : PropTypes.string,
        firstClassName: PropTypes.string,
        lastClassName : PropTypes.string,

        contentPadding: PropTypes.oneOfType([
            PropTypes.number,
            PropTypes.string
        ]),

        column : PropTypes.object,
        columns: PropTypes.array,
        index  : PropTypes.number,

        style      : PropTypes.object,
        text       : PropTypes.any,
        rowIndex   : PropTypes.number
    },

    getDefaultProps: function(){
        return {
            text: '',

            firstClassName: 'z-first',
            lastClassName : 'z-last',

            defaultStyle: {}
        }
    },

    prepareClassName: function(props) {
        var index     = props.index
        var columns   = props.columns
        var column    = props.column

        var textAlign = column && column.textAlign

        var className = props.className || ''

        className += ' ' + Cell.className

        if (columns){
            if (!index && props.firstClassName){
                className += ' ' + props.firstClassName
            }

            if (index == columns.length - 1 && props.lastClassName){
                className += ' ' + props.lastClassName
            }
        }

        if (textAlign){
            className += ' z-align-' + textAlign
        }

        return className
    },

    prepareStyle: function(props) {
        var column    = props.column
        var sizeStyle = column && column.sizeStyle

        var alignStyle
        var textAlign = (column && column.textAlign) || (props.style || {}).textAlign

        if (textAlign){
            alignStyle = { justifyContent: TEXT_ALIGN_2_JUSTIFY[textAlign] }
        }

        var style = assign({}, props.defaultStyle, sizeStyle, alignStyle, props.style)

        return normalize(style)
    },

    prepareProps: function(thisProps){

        var props = assign({}, thisProps)

        if (!props.column && props.columns){
            props.column  = props.columns[props.index]
        }

        props.className = this.prepareClassName(props)
        props.style     = this.prepareStyle(props)

        return props
    },

    render: function(){
        var props = this.p = this.prepareProps(this.props)

        var column    = props.column
        var textAlign = column && column.textAlign
        var text      = props.renderText?
            props.renderText(props.text, column, props.rowIndex):
            props.text

        var contentProps = {
            className: 'z-content',
            style    : {
                padding: props.contentPadding
            }
        }

        var content = props.renderCell?
                            props.renderCell(contentProps, text, props):
                            React.DOM.div(contentProps, text)

        var renderProps = assign({}, props)

        delete renderProps.data

        return (
            <div {...renderProps}>
                {content}
                {props.children}
            </div>
        )
    }
})

Cell.className = 'z-cell'

module.exports = Cell
