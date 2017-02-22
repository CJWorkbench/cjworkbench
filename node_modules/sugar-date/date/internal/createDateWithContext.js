'use strict';

var getExtendedDate = require('./getExtendedDate');

function createDateWithContext(contextDate, d, options, forceClone) {
  return getExtendedDate(contextDate, d, options, forceClone).date;
}

module.exports = createDateWithContext;