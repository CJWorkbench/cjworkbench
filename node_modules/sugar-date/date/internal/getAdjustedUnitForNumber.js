'use strict';

var trunc = require('../../common/var/trunc'),
    withPrecision = require('../../common/internal/withPrecision'),
    getAdjustedUnit = require('./getAdjustedUnit');

function getAdjustedUnitForNumber(ms) {
  return getAdjustedUnit(ms, function(unit) {
    return trunc(withPrecision(ms / unit.multiplier, 1));
  });
}

module.exports = getAdjustedUnitForNumber;