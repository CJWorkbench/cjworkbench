'use strict';

var callDateGet = require('../../common/internal/callDateGet');

function getWeekday(d) {
  return callDateGet(d, 'Day');
}

module.exports = getWeekday;