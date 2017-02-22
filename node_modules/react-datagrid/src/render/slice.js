'use strict';

function slice(data, props){

    if (!props.virtualRendering){
        return data
    }

    return data.slice(
            props.startIndex,
            props.startIndex + props.renderCount
        )
}

module.exports = slice