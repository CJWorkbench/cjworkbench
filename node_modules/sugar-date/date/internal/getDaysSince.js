'use strict';

var DateUnits = require('../var/DateUnits'),
    DateUnitIndexes = require('../var/DateUnitIndexes'),
    getTimeDistanceForUnit = require('./getTimeDistanceForUnit');

var DAY_INDEX = DateUnitIndexes.DAY_INDEX;

function getDaysSince(d1, d2) {
  return getTimeDistanceForUnit(d1, d2, DateUnits[DAY_INDEX]);
}

module.exports = getDaysSince;