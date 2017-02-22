'use strict';

var isValidRangeMember = require('./isValidRangeMember');

function rangeIsValid(range) {
  return isValidRangeMember(range.start) &&
         isValidRangeMember(range.end) &&
         typeof range.start === typeof range.end;
}

module.exports = rangeIsValid;