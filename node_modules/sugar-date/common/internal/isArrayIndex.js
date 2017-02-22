'use strict';

function isArrayIndex(n) {
  return n >>> 0 == n && n != 0xFFFFFFFF;
}

module.exports = isArrayIndex;