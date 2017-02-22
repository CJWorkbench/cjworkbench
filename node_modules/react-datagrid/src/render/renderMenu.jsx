'use strict';

module.exports = function renderMenu(props){
    if (!props.menu){
        return
    }

    return props.menu({
        className : 'z-header-menu-column',
        gridColumns: props.columns
    })
}