'use strict';

var React   = require('react')
var Region  = require('region')
var ReactMenu = React.createFactory(require('react-menus'))
var assign  = require('object-assign')
var clone   = require('clone')
var asArray = require('../utils/asArray')
var findIndexBy = require('../utils/findIndexBy')
var findIndexByName = require('../utils/findIndexByName')
var Cell    = require('../Cell')
var setupColumnDrag   = require('./setupColumnDrag')
var setupColumnResize = require('./setupColumnResize')

var normalize   = require('react-style-normalizer')

function emptyFn(){}

function getColumnSortInfo(column, sortInfo){

    sortInfo = asArray(sortInfo)

    var index = findIndexBy(sortInfo, function(info){
        return info.name === column.name
    })

    return sortInfo[index]
}

function removeColumnSort(column, sortInfo){
    sortInfo = asArray(sortInfo)

    var index = findIndexBy(sortInfo, function(info){
        return info.name === column.name
    })

    if (~index){
        sortInfo.splice(index, 1)
    }

    return sortInfo
}

function getDropState(){
    return {
        dragLeft  : null,
        dragColumn: null,
        dragColumnIndex: null,
        dragging  : false,
        dropIndex : null,

        shiftIndexes: null,
        shiftSize: null
    }
}

module.exports = React.createClass({

    displayName: 'ReactDataGrid.Header',

    propTypes: {
        columns: React.PropTypes.array
    },

    onDrop: function(event){
        var state = this.state
        var props = this.props

        if (state.dragging){
            event.stopPropagation()
        }

        var dragIndex = state.dragColumnIndex
        var dropIndex = state.dropIndex

        if (dropIndex != null){

            //since we need the indexes in the array of all columns
            //not only in the array of the visible columns
            //we need to search them and make this transform
            var dragColumn = props.columns[dragIndex]
            var dropColumn = props.columns[dropIndex]

            dragIndex = findIndexByName(props.allColumns, dragColumn.name)
            dropIndex = findIndexByName(props.allColumns, dropColumn.name)

            this.props.onDropColumn(dragIndex, dropIndex)
        }

        this.setState(getDropState())
    },

    getDefaultProps: function(){
        return {
            defaultClassName : 'z-header-wrapper',
            draggingClassName: 'z-dragging',
            cellClassName    : 'z-column-header',
            defaultStyle    : {},
            sortInfo        : null,
            scrollLeft      : 0,
            scrollTop       : 0
        }
    },

    getInitialState: function(){

        return {
            mouseOver : true,
            dragging  : false,

            shiftSize : null,
            dragColumn: null,
            shiftIndexes: null
        }
    },

    render: function() {
        var props = this.prepareProps(this.props)
        var state = this.state

        var cellMap = {}
        var cells = props.columns
                        .map(function(col, index){
                            var cell = this.renderCell(props, state, col, index)
                            cellMap[col.name] = cell

                            return cell
                        }, this)

        if (props.columnGroups && props.columnGroups.length){

            cells = props.columnGroups.map(function(colGroup){
                var cellProps = {}
                var columns = []

                var cells = colGroup.columns.map(function(colName){
                    var col = props.columnMap[colName]
                    columns.push(col)
                    return cellMap[colName]
                })

                return <Cell {...cellProps}>
                    {cells}
                </Cell>
            }, this)
        }

        var style = normalize(props.style)
        var headerStyle = normalize({
            paddingRight: props.scrollbarSize,
            transform   : 'translate3d(' + -props.scrollLeft + 'px, ' + -props.scrollTop + 'px, 0px)'
        })

        return (
            <div style={style} className={props.className}>
                <div className='z-header' style={headerStyle}>
                    {cells}
                </div>
            </div>
        )
    },

    renderCell: function(props, state, column, index){

        var resizing  = props.resizing
        var text      = column.title
        var className = props.cellClassName || ''
        var style     = {
            left: 0
        }

        var menu = this.renderColumnMenu(props, state, column, index)

        if (state.dragColumn && state.shiftIndexes && state.shiftIndexes[index]){
            style.left = state.shiftSize
        }

        if (state.dragColumn === column){
            className += ' z-drag z-over'
            style.zIndex = 1
            style.left = state.dragLeft || 0
        }

        var filterIcon = props.filterIcon || <svg version="1.1" style={{transform: 'translate3d(0,0,0)', height:'100%', width: '100%', padding: '0px 2px' }} viewBox="0 0 3 4">
                                <polygon points="0,0 1,2 1,4 2,4 2,2 3,0 " style={{fill: props.filterIconColor,strokeWidth:0, fillRule: 'nonZero'}} />
                            </svg>

        var filter  = column.filterable?
                        <div className="z-show-filter" onMouseUp={this.handleFilterMouseUp.bind(this, column)}>
                            {filterIcon}
                        </div>
                        :
                        null

        var resizer = column.resizable?
                        <span className="z-column-resize" onMouseDown={this.handleResizeMouseDown.bind(this, column)} />:
                        null

        if (column.sortable){
            text = <span >{text}<span className="z-icon-sort-info" /></span>

            var sortInfo = getColumnSortInfo(column, props.sortInfo)

            if (sortInfo && sortInfo.dir){
                className += (sortInfo.dir === -1 || sortInfo.dir === 'desc'?
                                ' z-desc':
                                ' z-asc')
            }

            className += ' z-sortable'
        }

        if (filter){
            className += ' z-filterable'
        }

        if (state.mouseOver === column.name && !resizing){
            className += ' z-over'
        }

        if (props.menuColumn === column.name){
            className += ' z-active'
        }

        className += ' z-unselectable'

        var events = {}

        events.onMouseDown = this.handleMouseDown.bind(this, column)
        events.onMouseUp = this.handleMouseUp.bind(this, column)

        return (
            <Cell
                key={column.name}
                contentPadding={props.cellPadding}
                columns={props.columns || []}
                index={index}
                column={props.columns[index]}
                className={className}
                style={style}
                text={text}
                header={true}
                onMouseOut={this.handleMouseOut.bind(this, column)}
                onMouseOver={this.handleMouseOver.bind(this, column)}
                {...events}
            >
                {filter}
                {menu}
                {resizer}
            </Cell>
        )
    },

    toggleSort: function(column){
        var sortInfo       = asArray(clone(this.props.sortInfo))
        var columnSortInfo = getColumnSortInfo(column, sortInfo)

        if (!columnSortInfo){
            columnSortInfo = {
                name: column.name,
                type: column.type,
                fn  : column.sortFn
            }

            sortInfo.push(columnSortInfo)
        }

        if (typeof column.toggleSort === 'function'){
            column.toggleSort(columnSortInfo, sortInfo)
        } else {

            var dir     = columnSortInfo.dir
            var dirSign = dir === 'asc'? 1 : dir === 'desc'? -1: dir
            var newDir  = dirSign === 1? -1: dirSign === -1?  0: 1

            columnSortInfo.dir = newDir

            if (!newDir){
                sortInfo = removeColumnSort(column, sortInfo)
            }
        }

        ;(this.props.onSortChange || emptyFn)(sortInfo)
    },

    renderColumnMenu: function(props, state, column, index){
        if (!props.withColumnMenu){
            return
        }

        var menuIcon = props.menuIcon || <svg version="1.1" style={{transform: 'translate3d(0,0,0)', height:'100%', width: '100%', padding: '0px 2px' }} viewBox="0 0 3 4">
                <polygon points="0,0 1.5,3 3,0 " style={{fill: props.menuIconColor,strokeWidth:0, fillRule: 'nonZero'}} />
            </svg>

        return <div className="z-show-menu" onMouseUp={this.handleShowMenuMouseUp.bind(this, props, column, index)}>
            {menuIcon}
        </div>
    },

    handleShowMenuMouseUp: function(props, column, index, event){
        event.nativeEvent.stopSort = true

        this.showMenu(column, event)
    },

    showMenu: function(column, event){

        var menuItem = function(column){
            var visibility = this.props.columnVisibility

            var visible = column.visible

            if (column.name in visibility){
                visible = visibility[column.name]
            }

            return {
                cls     : visible?'z-selected': '',
                selected: visible? <span style={{fontSize: '0.95em'}}>✓</span>: '',
                label   : column.title,
                fn      : this.toggleColumn.bind(this, column)
            }
        }.bind(this)

        function menu(eventTarget, props){

            var columns = props.gridColumns

            props.columns = [ 'selected', 'label']
            props.items = columns.map(menuItem)
            props.alignTo = eventTarget
            props.alignPositions = [
                'tl-bl',
                'tr-br',
                'bl-tl',
                'br-tr'
            ]
            props.style = {
                position: 'absolute'
            }

            var factory = this.props.columnMenuFactory || ReactMenu

            var result = factory(props)

            return result === undefined?
                    ReactMenu(props):
                    result
        }

        this.props.showMenu(menu.bind(this, event.currentTarget), {
            menuColumn: column.name
        })
    },

    showFilterMenu: function(column, event){

        function menu(eventTarget, props){

            var defaultFactory = this.props.filterMenuFactory
            var factory = column.filterMenuFactory || defaultFactory

            props.columns = ['component']
            props.column = column
            props.alignTo = eventTarget
            props.alignPositions = [
                'tl-bl',
                'tr-br',
                'bl-tl',
                'br-tr'
            ]
            props.style = {
                position: 'absolute'
            }

            var result = factory(props)

            return result === undefined?
                        defaultFactory(props):
                        result
        }

        this.props.showMenu(menu.bind(this, event.currentTarget), {
            menuColumn: column.name
        })
    },

    toggleColumn: function(column){
        this.props.toggleColumn(column)
    },

    hideMenu: function(){
        this.props.showColumnMenu(null, null)
    },

    handleResizeMouseDown: function(column, event){
        setupColumnResize(this, this.props, column, event)

        //in order to prevent setupColumnDrag in handleMouseDown
        // event.stopPropagation()

        //we are doing setupColumnDrag protection using the resizing flag on native event
        if (event.nativeEvent){
            event.nativeEvent.resizing = true
        }
    },

    handleFilterMouseUp: function(column, event){
        event.nativeEvent.stopSort = true

        this.showFilterMenu(column, event)
        // event.stopPropagation()
    },

    handleMouseUp: function(column, event){
        if (this.state.dragging){
            return
        }

        if (this.state.resizing){
            return
        }

        if (event && event.nativeEvent && event.nativeEvent.stopSort){
            return
        }

        if (column.sortable){
            this.toggleSort(column)
        }
    },

    handleMouseOut: function(column){
        this.setState({
            mouseOver: false
        })
    },

    handleMouseOver: function(column){
        this.setState({
            mouseOver: column.name
        })
    },

    handleMouseDown: function(column, event){
        if (event && event.nativeEvent && event.nativeEvent.resizing){
            return
        }

        if (!this.props.reorderColumns){
            return
        }

        setupColumnDrag(this, this.props, column, event)
    },

    onResizeDragStart: function(config){
        this.setState({
            resizing: true
        })
        this.props.onColumnResizeDragStart(config)
    },

    onResizeDrag: function(config){
        this.props.onColumnResizeDrag(config)
    },

    onResizeDrop: function(config, resizeInfo, event){
        this.setState({
            resizing: false
        })

        this.props.onColumnResizeDrop(config, resizeInfo)
    },

    prepareProps: function(thisProps){
        var props = {}

        assign(props, thisProps)

        this.prepareClassName(props)
        this.prepareStyle(props)

        var columnMap = {}

        ;(props.columns || []).forEach(function(col){
            columnMap[col.name] = col
        })

        props.columnMap = columnMap

        return props
    },

    prepareClassName: function(props){
        props.className = props.className || ''
        props.className += ' ' + props.defaultClassName

        if (this.state.dragging){
            props.className += ' ' + props.draggingClassName
        }
    },

    prepareStyle: function(props){
        var style = props.style = {}

        assign(style, props.defaultStyle)
    }
})
