'use strict';

var getExtendedDate = require('./getExtendedDate');

function createDate(d, options, forceClone) {
  return getExtendedDate(null, d, options, forceClone).date;
}

module.exports = createDate;