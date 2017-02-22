# react-style-normalizer

> Vendor prefixing and style normalization for React

Prefixes both style names and values, when needed.

## Install

```sh
$ npm i react-style-normalizer --save
```

## Usage

```jsx
var normalize = require('react-style-normalizer')

var style = normalize({
	userSelect: 'none',// in chrome/safari it becomes WebkitUserSelect: 'none'
	display: 'flex' //on safari it becomes display: '-webkit-flex'
})

React.render(<div style={style} />, mountNode)
```

## Contributing

Use [Github issues](https://github.com/radubrehar/react-style-normalizer/issues) for feature requests and bug reports.

We actively welcome pull requests.

## License

#### MIT