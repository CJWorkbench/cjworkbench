export const PopperSameWidth = {
  // https://codesandbox.io/s/bitter-sky-pe3z9?file=/src/index.js
  name: 'sameWidth',
  enabled: true,
  phase: 'beforeWrite',
  requires: ['computeStyles'],
  fn: ({ state }) => {
    state.styles.popper.width = `${state.rects.reference.width}px`
  },
  effect: ({ state }) => {
    // So the first computation picks the right x value
    state.elements.popper.style.width = `${state.elements.reference.offsetWidth}px`
  }
}
