'use strict';

var assign = require('object-assign')
var getSelected = require('./getSelected')

var hasOwn = function(obj, prop){
    return Object.prototype.hasOwnProperty.call(obj, prop)
}

/**
 * Here is how multi selection is implemented - trying to emulate behavior in OSX Finder
 *
 * When there is no selection, and an initial click for selection is done, keep that index (SELINDEX)
 *
 * Next, if we shift+click, we mark as selected the items from initial index to current click index.
 *
 * Now, if we ctrl+click elsewhere, keep the selection, but also add the selected file,
 * and set SELINDEX to the new index. Now on any subsequent clicks, have the same behavior,
 * selecting/deselecting items starting from SELINDEX to the new click index
 */


module.exports = {

    findInitialSelectionIndex: function(){
        var selected = getSelected(this.p, this.state)
        var index = undefined

        if (!Object.keys(selected).length){
            return index
        }


        var i = 0
        var data = this.p.data
        var len = data.length
        var id
        var idProperty = this.props.idProperty

        for (; i < len; i++){
            id = data[i][idProperty]

            if (selected[id]){
                index = i
            }
        }

        return index
    },

    notifySelection: function(selected, data){
        if (typeof this.props.onSelectionChange == 'function'){
            this.props.onSelectionChange(selected, data)
        }

        if (!hasOwn(this.props, 'selected')){
            this.cleanCache()
            this.setState({
                defaultSelected: selected
            })
        }
    },

    handleSingleSelection: function(data, event){
        var props = this.p

        var rowSelected = this.isRowSelected(data)
        var newSelected = !rowSelected

        var ctrlKey = event.metaKey || event.ctrlKey
        if (rowSelected && event && !ctrlKey){
            //if already selected and not ctrl, keep selected
            newSelected = true
        }

        var selectedId = newSelected?
                            data[props.idProperty]:
                            null

        this.notifySelection(selectedId, data)
    },


    handleMultiSelection: function(data, event, config){

        var selIndex = config.selIndex
        var prevShiftKeyIndex = config.prevShiftKeyIndex

        var props = this.p
        var map   = selIndex == null?
                        {}:
                        assign({}, getSelected(props, this.state))

        if (prevShiftKeyIndex != null && selIndex != null){
            var min = Math.min(prevShiftKeyIndex, selIndex)
            var max = Math.max(prevShiftKeyIndex, selIndex)

            var removeArray = props.data.slice(min, max + 1) || []

            removeArray.forEach(function(item){
                if (item){
                    var id = item[props.idProperty]
                    delete map[id]
                }
            })
        }

        data.forEach(function(item){
            if (item){
                var id = item[props.idProperty]
                map[id] = item
            }
        })

        this.notifySelection(map, data)
    },

    handleMultiSelectionRowToggle: function(data, event){

        var selected   = getSelected(this.p, this.state)
        var isSelected = this.isRowSelected(data)

        var clone = assign({}, selected)
        var id    = data[this.p.idProperty]

        if (isSelected){
            delete clone[id]
        } else {
            clone[id] = data
        }

        this.notifySelection(clone, data)

        return isSelected
    },

    handleSelection: function(rowProps, event){

        var props = this.p

        if (!hasOwn(props, 'selected') && !hasOwn(props, 'defaultSelected')){
            return
        }

        var isSelected  = this.isRowSelected(rowProps.data)
        var multiSelect = this.isMultiSelect()

        if (!multiSelect){
            this.handleSingleSelection(rowProps.data, event)
            return
        }

        if (this.selIndex === undefined){
            this.selIndex = this.findInitialSelectionIndex()
        }

        var selIndex = this.selIndex

        //multi selection
        var index = rowProps.index
        var prevShiftKeyIndex = this.shiftKeyIndex
        var start
        var end
        var data

        if (event.metaKey || event.ctrlKey){
            this.selIndex = index
            this.shiftKeyIndex = null

            var unselect = this.handleMultiSelectionRowToggle(props.data[index], event)

            if (unselect){
                this.selIndex++
                this.shiftKeyIndex = prevShiftKeyIndex
            }

            return
        }

        if (!event.shiftKey){
            //set selIndex, for future use
            this.selIndex = index
            this.shiftKeyIndex = null

            //should not select many, so make selIndex null
            selIndex = null
        } else {
            this.shiftKeyIndex = index
        }

        if (selIndex == null){
            data = [props.data[index]]
        } else {
            start = Math.min(index, selIndex)
            end   = Math.max(index, selIndex) + 1
            data  = props.data.slice(start, end)
        }

        this.handleMultiSelection(data, event, {
            selIndex: selIndex,
            prevShiftKeyIndex: prevShiftKeyIndex
        })
    },


    isRowSelected: function(data){
        var selectedMap = this.getSelectedMap()
        var id          = data[this.props.idProperty]

        return selectedMap[id]
    },

    isMultiSelect: function(){
        var selected = getSelected(this.p, this.state)

        return selected && typeof selected == 'object'
    },

    getSelectedMap: function(){
        var selected    = getSelected(this.p, this.state)
        var multiSelect = selected && typeof selected == 'object'
        var map

        if (multiSelect){
            map = selected
        } else {
            map = {}
            map[selected] = true
        }

        return map
    }
}