'use strict';

var valueIsNotInfinite = require('./valueIsNotInfinite'),
    getRangeMemberPrimitiveValue = require('./getRangeMemberPrimitiveValue');

function isValidRangeMember(m) {
  var val = getRangeMemberPrimitiveValue(m);
  return (!!val || val === 0) && valueIsNotInfinite(m);
}

module.exports = isValidRangeMember;