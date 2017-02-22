'use strict';

var mathAliases = require('./mathAliases');

var ceil = mathAliases.ceil,
    floor = mathAliases.floor;

var trunc = Math.trunc || function(n) {
  if (n === 0 || !isFinite(n)) return n;
  return n < 0 ? ceil(n) : floor(n);
};

module.exports = trunc;