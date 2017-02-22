'use strict';

var Sugar = require('sugar-core'),
    DateUnitIndexes = require('./var/DateUnitIndexes'),
    getWeekday = require('./internal/getWeekday'),
    setWeekday = require('./internal/setWeekday'),
    moveToEndOfUnit = require('./internal/moveToEndOfUnit');

var DAY_INDEX = DateUnitIndexes.DAY_INDEX;

Sugar.Date.defineInstance({

  'endOfISOWeek': function(date) {
    if (getWeekday(date) !== 0) {
      setWeekday(date, 7);
    }
    return moveToEndOfUnit(date, DAY_INDEX);
  }

});

module.exports = Sugar.Date.endOfISOWeek;