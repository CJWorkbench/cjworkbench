'use strict';

var Range = require('../internal/Range'),
    classChecks = require('../../common/var/classChecks'),
    getDateForRange = require('../internal/getDateForRange'),
    createDateRangeFromString = require('../internal/createDateRangeFromString');

var isString = classChecks.isString;

var DateRangeConstructor = function(start, end) {
  if (arguments.length === 1 && isString(start)) {
    return createDateRangeFromString(start);
  }
  return new Range(getDateForRange(start), getDateForRange(end));
};

module.exports = DateRangeConstructor;