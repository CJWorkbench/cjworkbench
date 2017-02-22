'use strict';

var ISODefaults = require('../var/ISODefaults'),
    setDate = require('./setDate'),
    getDate = require('./getDate'),
    cloneDate = require('./cloneDate'),
    isUndefined = require('../../common/internal/isUndefined'),
    moveToEndOfWeek = require('./moveToEndOfWeek'),
    moveToBeginningOfWeek = require('./moveToBeginningOfWeek'),
    moveToFirstDayOfWeekYear = require('./moveToFirstDayOfWeekYear');

var ISO_FIRST_DAY_OF_WEEK = ISODefaults.ISO_FIRST_DAY_OF_WEEK,
    ISO_FIRST_DAY_OF_WEEK_YEAR = ISODefaults.ISO_FIRST_DAY_OF_WEEK_YEAR;

function getWeekNumber(d, allowPrevious, firstDayOfWeek, firstDayOfWeekYear) {
  var isoWeek, n = 0;
  if (isUndefined(firstDayOfWeek)) {
    firstDayOfWeek = ISO_FIRST_DAY_OF_WEEK;
  }
  if (isUndefined(firstDayOfWeekYear)) {
    firstDayOfWeekYear = ISO_FIRST_DAY_OF_WEEK_YEAR;
  }
  // Moving to the end of the week allows for forward year traversal, ie
  // Dec 29 2014 is actually week 01 of 2015.
  isoWeek = moveToEndOfWeek(cloneDate(d), firstDayOfWeek);
  moveToFirstDayOfWeekYear(isoWeek, firstDayOfWeek, firstDayOfWeekYear);
  if (allowPrevious && d < isoWeek) {
    // If the date is still before the start of the year, then it should be
    // the last week of the previous year, ie Jan 1 2016 is actually week 53
    // of 2015, so move to the beginning of the week to traverse the year.
    isoWeek = moveToBeginningOfWeek(cloneDate(d), firstDayOfWeek);
    moveToFirstDayOfWeekYear(isoWeek, firstDayOfWeek, firstDayOfWeekYear);
  }
  while (isoWeek <= d) {
    // Doing a very simple walk to get the week number.
    setDate(isoWeek, getDate(isoWeek) + 7);
    n++;
  }
  return n;
}

module.exports = getWeekNumber;