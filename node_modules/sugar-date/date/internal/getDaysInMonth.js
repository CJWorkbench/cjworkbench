'use strict';

var getYear = require('./getYear'),
    getMonth = require('./getMonth'),
    callDateGet = require('../../common/internal/callDateGet');

function getDaysInMonth(d) {
  return 32 - callDateGet(new Date(getYear(d), getMonth(d), 32), 'Date');
}

module.exports = getDaysInMonth;