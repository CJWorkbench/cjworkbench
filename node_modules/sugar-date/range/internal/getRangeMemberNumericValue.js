'use strict';

var classChecks = require('../../common/var/classChecks');

var isString = classChecks.isString;

function getRangeMemberNumericValue(m) {
  return isString(m) ? m.charCodeAt(0) : m;
}

module.exports = getRangeMemberNumericValue;