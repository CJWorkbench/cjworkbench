'use strict';

var callDateSet = require('../../common/internal/callDateSet');

function setMonth(d, val) {
  callDateSet(d, 'Month', val);
}

module.exports = setMonth;