'use strict';

var callDateGet = require('../../common/internal/callDateGet');

function getHours(d) {
  return callDateGet(d, 'Hours');
}

module.exports = getHours;