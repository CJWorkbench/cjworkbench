'use strict';

var callDateGet = require('../../common/internal/callDateGet');

function getMonth(d) {
  return callDateGet(d, 'Month');
}

module.exports = getMonth;