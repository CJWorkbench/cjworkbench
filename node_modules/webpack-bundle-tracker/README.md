# webpack-bundle-tracker

[![Join the chat at https://gitter.im/owais/webpack-bundle-tracker](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/owais/webpack-bundle-tracker?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)


Spits out some stats about webpack compilation process to a file.

<br>

#### Install

```bash
npm install --save-dev webpack-bundle-tracker
```

<br>

#### Usage
```javascript
var BundleTracker  = require('webpack-bundle-tracker');
module.exports = {
        context: __dirname,
    entry: {
      app: ['./app']
    },
    
    output: {
        path: require("path").resolve('./assets/bundles/'),
        filename: "[name]-[hash].js",
        publicPath: 'http://localhost:3000/assets/bundles/',
    },
    
    plugins: [
      new BundleTracker({path: __dirname, filename: './assets/webpack-stats.json'})
    ]
}
```

`./assets/webpack-stats.json` will look like,

```json
{
  "status":"done",
  "chunks":{
   "app":[{
      "name":"app-0828904584990b611fb8.js",
      "publicPath":"http://localhost:3000/assets/bundles/app-0828904584990b611fb8.js",
      "path":"/home/user/project-root/assets/bundles/app-0828904584990b611fb8.js"
    }]
  }
}
```

In case webpack is still compiling, it'll look like,


```json
{
  "status":"compiling",
}
```



And errors will look like,
```json
{
  "status": "error",
  "file": "/path/to/file/that/caused/the/error",
  "error": "ErrorName", 
  "message": "ErrorMessage"
}
```

`ErrorMessage` shows the line and column that caused the error.



And in case `logTime` option is set to `true`, the output will look like,
```
{
  "status":"done",
  "chunks":{
   "app":[{
      "name":"app-0828904584990b611fb8.js",
      "publicPath":"http://localhost:3000/assets/bundles/app-0828904584990b611fb8.js",
      "path":"/home/user/project-root/assets/bundles/app-0828904584990b611fb8.js"
    }]
  },
  "startTime":1440535322138,
  "endTime":1440535326804
}
```



By default, the output JSON will not be indented. To increase readability, you can use the `indent`
option to make the output legible. By default it is off. The value that is set here will be directly
passed to the `space` parameter in `JSON.stringify`. More information can be found here:
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify
