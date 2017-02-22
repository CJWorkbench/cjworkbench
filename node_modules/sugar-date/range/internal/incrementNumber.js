'use strict';

var withPrecision = require('../../common/internal/withPrecision');

function incrementNumber(current, amount, precision) {
  return withPrecision(current + amount, precision);
}

module.exports = incrementNumber;