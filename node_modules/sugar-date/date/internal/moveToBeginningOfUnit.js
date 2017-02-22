'use strict';

var LocaleHelpers = require('../var/LocaleHelpers'),
    DateUnitIndexes = require('../var/DateUnitIndexes'),
    getLowerUnitIndex = require('./getLowerUnitIndex'),
    moveToBeginningOfWeek = require('./moveToBeginningOfWeek'),
    setUnitAndLowerToEdge = require('./setUnitAndLowerToEdge');

var WEEK_INDEX = DateUnitIndexes.WEEK_INDEX,
    localeManager = LocaleHelpers.localeManager;

function moveToBeginningOfUnit(d, unitIndex, localeCode) {
  if (unitIndex === WEEK_INDEX) {
    moveToBeginningOfWeek(d, localeManager.get(localeCode).getFirstDayOfWeek());
  }
  return setUnitAndLowerToEdge(d, getLowerUnitIndex(unitIndex));
}

module.exports = moveToBeginningOfUnit;