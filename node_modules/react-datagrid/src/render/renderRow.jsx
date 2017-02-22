'use strict';

var assign = require('object-assign')
var React  = require('react')

var Row        = require('../Row')
var RowFactory = React.createFactory(Row)

var renderCell = Row.prototype.renderCell

/**
 * Render a datagrid row
 *
 * @param  {Object}   props The props from which to build row props
 * @param  {Object}   data The data object that backs this row
 * @param  {Number}   index The index in the grid of the row to be rendered
 * @param  {Function} [fn] A function that can be used to modify built row props
 *
 * If props.rowFactory is specified, it will be used to build the ReactElement
 * corresponding to this row. In case it returns undefined, the default RowFactory will be used
 * (this case occurs when the rowFactory was specified just to modify the row props)
 *
 * @return {ReactElement}
 */
module.exports = function renderRow(props, data, index, fn){
    var factory     = props.rowFactory || RowFactory
    var key         = data[props.idProperty]
    var selectedKey = key
    var renderKey   = key

    if (!props.groupBy){
        renderKey = index - props.startIndex
    }

    var selected = false

    if (typeof props.selected == 'object' && props.selected){
        selected = !!props.selected[selectedKey]
    } else if (props.selected){
        selected = selectedKey === props.selected
    }

    var config = assign({}, props.rowProps, {
        selected : selected,

        key      : renderKey,
        data     : data,
        index    : index,

        cellFactory: props.cellFactory,
        renderCell : props.renderCell,
        renderText : props.renderText,
        cellPadding: props.cellPadding,
        rowHeight  : props.rowHeight,
        minWidth   : props.minRowWidth - props.scrollbarSize,
        columns    : props.columns,

        rowContextMenu: props.rowContextMenu,
        showMenu: props.showMenu,

        _onClick: this? this.handleRowClick: null
    })

    var style
    var rowStyle = props.rowStyle

    if (rowStyle){
        style = {}

        if (typeof rowStyle == 'function'){
            style = rowStyle(data, config)
        } else {
            assign(style, rowStyle)
        }

        config.style = style
    }

    var className = props.rowClassName

    if (typeof className == 'function'){
        className = className(data, config)
    }

    if (className){
        config.className = className
    }

    if (typeof fn == 'function'){
        config = fn(config)
    }

    var row = factory(config)

    if (row === undefined){
        row = RowFactory(config)
    }

    if (config.selected && this){
        this.selIndex = index
    }

    // var cached = this.rowCache && this.rowCache[renderKey]

    // if (cached){
        // return React.cloneElement(cached, {
        //     children: config.columns.map(function(col, index){
        //         return renderCell(config, col, index)
        //     })
        // })
    // }

    // if (this.rowCache){
    //     this.rowCache[renderKey] = row
    // }

    return row
}