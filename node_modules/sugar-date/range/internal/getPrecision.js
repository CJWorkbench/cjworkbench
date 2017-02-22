'use strict';

var periodSplit = require('../../common/internal/periodSplit');

function getPrecision(n) {
  var split = periodSplit(n.toString());
  return split[1] ? split[1].length : 0;
}

module.exports = getPrecision;