'use strict';

var Sugar = require('sugar-core'),
    DateUnitIndexes = require('./var/DateUnitIndexes'),
    moveToBeginningOfUnit = require('./internal/moveToBeginningOfUnit'),
    getUnitIndexForParamName = require('./internal/getUnitIndexForParamName');

var DAY_INDEX = DateUnitIndexes.DAY_INDEX;

Sugar.Date.defineInstance({

  'reset': function(date, unit, localeCode) {
    var unitIndex = unit ? getUnitIndexForParamName(unit) : DAY_INDEX;
    moveToBeginningOfUnit(date, unitIndex, localeCode);
    return date;
  }

});

module.exports = Sugar.Date.reset;