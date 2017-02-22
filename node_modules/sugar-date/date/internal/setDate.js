'use strict';

var callDateSet = require('../../common/internal/callDateSet');

function setDate(d, val) {
  callDateSet(d, 'Date', val);
}

module.exports = setDate;