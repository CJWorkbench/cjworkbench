'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes');

var HOURS_INDEX = DateUnitIndexes.HOURS_INDEX,
    DAY_INDEX = DateUnitIndexes.DAY_INDEX,
    WEEK_INDEX = DateUnitIndexes.WEEK_INDEX,
    MONTH_INDEX = DateUnitIndexes.MONTH_INDEX;

function getLowerUnitIndex(index) {
  if (index === MONTH_INDEX) {
    return DAY_INDEX;
  } else if (index === WEEK_INDEX) {
    return HOURS_INDEX;
  }
  return index - 1;
}

module.exports = getLowerUnitIndex;