'use strict';

var LocaleHelpers = require('../var/LocaleHelpers'),
    DateUnitIndexes = require('../var/DateUnitIndexes'),
    moveToEndOfWeek = require('./moveToEndOfWeek'),
    getLowerUnitIndex = require('./getLowerUnitIndex'),
    setUnitAndLowerToEdge = require('./setUnitAndLowerToEdge');

var WEEK_INDEX = DateUnitIndexes.WEEK_INDEX,
    localeManager = LocaleHelpers.localeManager;

function moveToEndOfUnit(d, unitIndex, localeCode, stopIndex) {
  if (unitIndex === WEEK_INDEX) {
    moveToEndOfWeek(d, localeManager.get(localeCode).getFirstDayOfWeek());
  }
  return setUnitAndLowerToEdge(d, getLowerUnitIndex(unitIndex), stopIndex, true);
}

module.exports = moveToEndOfUnit;