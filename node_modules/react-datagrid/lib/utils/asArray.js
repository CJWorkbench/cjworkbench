'use strict';

module.exports = function asArray(x) {
    if (!x) {
        x = [];
    }

    if (!Array.isArray(x)) {
        x = [x];
    }

    return x;
};