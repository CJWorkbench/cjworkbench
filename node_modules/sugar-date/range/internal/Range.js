'use strict';

var cloneRangeMember = require('./cloneRangeMember');

function Range(start, end) {
  this.start = cloneRangeMember(start);
  this.end   = cloneRangeMember(end);
}

module.exports = Range;