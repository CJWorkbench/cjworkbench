'use strict';

var ISODefaults = require('../var/ISODefaults'),
    getDate = require('./getDate'),
    setDate = require('./setDate'),
    setYear = require('./setYear'),
    getYear = require('./getYear'),
    getMonth = require('./getMonth'),
    setMonth = require('./setMonth'),
    cloneDate = require('./cloneDate'),
    getWeekday = require('./getWeekday'),
    setWeekday = require('./setWeekday'),
    classChecks = require('../../common/var/classChecks'),
    moveToFirstDayOfWeekYear = require('./moveToFirstDayOfWeekYear');

var isNumber = classChecks.isNumber,
    ISO_FIRST_DAY_OF_WEEK = ISODefaults.ISO_FIRST_DAY_OF_WEEK,
    ISO_FIRST_DAY_OF_WEEK_YEAR = ISODefaults.ISO_FIRST_DAY_OF_WEEK_YEAR;

function setISOWeekNumber(d, num) {
  if (isNumber(num)) {
    // Intentionally avoiding updateDate here to prevent circular dependencies.
    var isoWeek = cloneDate(d), dow = getWeekday(d);
    moveToFirstDayOfWeekYear(isoWeek, ISO_FIRST_DAY_OF_WEEK, ISO_FIRST_DAY_OF_WEEK_YEAR);
    setDate(isoWeek, getDate(isoWeek) + 7 * (num - 1));
    setYear(d, getYear(isoWeek));
    setMonth(d, getMonth(isoWeek));
    setDate(d, getDate(isoWeek));
    setWeekday(d, dow || 7);
  }
  return d.getTime();
}

module.exports = setISOWeekNumber;