import * as d3 from "d3";
import saveSvgAsPng from 'save-svg-as-png';

function _getNode(className) {
  var chartNode = null;
  var chartOuterNode = document.getElementsByClassName(className)[0];
  if (chartOuterNode) {
    var chart = chartOuterNode.getElementsByClassName("chartbuilder-svg")[0];
    return chart;
  }
  return false;
}

function _addIDsForIllustrator(node) {
  var chart = d3.select(node);
  var classAttr = "";

  chart
    .attr("id","chartbuilder-export")
    .selectAll("g")
    .attr("id",function(d,i){
      try {
        classAttr = this.getAttribute("class").split(" ");
        return classAttr.join("::") + (classAttr == "tick" ? "::" + this.textContent : "");
      }
      catch(e) {
        return null;
      }
    });
  return chart.node();
}

function _makeFilename(extension) {
  var filename = this.props.data.reduce(function(a, b, i) {
    if (a.length === 0) {
      return b.name;
    } else {
      return [a, b.name].join("_");
    }
  }, this.props.metadata.title);
  return [
    (filename + "_chartbuilder").replace(/\s/g, "_"),
    extension
  ].join(".");
}

function _autoClickDownload(filename, href) {
  var a = document.createElement('a');
  a.download = filename;
  a.href = href;
  document.body.appendChild(a);
  a.addEventListener("click", function(e) {
    a.parentNode.removeChild(a);
  });
  a.click();
}

function downloadPNG(className, title) {
  var title = title;
  if (!title) {
    title = 'export';
  }
  var filename = title + '.png';
  var node = _getNode(className);
  saveSvgAsPng.saveSvgAsPng(node, filename, { scale: 2.0 });
}

function downloadSVG(className, title) {
  if (!filename) {
    filename = 'export'
  }
  var filename = filename + '.svg';
  var node = _getNode(className);
  var chart = _addIDsForIllustrator(node);
  var autoClickDownload = _autoClickDownload;
  saveSvgAsPng.svgAsDataUri(chart, {
    cleanFontDefs: true,
    fontFamilyRemap: {
      "Khula-Light": "Khula Light",
      "Khula-Regular": "Khula",
    }
  }, function(uri) {
    autoClickDownload(filename, uri);
  });
}

function downloadJSON(model) {
  json_string = JSON.stringify({
    chartProps: model.chartProps,
    metadata: model.metadata
  }, null, "\t")

  var filename = this._makeFilename("json");
  var href = "data:text/json;charset=utf-8," + encodeURIComponent(json_string);
  this._autoClickDownload(filename, href);
}

export {downloadPNG, downloadSVG, downloadJSON}
