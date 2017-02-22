'use strict';

var classChecks = require('../../common/var/classChecks'),
    getRangeMemberPrimitiveValue = require('./getRangeMemberPrimitiveValue');

var isDate = classChecks.isDate;

function cloneRangeMember(m) {
  if (isDate(m)) {
    return new Date(m.getTime());
  } else {
    return getRangeMemberPrimitiveValue(m);
  }
}

module.exports = cloneRangeMember;