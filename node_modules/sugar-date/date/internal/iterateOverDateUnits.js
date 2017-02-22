'use strict';

var DateUnits = require('../var/DateUnits'),
    DateUnitIndexes = require('../var/DateUnitIndexes'),
    isUndefined = require('../../common/internal/isUndefined');

var YEAR_INDEX = DateUnitIndexes.YEAR_INDEX;

function iterateOverDateUnits(fn, startIndex, endIndex) {
  endIndex = endIndex || 0;
  if (isUndefined(startIndex)) {
    startIndex = YEAR_INDEX;
  }
  for (var index = startIndex; index >= endIndex; index--) {
    if (fn(DateUnits[index], index) === false) {
      break;
    }
  }
}

module.exports = iterateOverDateUnits;