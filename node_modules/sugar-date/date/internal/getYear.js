'use strict';

var callDateGet = require('../../common/internal/callDateGet');

function getYear(d) {
  return callDateGet(d, 'FullYear');
}

module.exports = getYear;