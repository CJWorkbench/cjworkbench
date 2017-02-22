'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes');

var DAY_INDEX = DateUnitIndexes.DAY_INDEX,
    MONTH_INDEX = DateUnitIndexes.MONTH_INDEX;

function getHigherUnitIndex(index) {
  return index === DAY_INDEX ? MONTH_INDEX : index + 1;
}

module.exports = getHigherUnitIndex;