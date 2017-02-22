'use strict';

var callDateSet = require('../../common/internal/callDateSet');

function setYear(d, val) {
  callDateSet(d, 'FullYear', val);
}

module.exports = setYear;