'use strict';

function allCharsReg(src) {
  return RegExp('[' + src + ']', 'g');
}

module.exports = allCharsReg;