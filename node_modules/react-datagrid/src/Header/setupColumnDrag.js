'use strict';

var Region     = require('region')
var DragHelper = require('drag-helper')
var findDOMNode = require('react-dom').findDOMNode

function range(start, end){
    var res = []

    for ( ; start <= end; start++){
        res.push(start)
    }

    return res
}

function buildIndexes(direction, index, dragIndex){
    var indexes = direction < 0 ?
                    range(index, dragIndex):
                    range(dragIndex, index)

    var result = {}

    indexes.forEach(function(value){
        result[value] = true
    })

    return result
}

module.exports = function(header, props, column, event){

    event.preventDefault()

    var headerNode   = findDOMNode(header)
    var headerRegion = Region.from(headerNode)
    var dragColumn = column
    var dragColumnIndex
    var columnData
    var shiftRegion

    DragHelper(event, {

        constrainTo: headerRegion.expand({ top: true, bottom: true}),

        onDragStart: function(event, config){

            var columnHeaders = headerNode.querySelectorAll('.' + props.cellClassName)

            columnData = props.columns.map(function(column, i){
                var region = Region.from(columnHeaders[i])

                if (column === dragColumn){
                    dragColumnIndex = i
                    shiftRegion = region.clone()
                }

                return {
                    column: column,
                    index: i,
                    region: region
                }
            })

            header.setState({
                dragColumn: column,
                dragging  : true
            })

            config.columnData = columnData

        },
        onDrag: function(event, config){
            var diff = config.diff.left
            var directionSign = diff < 0? -1: 1
            var state = {
                dragColumnIndex  : dragColumnIndex,
                dragColumn  : dragColumn,
                dragLeft    : diff,
                dropIndex   : null,
                shiftIndexes: null,
                shiftSize   : null
            }

            var shift
            var shiftSize
            var newLeft   = shiftRegion.left + diff
            var newRight  = newLeft + shiftRegion.width
            var shiftZone = { left: newLeft, right: newRight}

            config.columnData.forEach(function(columnData, index, arr){

                var itColumn = columnData.column
                var itRegion = columnData.region

                if (shift || itColumn === dragColumn){
                    return
                }

                var itLeft  = itRegion.left
                var itRight = itRegion.right
                var itZone  = directionSign == -1?
                            { left: itLeft, right: itLeft + itRegion.width }:
                            { left: itRight - itRegion.width, right: itRight }

                if (shiftRegion.width < itRegion.width){
                    //shift region is smaller than itRegion
                    shift = Region.getIntersectionWidth(
                            itZone,
                            shiftZone
                        ) >= Math.min(
                            itRegion.width,
                            shiftRegion.width
                        ) / 2

                } else {
                    //shift region is bigger than itRegion
                    shift = Region.getIntersectionWidth(itRegion, shiftZone) >= itRegion.width / 2
                }

                if (shift) {
                    shiftSize = -directionSign * shiftRegion.width
                    state.dropIndex = index
                    state.shiftIndexes = buildIndexes(directionSign, index, dragColumnIndex)
                    state.shiftSize = shiftSize
                }
            })

            header.setState(state)
        },

        onDrop: function(event){
            header.onDrop(event)
        }
    })
}
