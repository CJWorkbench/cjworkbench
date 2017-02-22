'use strict';

var proto = Element.prototype

var nativeMatches = proto.matches ||
  proto.mozMatchesSelector ||
  proto.msMatchesSelector ||
  proto.oMatchesSelector ||
  proto.webkitMatchesSelector

module.exports = nativeMatches
