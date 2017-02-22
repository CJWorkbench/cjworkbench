'use strict';

var LocaleHelpers = require('../var/LocaleHelpers'),
    trim = require('../../common/internal/trim'),
    getMonth = require('./getMonth'),
    isDefined = require('../../common/internal/isDefined'),
    getNewDate = require('./getNewDate'),
    compareDay = require('./compareDay'),
    getWeekday = require('./getWeekday'),
    dateIsValid = require('./dateIsValid'),
    classChecks = require('../../common/var/classChecks'),
    compareDate = require('./compareDate');

var isString = classChecks.isString,
    English = LocaleHelpers.English;

function fullCompareDate(date, d, margin) {
  var tmp;
  if (!dateIsValid(date)) return;
  if (isString(d)) {
    d = trim(d).toLowerCase();
    switch(true) {
      case d === 'future':    return date.getTime() > getNewDate().getTime();
      case d === 'past':      return date.getTime() < getNewDate().getTime();
      case d === 'today':     return compareDay(date);
      case d === 'tomorrow':  return compareDay(date,  1);
      case d === 'yesterday': return compareDay(date, -1);
      case d === 'weekday':   return getWeekday(date) > 0 && getWeekday(date) < 6;
      case d === 'weekend':   return getWeekday(date) === 0 || getWeekday(date) === 6;

      case (isDefined(tmp = English.weekdayMap[d])):
        return getWeekday(date) === tmp;
      case (isDefined(tmp = English.monthMap[d])):
        return getMonth(date) === tmp;
    }
  }
  return compareDate(date, d, margin);
}

module.exports = fullCompareDate;