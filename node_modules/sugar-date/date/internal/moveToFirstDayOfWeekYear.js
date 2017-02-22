'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes'),
    setDate = require('./setDate'),
    setUnitAndLowerToEdge = require('./setUnitAndLowerToEdge'),
    moveToBeginningOfWeek = require('./moveToBeginningOfWeek');

var MONTH_INDEX = DateUnitIndexes.MONTH_INDEX;

function moveToFirstDayOfWeekYear(d, firstDayOfWeek, firstDayOfWeekYear) {
  setUnitAndLowerToEdge(d, MONTH_INDEX);
  setDate(d, firstDayOfWeekYear);
  moveToBeginningOfWeek(d, firstDayOfWeek);
}

module.exports = moveToFirstDayOfWeekYear;