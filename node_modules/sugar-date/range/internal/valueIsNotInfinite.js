'use strict';

function valueIsNotInfinite(m) {
  return m !== -Infinity && m !== Infinity;
}

module.exports = valueIsNotInfinite;