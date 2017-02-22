'use strict';

module.exports = function (props, state) {
                    var selected = props.selected == null ? state.defaultSelected : props.selected;

                    return selected;
};