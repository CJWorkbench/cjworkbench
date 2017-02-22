'use strict';

var mathAliases = require('../../common/var/mathAliases'),
    getPrecision = require('./getPrecision');

var max = mathAliases.max;

function getGreaterPrecision(n1, n2) {
  return max(getPrecision(n1), getPrecision(n2));
}

module.exports = getGreaterPrecision;