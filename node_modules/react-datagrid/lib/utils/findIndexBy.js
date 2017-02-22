'use strict';

function findIndexBy(arr, fn) {

    var i = 0;
    var len = arr.length;

    for (; i < len; i++) {
        if (fn(arr[i]) === true) {
            return i;
        }
    }

    return -1;
}

module.exports = findIndexBy;