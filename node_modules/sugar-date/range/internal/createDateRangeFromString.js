'use strict';

var Range = require('./Range'),
    DurationTextFormats = require('../var/DurationTextFormats'),
    incrementDate = require('./incrementDate'),
    getDateForRange = require('./getDateForRange'),
    namespaceAliases = require('../../common/var/namespaceAliases'),
    getDateIncrementObject = require('./getDateIncrementObject');

var sugarDate = namespaceAliases.sugarDate,
    RANGE_REG_FROM_TO = DurationTextFormats.RANGE_REG_FROM_TO,
    RANGE_REG_REAR_DURATION = DurationTextFormats.RANGE_REG_REAR_DURATION,
    RANGE_REG_FRONT_DURATION = DurationTextFormats.RANGE_REG_FRONT_DURATION;

function createDateRangeFromString(str) {
  var match, datetime, duration, dio, start, end;
  if (sugarDate.get && (match = str.match(RANGE_REG_FROM_TO))) {
    start = getDateForRange(match[1].replace('from', 'at'));
    end = sugarDate.get(start, match[2]);
    return new Range(start, end);
  }
  if (match = str.match(RANGE_REG_FRONT_DURATION)) {
    duration = match[1];
    datetime = match[2];
  }
  if (match = str.match(RANGE_REG_REAR_DURATION)) {
    datetime = match[1];
    duration = match[2];
  }
  if (datetime && duration) {
    start = getDateForRange(datetime);
    dio = getDateIncrementObject(duration);
    end = incrementDate(start, dio[0], dio[1]);
  } else {
    start = str;
  }
  return new Range(getDateForRange(start), getDateForRange(end));
}

module.exports = createDateRangeFromString;