'use strict';

var callDateGet = require('../../common/internal/callDateGet');

function getDate(d) {
  return callDateGet(d, 'Date');
}

module.exports = getDate;