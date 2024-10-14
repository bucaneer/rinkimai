/**
 * Copyright 2024 Justas Lavišius <bucaneer@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

'use strict';

var map;
var geojson;
var content = {};
var cur_style = "theme_lrecon";
var cur_area;
var cur_marker;
var absolute_values = false;
var election = "summary";
var id_layer_map = {};
var election_input;
var absolute_values_input;
var compass_cloud = {};
import { polyline } from './polyline.min.js';

const base_style = {
  "weight": 1,
  "color": getThemeColor("grey"),
  "opacity": 0.5,
  "fillColor": getThemeColor("grey"),
  "fillOpacity": 0.6,
};

const value_color_keys = {
  "lrecon": ["l-econ", "r-econ"],
  "galtan": ["gal", "tan"],
};

const value_labels = {
  "lrecon": ["Reguliuojama rinka", "Laisva rinka"],
  "galtan": ["Asmens pasirinkimo laisvė", "Konservatyvumas ir tradicija"],
};

const absolute_relative_themes = [
  "theme_lrecon",
  "theme_galtan",
  "theme_compass",
];

const skip_keys = [
  "TURNOUT",
  "VOTERS",
  "summary",
  "bias",
  "top",
];

const election_options = [
  { value: "summary", label: "pagal rinkimų svertinį vidurkį" },
  { value: "2016_LRS", label: "2016 m. Seimo rinkimuose" },
  { value: "2019_EP", label: "2019 m. EP rinkimuose" },
  { value: "2020_LRS", label: "2020 m. Seimo rinkimuose" },
  { value: "2024_EP", label: "2024 m. EP rinkimuose" },
  { value: "2024_LRS", label: "2024 m. Seimo rinkimuose" },
];

const election_labels = {
  "summary": "Vidurkis",
  "2016_LRS": "2016 Seimo",
  "2019_EP": "2019 EP",
  "2020_LRS": "2020 Seimo",
  "2024_EP": "2024 EP",
  "2024_LRS": "2024 Seimo",
};

const absolute_values_options = [
  { value: false, label: "santykinę",  description: "lyginant su vidutine apylinke" },
  { value: true,  label: "absoliučią", description: "lyginant su skalės centru" },
];

const ABSOLUTE_MEAN =  0;
const ABSOLUTE_MIN  = -2;
const ABSOLUTE_MAX  =  2;

const default_state = {
  apl: undefined,
  election: "summary",
  abs: false,
  style: "theme_lrecon",
  z: null,
  c: null,
};

zingchart.i18n.lt = mergeDeep(zingchart.i18n.en_us, {
  'decimals-separator': ',',
  'thousands-separator': '',
});

const bias_style = function(category, prop_key, __election) {
  let min_hsl, max_hsl;
  if (category == "votes") {
    max_hsl = splitHSL(getThemeColor(prop_key));
    min_hsl = splitHSL(getThemeComplementaryColor(prop_key));
  } else if (category == "values") {
    let color_keys = value_color_keys[prop_key];
    min_hsl = splitHSL(getThemeColor(color_keys[0]));
    max_hsl = splitHSL(getThemeColor(color_keys[1]));
  }

  return (f) => {
    if (!content) return base_style;
    const id = f.properties.index || undefined;
    const props = content[id] || {};
    const style = JSON.parse(JSON.stringify(base_style));
    if (!props[category]) return style;
    
    let _election = (__election === undefined)
      ? election
      : __election;
    const totals = content.sds[category][prop_key][_election];
    let value, mean, min, max, hue, saturation, limit, limit_l;
    let raw_value = props[category][prop_key][_election].value;
    if (absolute_relative_themes.includes(cur_style) && absolute_values) {
      value = raw_value == null
        ? raw_value
        : raw_value - ABSOLUTE_MEAN;
      mean = ABSOLUTE_MEAN;
      min = ABSOLUTE_MIN;
      max = ABSOLUTE_MAX;
    } else {
      value = raw_value == null
        ? raw_value
        : props[category][prop_key][_election].value - totals.mean;
      mean = totals.mean;
      min = totals.min;
      max = totals.max;
    }
    
    if (value == null) {
      hue = min_hsl[0];
      saturation = min_hsl[1];
      limit = 1;
      limit_l = 100;
    } else if (value <= 0) {
      hue = min_hsl[0];
      saturation = min_hsl[1];
      limit = Math.abs(mean - min);
      limit_l = min_hsl[2];
    } else if (value > 0) {
      hue = max_hsl[0];
      saturation = max_hsl[1];
      limit = Math.abs(max - mean);
      limit_l = max_hsl[2];
    }

    let lightness = 100 - cubed(Math.min(1, (Math.abs(value) / limit))) * (100 - limit_l);
    style["color"] = joinHSL(hue, saturation, lightness);
    style["fillColor"] = style["color"];
    return style;
  };
};

const max_bias_style = function(category) {
  return f => {
    if (!content) return base_style;
    const id = f.properties.index || undefined;
    const props = content[id] || {};
    const style = JSON.parse(JSON.stringify(base_style));
    if (!props[category]) return style;
    let key, bias, totals;
    key = getMaxKey(id, category, election, "bias");
    totals = content.sds[category][key][election];
    bias = (props[category][key][election].value - totals.mean) / totals.sd;
    const max_value = bias <= 0
      ? (totals.min - totals.mean) / totals.sd
      : (totals.max - totals.mean) / totals.sd;

    let color_key;
    if (category == "votes") {
      color_key = key;
    } else if (category == "values") {
      color_key = value_color_keys[key][bias <= 0 ? 0 : 1];
    }
    style["color"] = getThemeColor(color_key);
    style["fillColor"] = style["color"];
    return style;
  };
};

const top_style = function(category) {
  return f => {
    if (!content) return base_style;
    const id = f.properties.index || undefined;
    const props = content[id] || {};
    const style = JSON.parse(JSON.stringify(base_style));
    if (!props[category]) return style;
    let key, value, totals;
    key = getMaxKey(id, category, election, "top");
    totals = content.sds[category][key][election];
    value = props[category][key][election].value;
    const max_value = totals.max;

    let color_key;
    if (category == "votes") {
      color_key = key;
    } else if (category == "values") {
      color_key = value_color_keys[key][bias <= 0 ? 0 : 1];
    }
    style["color"] = getThemeColor(color_key);
    style["fillColor"] = style["color"];
    return style;
  };
};

const compass_style = function() {
  return (f) => {
    if (!content) return base_style;
    const id = f.properties.index || undefined;
    const props = content[id] || {};
    const style = JSON.parse(JSON.stringify(base_style));
    if (!props['values']) return style;
    let lr_tot = content.sds.values.lrecon[election];
    let gt_tot = content.sds.values.galtan[election];
    const lrecon = absolute_values
      ? props.values.lrecon[election].value - ABSOLUTE_MEAN
      : props.values.lrecon[election].value - lr_tot.mean;
    const galtan = absolute_values
      ? props.values.galtan[election].value - ABSOLUTE_MEAN
      : props.values.galtan[election].value - gt_tot.mean;
    let hue, sat, max_l, limit;

    let lr_min_lim, lr_max_lim, gt_min_lim, gt_max_lim;
    if (absolute_values) {
      lr_min_lim = gt_min_lim = ABSOLUTE_MEAN - ABSOLUTE_MIN;
      lr_max_lim = gt_max_lim = ABSOLUTE_MAX  - ABSOLUTE_MEAN;
    } else {
      lr_min_lim = lr_tot.mean - lr_tot.min;
      lr_max_lim = lr_tot.max  - lr_tot.mean;
      gt_min_lim = gt_tot.mean - gt_tot.min;
      gt_max_lim = gt_tot.max  - gt_tot.mean;
    }
    
    if (     lrecon <= 0 && galtan <= 0) {
      [hue, sat, max_l] = splitHSL(getThemeColor("lgal"));
      limit = Math.sqrt(lr_min_lim**2 + gt_min_lim**2);
    } else if (lrecon >  0 && galtan <= 0) {
      [hue, sat, max_l] = splitHSL(getThemeColor("rgal"));
      limit = Math.sqrt(lr_max_lim**2 + gt_min_lim**2);
    } else if (lrecon <= 0 && galtan >  0) {
      [hue, sat, max_l] = splitHSL(getThemeColor("ltan"));
      limit = Math.sqrt(lr_min_lim**2 + gt_max_lim**2);
    } else if (lrecon >  0 && galtan >  0) {
      [hue, sat, max_l] = splitHSL(getThemeColor("rtan"));
      limit = Math.sqrt(lr_max_lim**2 + gt_max_lim**2);
    }
    let color_l = 100 - cubed(Math.min(1, Math.sqrt(lrecon**2 + galtan**2)/limit)) * (100 - max_l);
    style["color"] = joinHSL(hue, sat, color_l);
    style["fillColor"] = style["color"];
    return style;
  };
};

const cubed = (x) => 1 - Math.pow(1 - x, 3);

function splitHSL (color_string) {
  return color_string
    .replace(/[hsl%\(\)]/g, '')
    .split(/,\s*/);
}

function joinHSL(hue, saturation, lightness) {
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function HSLtoRGB(hue, saturation, lightness) {
  let h = parseFloat(hue);
  let s = parseFloat(saturation) / 100;
  let l = parseFloat(lightness) / 100;
  let a=s*Math.min(l,1-l);
  let f= (n,k=(n+h/30)%12) => l - a*Math.max(Math.min(k-3,9-k,1),-1);
  let output = [f(0),f(8),f(4)]
    .map(x => {
      return Math.round(x*255).toString(16).padStart(2, '0');
    })
    .join('');
  return '#' + output;
}

function getThemeColor(name) {
  let style = window.getComputedStyle(document.querySelector(':root'));
  return style.getPropertyValue('--c-' + name).trim();
}

function getThemeComplementaryColor(name) {
  let parts = splitHSL(getThemeColor(name));
  return joinHSL(
    (parseInt(parts[0]) + 180) % 360,
    parseInt(parts[1]) > 30 ? 20 : 10,
    75
  );
}

function getThemeTitle(name) {
  let node = document.querySelector(`label[for="${name}"]`);
  return node
    ? node.title || node.innerText
    : name;
}

function getColorSwab(color) {
  return `<span class="color-swab" style="--theme-color: ${color}"></span>`;
}

function displayFloat(num) {
  return parseFloat(num.toFixed(2)).toLocaleString("lt");
}

function getTooltip(layer) {
  const props = (layer.feature || {}).properties || {};
  const id = props.index || null;
  const title = `<strong>${getAreaTitle(layer)}</strong>`;
  if (!id || !content || !content[id]) return title;
  const data = content[id];
  return `${title}<br>${getAreaDetail(id)}`;
}

function getAreaTitle(layer) {
  const props = (layer.feature || {}).properties || {};
  return `${props['pavad']} (${props['sav_pav']})`;
}

function biasDetail (data, category, key) {
  const ref_val = absolute_values
    ? ABSOLUTE_MEAN
    : content.sds[category][key][election].mean;
  const val = absolute_values
    ? data.values[key][election].value - ABSOLUTE_MEAN
    : data.values[key][election].value - ref_val;
  let label;
  if (category == "votes") {
    label = key;
  } else if (category == "values") {
    label = value_labels[key][val <= 0 ? 0 : 1];
  }
  const sign = val > 0
    ? '+'
    : '';
  return `${label} (${sign}${displayFloat(val)} balo nuo ${displayFloat(ref_val)})`;
}

function partyDetail (id, party) {
  const data = content[id];
  const ref_val = absolute_values
    ? 0
    : content
  const totals = content.sds.votes[party][election];
  const val = data.votes[party][election].value;
  const bias = (val - totals.mean) / totals.sd;
  const sign = bias > 0
    ? '+'
    : '';
  const label = party == "TURNOUT"
    ? "Rinkėjų aktyvumas"
    : party;
  return val == null
    ? `${label}: —`
    : `${label}: ${displayFloat(val)}% (${sign}${displayFloat(bias)} σ)`;
}

function getMaxKey (id, category, election, type) {
  if (!content || !content[id]) return;
  const data = content[id];

  if (!content[id][category][type]) {
    content[id][category][type] = {};
  }
  
  if (!content[id][category][type][election]) {
    let value, key;
    Object.keys(data[category]).forEach(k => {
      if (skip_keys.includes(k)) return;
      let totals = content.sds[category][k][election];
      let _value = type == "bias"
        ? (data[category][k][election].value - totals.mean) / totals.sd
        : data[category][k][election].value;
      if (value === undefined || _value > value) {
        value = _value;
        key = k;
      }
    });
    content[id][category][type][election] = key;
  };

  return content[id][category][type][election];
}

function maxBiasDetail (id, category) {
  const key = getMaxKey(id, category, election, "bias");
  const totals = content.sds[category][key][election];
  let bias = (content[id][category][key][election].value - totals.mean) / totals.sd;
  let label;
  if (category == "votes") {
    label = key;
  } else if (category == "values") {
    label = value_labels[key][bias <= 0 ? 0 : 1];
    bias = Math.abs(bias);
  }
  const sign = bias > 0
    ? '+'
    : '';
  return `${label} (${sign}${displayFloat(bias)} σ)`;
}

function topPartyDetail (id) {
  const party = getMaxKey(id, "votes", election, "top");
  return partyDetail(id, party);
}

function getAreaDetail(id) {
  let val, label, sign, output;
  const data = content[id];

  const theme_key = cur_style.substring(6);

  switch (cur_style) {
    case "theme_lrecon":
    case "theme_galtan":
      output = biasDetail(data, "values", theme_key);
    break;
    case "theme_compass":
      let lr_ref = absolute_values
        ? ABSOLUTE_MEAN
        : content.sds.values.lrecon[election].mean;
      let gt_ref = absolute_values
        ? ABSOLUTE_MEAN
        : content.sds.values.galtan[election].mean;
      let lrecon = data.values.lrecon[election].value - lr_ref;
      let galtan = data.values.galtan[election].value - gt_ref;
      let label1 = galtan <= 0
        ? "Liberali"
        : "Konservatyvi";
      let label2 = lrecon <= 0
        ? "kairė"
        : "dešinė";
      label = `${label1} ${label2}`;
      val = Math.sqrt(lrecon**2 + galtan**2);
      output = `${label} (${displayFloat(val)} balo)`;
    break;
    case "theme_max_bias_party":
      output = maxBiasDetail(id, "votes");
    break;
    case "theme_max_bias_value":
      output = maxBiasDetail(id, "values");
    break;
    case "theme_top_party":
      output = topPartyDetail(id);
    break;
    default:
      output = partyDetail(id, theme_key);
    break;
  }

  return output;
}

const theme_descriptions = {
  "party": "<p>Žemėlapis rodo <strong>%PARTY_ABBR%</strong> populiarumą %ELECTION%.</p>" +
    "<p>Partijos spalva %PARTY_COLOR% rodo didesnį palaikymą nei vidutinėje apylinkėje, o komplementari spalva %COMPLEMENTARY_COLOR% – mažesnį.</p>" +
    "<p>Pasirinktoje apylinkėje nurodomas partijos populiarumas balsų procentais bei standartiniais nuokrypiais (σ) nuo vidutinės apylinkės.</p>",

  "turnout": "<p>Žemėlapis rodo rinkėjų aktyvumą %ELECTION%.</p>" +
    "<p>Pagrindinė spalva %MAIN_COLOR% rodo didesnį aktyvumą nei vidutinėje apylinkėje, o komplementari spalva %COMPLEMENTARY_COLOR% – mažesnį.</p>" +
    "<p>Pasirinktoje apylinkėje nurodomas rinkėjų aktyvumas procentais bei standartiniais nuokrypiais (σ) nuo vidutinės apylinkės.</p>",
  
  "value": "<p>Žemėlapis rodo rinkėjų poziciją kategorijoje „%VALUE_TITLE%“ %ELECTION%.</p>" +
    "<p>Pozicija vertinama balais nuo -2 (&NoBreak;<strong>%VALUE_MIN%</strong> %MIN_COLOR%&NoBreak;) iki +2 (&NoBreak;<strong>%VALUE_MAX%</strong> %MAX_COLOR%&NoBreak;).</p>" +
    "<p>Balai apskaičiuoti pagal partijų atsakymus projekto <a href=\"https://www.manobalsas.lt\">Mano balsas</a> anketose bei rinkimų rezultatus. Atvaizduojama pagal %ABSOLUTE_VALUES% skalę, t.y. %ABSOLUTE_VALUES_DESCRIPTION%.</p>",
  
  "compass": "<p>Žemėlapis rodo rinkėjų poziciją politinio kompaso ketvirčiuose: <strong>%Q1%</strong> %Q1_COLOR%, <strong>%Q2%</strong> %Q2_COLOR%, <strong>%Q3%</strong> %Q3_COLOR% ir <strong>%Q4%</strong> %Q4_COLOR% %ELECTION%.</p>" +
    "<p>Pozicijos nuotolis nuo kompaso centro vertinamas balais nuo 0 iki 4.</p>" +
    "<p>Balai apskaičiuoti pagal partijų atsakymus projekto <a href=\"https://www.manobalsas.lt\">Mano balsas</a> anketose bei rinkimų rezultatus. Atvaizduojama pagal %ABSOLUTE_VALUES% skalę, t.y. %ABSOLUTE_VALUES_DESCRIPTION%.</p>",

  "max_bias_value": "<p>Žemėlapis rodo populiariausią iš keturių politinių vertybių – <strong>%V1%</strong> %V1_COLOR%, <strong>%V2%</strong> %V2_COLOR%, <strong>%V3%</strong> %V3_COLOR% ir <strong>%V4%</strong> %V4_COLOR% %ELECTION%.</p>" +
    "<p>Vertybės populiarumas nurodomas standartiniais nuokrypiais (σ) nuo vidutinės apylinkės.</p>",

  "max_bias_party": "<p>Žemėlapis rodo partiją, kurios populiarumas labiausiai skiriasi nuo vidutinės apylinkės %ELECTION%. Tai nebūtinai yra populiariausia partija.</p>" +
    "<p>Partijos populiarumas nurodomas standartiniais nuokrypiais (σ) nuo vidutinės apylinkės.</p>",

  "top_party": "<p>Žemėlapis rodo populiariausią partiją kiekvienoje apylinkėje %ELECTION%.</p>" +
    "<p>Partijos populiarumas nurodomas balsų procentais bei standartiniais nuokrypiais (σ) nuo vidutinės apylinkės.</p>",
};

function getThemeDescription(name) {
  let base = '';
  let substitutions = {};

  const theme_key = cur_style.substring(6);
  const election_placeholder = '<span class="election-placeholder"></span>';
  const absolute_values_placeholder = '<span class="absolute-values-placeholder"></span>';
  const absolute_values_description = '<span class="absolute-values-description"></span>';

  switch (name) {
    case "theme_lrecon":
    case "theme_galtan":
      base = theme_descriptions["value"];
      substitutions = {
        VALUE_TITLE: getThemeTitle(name),
        VALUE_MIN: value_labels[theme_key][0],
        VALUE_MAX: value_labels[theme_key][1],
        MIN_COLOR: getColorSwab(getThemeColor(value_color_keys[theme_key][0])),
        MAX_COLOR: getColorSwab(getThemeColor(value_color_keys[theme_key][1])),
        ELECTION: election_placeholder,
        ABSOLUTE_VALUES: absolute_values_placeholder,
        ABSOLUTE_VALUES_DESCRIPTION: absolute_values_description,
      };
    break;
    case "theme_LSDP":
    case "theme_TS-LKD":
    case "theme_LVŽS":
    case "theme_LLRA-KŠS":
    case "theme_LS":
    case "theme_LP":
    case "theme_DSVL":
    case "theme_LT":
    case "theme_DP":
    case "theme_LRP":
    case "theme_TTS":
    case "theme_NS":
    case "theme_KS":
    case "theme_LŽP":
    case "theme_LLP":
    case "theme_TK":
    case "theme_NA":
      base = theme_descriptions["party"];
      substitutions = {
        PARTY_ABBR: theme_key,
        ELECTION: election_placeholder,
        PARTY_COLOR: getColorSwab(getThemeColor(theme_key)),
        COMPLEMENTARY_COLOR: getColorSwab(getThemeComplementaryColor(theme_key)),
      };
    break;
    case "theme_TURNOUT":
      base = theme_descriptions["turnout"];
      substitutions = {
        ELECTION: election_placeholder,
        MAIN_COLOR: getColorSwab(getThemeColor(theme_key)),
        COMPLEMENTARY_COLOR: getColorSwab(getThemeComplementaryColor(theme_key)),     
      };
    break;
    case "theme_compass":
      base = theme_descriptions["compass"];
      substitutions = {
        Q1: "Konservatyvi kairė",
        Q1_COLOR: getColorSwab(getThemeColor("ltan")),
        Q2: "Liberali kairė",
        Q2_COLOR: getColorSwab(getThemeColor("lgal")),
        Q3: "Konservatyvi dešinė",
        Q3_COLOR: getColorSwab(getThemeColor("rtan")),
        Q4: "Liberali dešinė",
        Q4_COLOR: getColorSwab(getThemeColor("rgal")),
        ELECTION: election_placeholder,
        ABSOLUTE_VALUES: absolute_values_placeholder,
        ABSOLUTE_VALUES_DESCRIPTION: absolute_values_description,
      };
    break;
    case "theme_max_bias_value":
      base = theme_descriptions["max_bias_value"];
      substitutions = {
        V1: value_labels["lrecon"][0],
        V1_COLOR: getColorSwab(getThemeColor(value_color_keys["lrecon"][0])),
        V2: value_labels["lrecon"][1],
        V2_COLOR: getColorSwab(getThemeColor(value_color_keys["lrecon"][1])),
        V3: value_labels["galtan"][0],
        V3_COLOR: getColorSwab(getThemeColor(value_color_keys["galtan"][0])),
        V4: value_labels["galtan"][1],
        V4_COLOR: getColorSwab(getThemeColor(value_color_keys["galtan"][1])),
        ELECTION: election_placeholder,
      };
    break;
    case "theme_max_bias_party":
      base = theme_descriptions["max_bias_party"];
      substitutions = {
        ELECTION: election_placeholder,
      };
    break;
    case "theme_top_party":
      base = theme_descriptions["top_party"];
      substitutions = {
        ELECTION: election_placeholder,
      };
    break;
  }

  Object.keys(substitutions).forEach(key => {
    base = base.replaceAll(`%${key}%`, substitutions[key]);
  });

  return base;
}

function updateThemeDescription() {
  const bar = document.getElementById('content-bar');
  if (!bar) return;

  const description = bar.querySelector('[data-field="theme_description"]');
  if (description) {
    description.innerHTML = getThemeDescription(cur_style);
    let election_placeholder = description.querySelector('.election-placeholder');
    if (election_placeholder) {
      election_placeholder.append(election_input);
    }

    let absolute_values_placeholder = description.querySelector('.absolute-values-placeholder');
    if (absolute_values_placeholder) {
      absolute_values_placeholder.append(absolute_values_input);
      updateAbsoluteValuesDescription();
    }
  }

  const title = bar.querySelector('[data-field="theme_title"]');
  if (title) {
    title.innerHTML = getThemeTitle(cur_style);
  }
}

function loadGeoJson(data) {
  data.features.forEach((feature, f) => {
    feature.geometry.coordinates.forEach((line, l) => {
      if (feature.geometry.type == "Polygon") {
        data.features[f].geometry.coordinates[l] = polyline.toGeoJSON(line).coordinates;
      } else if (feature.geometry.type == "MultiPolygon") {
        line.forEach((pline, p) => {
          data.features[f].geometry.coordinates[l][p] = polyline.toGeoJSON(pline).coordinates;
        });
      }
    });
  });

  geojson = L.geoJson(data,
    {
      style: base_style,
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: e => {
            layer.bringToFront();
          },
          click: e => {
            let id = feature.properties.index;
            selectArea(id, e.latlng);
          },
        });
        id_layer_map[feature.properties.index] = layer;
      }
    }
  );

  geojson.addTo(map);

  geojson.bindTooltip(getTooltip, {sticky: true});
}

function loadDataArray (data) {
  const header = data[0];
  const values = Object.keys(value_labels);
  const sds_keys = ["mean", "sd", "min", "max"];
  for (let r=1; r<data.length; r++) {
    let row = data[r];
    let apl_id = row[0];
    let is_sds = sds_keys.includes(apl_id);
    if (!content[apl_id] && !is_sds) {
      content[apl_id] = {};
    }
    for (let i=1; i<row.length; i++) {
      let field, election, category, value;
      [field, election] = header[i].split('|');
      category = values.includes(field)
        ? "values"
        : "votes";
      value = row[i] == ''
        ? null
        : parseFloat(row[i]);
      
      if (is_sds) {
        if (!content.sds) {
          content.sds = {};
        }
        if (!content.sds[category]) {
          content.sds[category] = {};
        }
        if (!content.sds[category][field]) {
          content.sds[category][field] = {};
        }
        if (!content.sds[category][field][election]) {
          content.sds[category][field][election] = {};
        }
        content.sds[category][field][election][apl_id] = value;
      } else {
        if (!content[apl_id][category]) {
          content[apl_id][category] = {};
        }
        if (!content[apl_id][category][field]) {
          content[apl_id][category][field] = {};
        }
        if (!content[apl_id][category][field][election]) {
          content[apl_id][category][field][election] = {};
        }
        content[apl_id][category][field][election]["value"] = value;
      }
    }
  }
}

function loadSummary (data) {
  Object.keys(data).forEach(apl_id => {
    if (apl_id == "sds") {
      content[apl_id] = data[apl_id];
      return;
    }
    Object.keys(data[apl_id]).forEach(category => {
      if (!content[apl_id]) {
        content[apl_id] = {};
      }
      if (!content[apl_id][category]) {
        content[apl_id][category] = {};
      }
      content[apl_id][category]["summary"] = data[apl_id][category];
    });
  });
}

function setCurStyle(new_style) {
  cur_style = new_style;
  applyHash("style", new_style);
  applyCurStyle();
  updateAreaDescription();
  let input = document.querySelector(`input[name=theme][value=${cur_style}`);
  if (input) {
    input.checked = true;
  }
}

function applyCurStyle() {
  if (!geojson) return;

  let style_def;
  const theme_key = cur_style.substring(6);
  switch (theme_key) {
    case "compass":
      style_def = compass_style();
    break;
    case "max_bias_party":
      style_def = max_bias_style("votes");
    break;
    case "max_bias_value":
      style_def = max_bias_style("values");
    break;
    case "top_party":
      style_def = top_style("votes");
    break;
    default:
      let category = Object.keys(value_labels).includes(theme_key)
        ? "values"
        : "votes";
      style_def = bias_style(category, theme_key);
    break;
  }

  geojson.setStyle(style_def);

  updateThemeDescription();
}

function setAbsoluteValues(toggle) {
  absolute_values = toggle;

  updateAbsoluteValuesDescription();
  
  if (absolute_relative_themes.includes(cur_style)) {
    applyCurStyle();
  }

  applyHash("abs", +toggle);
}

function updateAbsoluteValuesDescription() {
  document.querySelectorAll('.absolute-values-description').forEach(node => {
    node.innerText = absolute_values_options.find(e => e.value == absolute_values).description;
  });
}

function setElection(value) {
  election = value;

  applyCurStyle();
  updateAreaDescription();
  applyHash("election", value);
}

function getElectionInput() {
  const input = document.createElement('input');
  input.type = "text";
  input.name = "election";
  input.readOnly = true;
  input.classList.add('search-input');
  input.style.width = "25ch";
  
  input.value = election_options.find(e => e.value == election).label;
  autocomplete({
    input: input,
    fetch: (text, update) => {
      update(election_options.filter(e => e.value != election));
    },
    onSelect: item => {
      setElection(item.value);
      input.blur();
      input.value = item.label;
    },
    showOnFocus: true,
    disableAutoSelect: true,
  });
  input.addEventListener('wheel', event => {
    let i = election_options.findIndex(e => e.value == election);
    if (event.deltaY < 0) {
      i--;
    } else if (event.deltaY > 0) {
      i++;
    }
    if (i < 0) {
      i = election_options.length - 1;
    } else if (i >= election_options.length) {
      i = 0;
    }
    let new_item = election_options[i];
    if (!new_item) return;
    input.value = new_item.label;
    setElection(new_item.value);
    event.preventDefault();
  });
  
  return input;
}

function getAbsoluteValuesInput() {
  const input = document.createElement('input');
  input.type = "text";
  input.name = "absolute_values";
  input.readOnly = true;
  input.classList.add('search-input');
  input.style.width = "10ch";
  
  input.value = absolute_values_options.find(e => e.value == absolute_values).label;
  autocomplete({
    input: input,
    fetch: (text, update) => {
      update(absolute_values_options.filter(i => i.value != absolute_values));
    },
    onSelect: item => {
      setAbsoluteValues(!!item.value);
      input.blur();
      input.value = item.label;
    },
    showOnFocus: true,
  });
  input.addEventListener('wheel', event => {
    let i = absolute_values_options.findIndex(e => e.value == absolute_values);
    if (event.deltaY < 0) {
      i--;
    } else if (event.deltaY > 0) {
      i++;
    }
    if (i < 0) {
      i = absolute_values_options.length - 1;
    } else if (i >= absolute_values_options.length) {
      i = 0;
    }
    let new_item = absolute_values_options[i];
    if (!new_item) return;
    input.value = new_item.label;
    setAbsoluteValues(!!new_item.value);
    event.preventDefault();
  });
  
  return input;
}

function onFullInit() {
  let input = document.querySelector('input[name=theme]:checked');
  if (input && input.value) {
    cur_style = input.value;
    applyCurStyle();
    updateAreaDescription();
  }

  processURL(document.location);
  document.getElementById('overlay').style.visibility = "hidden";
}

function selectArea(id, latLng) {
  if (id === undefined) {
    cur_area = undefined;
    if (cur_marker) {
      cur_marker.remove();
      cur_marker = undefined;
    }
    applyHash("apl", undefined);
    updateAreaDescription();
    return;
  }
  if (!content || !content[id]) return;
  cur_area = id;
  let layer = id_layer_map[id];
  if (!layer) return;
  if (!cur_marker) {
    cur_marker = L.marker([0, 0]).addTo(map);
  }
  if (latLng === undefined) {
    latLng = layer.getCenter();
  }
  cur_marker.setLatLng(latLng);

  applyHash("apl", id.replaceAll(':', '-'));
  updateAreaDescription();
}

function updateAreaDescription() {
  const bar = document.getElementById('content-bar');
  if (!bar) return;

  bar.querySelectorAll('.area-description').forEach(node => {
    node.style.visibility = !!cur_area
      ? 'visible'
      : 'hidden';
  });

  const plot = bar.querySelector('#area-plot');
  if (plot) {
    let chart_config = getChartConfig();
    if (chart_config) {
      zingchart.render(chart_config);
      plot.style.visibility = 'visible';
    } else {
      plot.style.visibility = 'hidden';
    }
  }

  const title = bar.querySelector('[data-field="area_title"]');
  if (title) {
    title.innerHTML = cur_area
      ? getAreaTitle(id_layer_map[cur_area])
      : '';
  }

  const tip = bar.querySelector('[data-field="area_tip"]');
  if (tip) {
    tip.innerHTML = cur_area
      ? getAreaDetail(cur_area)
      : '';
  }
}

const chart_base_configs = {
  "global": {
    id: "area-plot",
    data: {},
    height: '400px',
    output: 'canvas',
    locale: 'lt',
    plot: {
      exact: true,
      maxTrackers: 1,
    }
  },
  "party": {
    type: "bar",
    scaleX: {
      minValue: 0,
      item: {
        wrapText: true,
      },
      itemsOverlap: true,
    },
    scaleY: {
      label: {
        text: "%",
      }
    },
    tooltip: {
      text: "%v%",
      color: '#000',
      backgroundColor: '#fff',
    },
    plotarea: {
      marginTop: 5,
    },
  },
  "compass": {
    type: "scatter",
    scaleX: {
      minValue: -2,
      maxValue:  2,
      step: 1,
      normalize: false,
      lineWidth: 0,
      tick: {
        visible: false,
      },
      item: {
        visible: false,
      },
      label: {
        text: value_labels["galtan"][0],
      },
      guide: {
        lineColor: '#eee',
      },
    },
    scaleX2: {
      used: true,
      placement: 'opposite',
      label: {
        text: value_labels["galtan"][1],
      },
      lineWidth: 0,
      tick: {
        visible: false,
      },
      item: {
        visible: false,
      },
      guide: {
        visible: false,
      },
    },
    scaleY: {
      minValue: -2,
      maxValue:  2,
      step: 1,
      lineWidth: 0,
      tick: {
        visible: false,
      },
      item: {
        visible: false,
      },
      label: {
        text: value_labels["lrecon"][0],
      },
      guide: {
        lineColor: '#eee',
      },
    },
    scaleY2: {
      used: true,
      placement: 'opposite',
      label: {
        text: value_labels["lrecon"][1],
      },
      lineWidth: 0,
      tick: {
        visible: false,
      },
      item: {
        visible: false,
      },
      guide: {
        visible: false,
      },
    },
    plotarea: {
      backgroundImage: "includes/compass.png",
      backgroundFit: "xy",
      backgroundRepeat: "no-repeat",
    },
    tooltip: {
      text: "Rinka ir valstybė: %kt <br>Visuomenė ir kultūra: %v",
      color: '#000',
      backgroundColor: '#fff',
      rules: [
        {
          visible: false,
          rule: "%data-bg > 0",
        }
      ],
    },
  }
};

function getCompassCloud(election) {
    if (!content) return [];

    if (!compass_cloud[election]) {
        compass_cloud[election] = Object.keys(content).map(apl_id => {
          if (apl_id == "sds") return;
          return  [
            content[apl_id].values.lrecon[election].value,
            content[apl_id].values.galtan[election].value
          ];
        });
    }

    return compass_cloud[election];
}

function getChartConfig() {
  if (!cur_style || !content || !cur_area || !content[cur_area]) {
    return;
  }

  let base, area;

  let theme_key = cur_style.substring(6);
  const data = content[cur_area];

  switch (cur_style) {
    case "theme_galtan":
    case "theme_lrecon":
    case "theme_compass":
    case "theme_max_bias_value":
      base = chart_base_configs["compass"];
      let color = HSLtoRGB(...splitHSL(compass_style()(id_layer_map[cur_area].feature)["color"]));
      let dot = {
        values: [[
          data.values.lrecon[election].value,
          data.values.galtan[election].value
        ]],
        "data-bg": 0,
        marker: {
          backgroundColor: color,
          borderColor: '#000',
          zIndex: 10,
        },
      };
      area = {
        scaleX: {
          markers: [
            {
              type: "line",
              range: [0+2],
            },
            {
              type: "line",
              range: [content.sds.values.lrecon[election].mean+2],
              lineStyle: 'dashed',
              lineColor: "#666",
              zIndex: 2,
            },
          ],
        },
        scaleY: {
          markers: [
            {
              type: "line",
              range: [0],
            },
            {
              type: "line",
              range: [content.sds.values.galtan[election].mean],
              lineStyle: 'dashed',
              lineColor: "#666",
              zIndex: 2,
            },
          ],
        },
        series: [
          dot,
          {
            values: getCompassCloud(election),
            marker: {
              size: 1,
              borderWidth: 0,
              backgroundColor: '#fff',
              alpha: 0.25,
            },
            "data-bg": 1,
            zIndex: 0,
          },
          dot,
        ],
      };
    break;
    default:
      if (theme_key == "max_bias_party") {
        theme_key = getMaxKey(cur_area, "votes", election, "bias");
      } else if (theme_key == "top_party") {
        theme_key = getMaxKey(cur_area, "votes", election, "top");
      }
      base = chart_base_configs["party"];
      let elections = Object.keys(data["votes"][theme_key]);
      area = {
        scaleX: {
          labels: elections.map(key => election_labels[key]),
          maxItems: elections.length,
        },
        plot: {
          styles: elections.map(key => {
            let feature = id_layer_map[cur_area].feature;
            let style_func = bias_style("votes", theme_key, key);
            let style = style_func(feature);
            return {
              backgroundColor: HSLtoRGB(...splitHSL(style['color'])),
              borderColor: getThemeColor(theme_key),
              borderWidth: 1,
            };
          }),
        },
        series: [
          {
            values: elections.map(key => data["votes"][theme_key][key]["value"]),
          },
        ],
      };
    break;
  }

  if (!base || !area) return null;

  let output = mergeDeep({}, chart_base_configs["global"], {data: base}, {data: area});

  return output;
}

function applyHash(key, value) {
  let url = new URL(document.location);
  let hash = url.hash;
  hash = hash.replace(/^#/, '');
  let elements = hash.split(';');
  let map = Object.fromEntries(elements.map(e => e.split(':')));
  map[key] = value;
  let output = [];
  Object.keys(map).forEach(k => {
    let v = map[k];
    if (v === undefined || v == default_state[k]) return;
    output.push(k + ':' + v);
  });
  url.hash = '#' + output.join(';');
  if (url.toString() !== document.location) {
    history.replaceState({}, "", url.toString());
  }
}

function processURL(url) {
  let hash = decodeURIComponent(new URL(url).hash);
  hash = hash.replace(/^#/, '');
  let elements = hash.split(';');
  let state = {...default_state};

  elements.forEach(element => {
    let parts = element.split(':');
    if (parts.length < 2) return;
    switch (parts[0]) {
      case "apl":
        state.apl = parts[1].replaceAll('-', ':');
      break;
      case "election":
        state.election = parts[1];
      break;
      case "abs":
        state.abs = !!parseInt(parts[1]);
      break;
      case "style":
        state.style = parts[1];
      break;
      case "z":
        state.z = parseFloat(parts[1]);
      break;
      case "c":
        state.c = parts[1].split(',').map(x => parseFloat(x));
      break;
    }
  });

  setCurStyle(state.style);
  setAbsoluteValues(state.abs);
  setElection(state.election);
  selectArea(state.apl);
  if (default_state.c && default_state.z) {
    setMapView(state.c, state.z);
  }
}

function setMapView(center, zoom) {
  if (!map) return;
  map.setView(center, zoom);
}

/**
 * From https://stackoverflow.com/a/34749873 by Salakar
 */
function mergeDeep(target, ...sources) {
  if (!sources.length) return target;
  const source = sources.shift();

  if (isObject(target) && isObject(source)) {
    for (const key in source) {
      if (isObject(source[key])) {
        if (!target[key]) Object.assign(target, { [key]: {} });
        mergeDeep(target[key], source[key]);
      } else {
        Object.assign(target, { [key]: source[key] });
      }
    }
  }

  return mergeDeep(target, ...sources);
}

function isObject(item) {
  return (item && typeof item === 'object' && !Array.isArray(item));
}

window.addEventListener('load', async (event) => {
  map = L.map(
    "map",
    {
      center: [55.3299, 23.9055],
      crs: L.CRS.EPSG3857,
      zoom: 8,
      zoomControl: true,
      preferCanvas: true,
      maxBounds: [[56.97,20.36], [53.23,27.60]],
      zoomDelta: 0.5,
      zoomSnap: 0.5,
    }
  );
  L.control.scale().addTo(map);
  const osm_layer = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      "attribution": "© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap contributors</a>",
      "detectRetina": false,
      "maxNativeZoom": 18,
      "maxZoom": 18,
      "minZoom": 0,
      "noWrap": false,
      "opacity": 1,
      "subdomains": "abc",
      "tms": false
    }
  ).addTo(map);
  
  map.fitBounds(
    [[56.450,20.953], [53.896,26.835]],
    {}
  );

  const map_elem = document.getElementById('map');
  map.addEventListener('click', e => {
    if (e.originalEvent.target == map_elem
      || e.originalEvent.target.matches('canvas:not(.leaflet-interactive)')
    ) {
      selectArea(undefined);
    }
  });

  map.addEventListener('zoomend', e => {
    let z = e.target.getZoom();
    if (default_state.z == null) {
      default_state.z = z;
      processURL(document.location);
    } else {
      applyHash('z', e.target.getZoom());
    }
  });

  map.addEventListener('moveend', e => {
    let center = e.target.getCenter();
    let c = Object.values(center);
    if (default_state.c == null) {
      default_state.c = c;
      processURL(document.location);
    } else {
      applyHash('c', c.map(x => x.toFixed(4)).join(','));
    }
  });
  
  let geojson_promise = fetch('2024_LRS_geo.json')
    .then(response => response.json())
    .then(data => loadGeoJson(data));

  let data_promise = fetch('data.csv')
    .then(response => response.text())
    .then(data => {
      let parsed_data = data.csvToArray({rSep:"\n"});
      loadDataArray(parsed_data);
    });

  document.querySelectorAll('input[name=theme]').forEach(node => {
    node.addEventListener('change', e => {
      setCurStyle(e.target.value);
    });
  });

  document.querySelectorAll('a[href].reset').forEach(node => {
    node.addEventListener('click', e => {
      processURL(node.href);
    });
  });

  processURL(document.location);

  election_input = getElectionInput();
  absolute_values_input = getAbsoluteValuesInput();

  await geojson_promise;
  await data_promise;

  onFullInit();
});
