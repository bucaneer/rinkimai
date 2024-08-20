#!/usr/bin/env python3

"""
Copyright 2024 Justas Lavišius <bucaneer@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import numpy as np
import urllib
import json
import shapefile as shpf
import shapely as shpl
import pandas as pd
import re
from time import time
import geopandas as gpd
import csv
import polyline
from datetime import date, timedelta

elections = {
  "2016_LRS": "2016 m. LR Seimo rinkimai",
  "2019_ST": "2019 m. Savivaldybių tarybų rinkimai",
  "2019_EP": "2019 m. Europos Parlamento rinkimai",
  "2020_LRS": "2020 m. LR Seimo rinkimai",
  "2023_ST": "2023 m. Savivaldybių tarybų rinkimai",
  "2024_EP": "2024 m. Europos Parlamento rinkimai",
  "2024_LRS": "2024 m. LR Seimo rinkimai",
}

# https://www.vrk.lt/rinkimu-teritoriju-gis-duomenys
shape_paths = {
  "2016_LRS": "../Apylinkiu_ribos_2016/apylinkes.shp",
  "2019_ST": "../2019SAV_apylinkes/apylinkes.shp",
  "2019_EP": "../2019_PR_REF_EP_apylinkes/apylinkes.shp",
  "2020_LRS": "../Apylinkės2020/Apylinkės_2020.shp",
  "2023_ST": "../202303_savivaldybiu_tarybu_ir_meru/apylinkes.shp",
  "2024_EP": "../Seimo_apylinkiu_apygardu_ribos_2024/apylinkes.shp",
  "2024_LRS": "../Seimo_apylinkiu_apygardu_ribos_2024/apylinkes.shp",
}

# https://open-data-ls-osp-sdg.hub.arcgis.com/datasets/ff7b85eaf2e64032bdb564f878026a7c_21/about
pop_path = "../gyventojai 2021/Gyventoj%C5%B3_ir_b%C5%ABst%C5%B3_sura%C5%A1ymas_2021%E2%80%94_Gyventojai_(GRID_1km).shp"

id_fields = {
  "2016_LRS": ['APG_NUM', 'APL_NUM', 'APL_PAV'],
  "2019_ST": ['sav_num', 'apl_num', 'apl_pav'],
  "2019_EP": ['sav_num', 'apl_num', 'apl_pav'],
  "2020_LRS": ['Apg_nr', 'Apl_nr', 'Apl_pav'],
  "2023_ST": ['apg_nr', 'apl_nr', 'pavad'],
  "2024_EP": ['sav_nr', 'apl_nr', 'pavad'],
  "2024_LRS": ['apg_nr', 'apl_nr', 'pavad'],
}

urls = {
  "2016_LRS": {
    "dir": "102/1/",
    "id": "1304",
  },
  "2019_ST": {
    "dir": "864/1/",
    "id": "1506",
  },
  "2019_EP": {
    "dir": "904/2/",
    "id": "1548",
  },
  "2020_LRS": {
    "dir": "1104/1/",
    "id": "1746",
  },
  "2023_ST": {
    "dir": "1304/1/",
    "id": "1922",
  },
  "2024_EP": {
    "dir": "1546/1/",
    "id": "2146",
  },
  "2024_LRS": {
    "dir": None,
    "id": None,
  },
}

name_map = {
  "2016_LRS": {
    "Tėvynės sąjunga - Lietuvos krikščionys demokratai": "TS-LKD",
    "Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "Lietuvos socialdemokratų partija": "LSDP",
    "Lietuvos Respublikos liberalų sąjūdis": "LS",
    "Antikorupcinė N. Puteikio ir K. Krivicko koalicija (Lietuvos centro partija, Lietuvos pensininkų partija)": "LCP",
    "Lietuvos lenkų rinkimų akcija-Krikščioniškų šeimų sąjunga": "LLRA-KŠS",
    "Partija Tvarka ir teisingumas": "TT",
    "Darbo partija": "DP",
    "Lietuvos laisvės sąjunga (liberalai)": "LLS",
    "Lietuvos žaliųjų partija": "LŽP",
    "Politinė partija „Lietuvos sąrašas“": "PPLS",
    "Lietuvos liaudies partija": "LLP",
    "S. Buškevičiaus ir Tautininkų koalicija „Prieš korupciją ir skurdą“ (Partija „Jaunoji Lietuva“, Tautininkų sąjunga)": "JLTS",
    "„Drąsos kelias“ politinė partija": "DK",
  },
  "2019_ST": {
    "1. Partija Tvarka ir teisingumas": "TT",
    "2. Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "4. Lietuvos socialdemokratų partija": "LSDP",
    "5. Lietuvos žaliųjų partija": "LŽP",
    "6. Tėvynės sąjunga – Lietuvos krikščionys demokratai": "TS-LKD",
    "7. Lietuvos laisvės sąjunga (liberalai)": "LLS",
    "8. Lietuvos socialdemokratų darbo partija": "LSDDP",
    "10. Lietuvos Respublikos liberalų sąjūdis": "LS",
    "12. Darbo partija": "DP",
    "13. Politinė partija Rusų aljansas": "RA",
    "16. Lietuvos krikščioniškosios demokratijos partija": "LKDP",
    "17. Lietuvos lenkų rinkimų akcija – Krikščioniškų šeimų sąjunga": "LLRA-KŠS",
    "18. Lietuvos centro partija": "LCP",
    "22. Lietuvių tautininkų ir respublikonų sąjunga": "LTRS",
  },
  "2019_EP": {
    "5. Tėvynės sąjunga - Lietuvos krikščionys demokratai": "TS-LKD",
    "4. Lietuvos socialdemokratų partija": "LSDP",
    "2. Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "9. Darbo partija": "DP",
    "16. Lietuvos Respublikos liberalų sąjūdis": "LS",
    "13. Visuomeninis rinkimų komitetas „Aušros Maldeikienės traukinys“": "AMT",
    "8. „Valdemaro Tomaševskio blokas“ – Krikščioniškų šeimų sąjungos ir Rusų aljanso koalicija": "VTB",
    "7. Lietuvos centro partija": "LCP",
    "1. Visuomeninis rinkimų komitetas „Prezidento Rolando Pakso judėjimas“": "RPJ",
    "12. Visuomeninis rinkimų komitetas „Vytautas Radžvilas: susigrąžinkime valstybę!“": "VRSV",
    "17. Partija Tvarka ir teisingumas": "TT",
    "11. Lietuvos socialdemokratų darbo partija": "LSDDP",
    "3. Lietuvos žaliųjų partija": "LŽP",
    "14. Lietuvos laisvės sąjunga (liberalai)": "LLS",
    "10. Visuomeninis rinkimų komitetas „Stipri Lietuva vieningoje Europoje“": "SLVE",
    "6. Visuomeninis rinkimų komitetas „Lemiamas šuolis“": "LŠ",
  },
  "2020_LRS": {
    "5. Tėvynės sąjunga – Lietuvos krikščionys demokratai": "TS-LKD",
    "3. Laisvės partija": "LP",
    "13. Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "17. Lietuvos socialdemokratų partija": "LSDP",
    "9. Lietuvos socialdemokratų darbo partija": "LSDDP",
    "12. Lietuvos Respublikos liberalų sąjūdis": "LS",
    "6. Centro partija - tautininkai": "CP-T",
    "8. Lietuvos lenkų rinkimų akcija - Krikščioniškų šeimų sąjunga": "LLRA-KŠS",
    "7. Nacionalinis susivienijimas": "NS",
    "2. Partija „Laisvė ir teisingumas“": "LT",
    "16. Darbo partija": "DP",
    "14. Lietuvos žaliųjų partija": "LŽP",
    "4. Lietuvos liaudies partija": "LLP",
    "S. Buškevičiaus ir Tautininkų koalicija „Prieš korupciją ir skurdą“ (Partija „Jaunoji Lietuva“, Tautininkų sąjunga)": "JLTS",
    "1. „Drąsos kelias“ politinė partija": "DK",
    "11. Partija LIETUVA – VISŲ": "LV",
    "15. Krikščionių sąjunga": "KS",
    "10. KARTŲ SOLIDARUMO SĄJUNGA - SANTALKA LIETUVAI": "KSS-SL",
  },
  "2023_ST": {
    "1. Lietuvos lenkų rinkimų akcija-Krikščioniškų šeimų sąjunga": "LLRA-KŠS",
    "2. Partija „Jaunoji Lietuva“": "JL",
    "3. Lietuvos žaliųjų partija": "LŽP",
    "4. Krikščionių sąjunga": "KS",
    "5. Lietuvos socialdemokratų partija": "LSDP",
    "6. Žemaičių partija": "ŽP",
    "7. Demokratų sąjunga „Vardan Lietuvos“": "DSVL",
    "8. Darbo partija": "DP",
    "9. Tėvynės sąjunga-Lietuvos krikščionys demokratai": "TS-LKD",
    "10. Lietuvos regionų partija": "LRP",
    "11. Liberalų sąjūdis": "LS",
    "12. Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "13. Laisvės partija": "LP",
    "14. Tautos ir teisingumo sąjunga (centristai, tautininkai)": "TTS",
    "17. Nacionalinis susivienijimas": "NS",
    "18. Partija „Laisvė ir teisingumas“": "LT",
  },
  "2024_EP": {
    "1. Laisvės partija": "LP",
    "2. Lietuvos socialdemokratų partija": "LSDP",
    "3. Darbo partija": "DP",
    "4. Lietuvos regionų partija": "LRP",
    "5. Lietuvos valstiečių ir žaliųjų sąjunga": "LVŽS",
    "6. Lietuvos lenkų rinkimų akcija-Krikščioniškų šeimų sąjunga": "LLRA-KŠS",
    "7. Lietuvos žaliųjų partija": "LŽP",
    "8. Tautos ir teisingumo sąjunga (centristai, tautininkai)": "TTS",
    "9. Liberalų sąjūdis": "LS",
    "10. Taikos koalicija (Lietuvos krikščioniškosios demokratijos partija, Žemaičių partija)": "TK",
    "11. Partija „Laisvė ir teisingumas“": "LT",
    "12. Krikščionių sąjunga": "KS",
    "13. Demokratų sąjunga „Vardan Lietuvos“": "DSVL",
    "14. Tėvynės sąjunga-Lietuvos krikščionys demokratai": "TS-LKD",
    "15. Nacionalinis susivienijimas": "NS",
  },
  "2024_LRS": {},
}

party_alias = {
  "LSDP": {},
  "TS-LKD": {},
  "LVŽS": {},
  "LRP": {
    "2020_LRS": ["LSDDP"],
    "2019_EP": ["LSDDP"],
    "2019_ST": ["LSDDP"],
  },
  "LS": {},
  "DSVL": {},
  "LP": {},
  "LT": {
    "2019_EP": ["TT", "LLS"],
    "2019_ST": ["TT", "LLS"],
    "2016_LRS": ["TT", "LLS"],
  },
  "LLRA-KŠS": {
    "2019_EP": ["VTB"],
  },
  "DP": {},
  "TTS": {
    "2020_LRS": ["CP-T"],
    "2019_EP": ["LCP"],
    "2019_ST": ["LCP"],
    "2016_LRS": ["LCP"],
  },
  "NS": {
    "2019_EP": ["VRSV"],
  },
  #"KS": {},
  "LŽP": {},
  "LLP": {},
  "TK": {
    "2023_ST": ["ŽP"],
    "2019_ST": ["LKDP"],
  },
}

TOTAL = 'TOTAL'
TURNOUT = 'TURNOUT'
VOTERS = 'VOTERS'

LRECON = "lrecon"
GALTAN = "galtan"
ANTIELITE = "antielite"

values = [
  LRECON,
  GALTAN,
  #ANTIELITE,
]

# https://www.chesdata.eu/ches-europe
party_values_CHES = {
  "TT": {
    2014: {
      LRECON: 4.38461542129517,
      GALTAN: 8.2857141494751,
      ANTIELITE: 7.5,
    },
    2019: {
      LRECON: 4.27272748947144,
      GALTAN: 8.6363639831543,
      ANTIELITE: 6.1999998,
    },
    2023: {
      LRECON: 4.33333,
      GALTAN: 8.0,
      ANTIELITE: 8.0,
    },
  },
  "TTS": {
    2019: {
      LRECON: 3.77777767181397,
      GALTAN: 8.625,
      ANTIELITE: 8.1999998,
    },
    2023: {
      LRECON: 4.0,
      GALTAN: 7.33333,
      ANTIELITE: 8.25,
    },
  },
  "LVŽS": {
    2014: {
      LRECON: 3.41666674613953,
      GALTAN: 6.16666650772095,
      ANTIELITE: 6.2727275,
    },
    2019: {
      LRECON: 4.0,
      GALTAN: 8.45454502105713,
      ANTIELITE: 5.2727275,
    },
    2023: {
      LRECON: 3.0,
      GALTAN: 8.75,
      ANTIELITE: 8.0,
    },
  },
  "LS": {
    2014: {
      LRECON: 8.61538505554199,
      GALTAN: 2.42857146263123,
      ANTIELITE: 1.5,
    },
    2019: {
      LRECON: 8.27272701263428,
      GALTAN: 1.90909087657929,
      ANTIELITE: 2.1818182,
    },
    2023: {
      LRECON: 6.5,
      GALTAN: 2.5,
      ANTIELITE: 2.8,
    },
  },
  "DP": {
    2014: {
      LRECON: 4.692307472229,
      GALTAN: 5.85714292526245,
      ANTIELITE: 4.6666665,
    },
    2019: {
      LRECON: 4.90909099578857,
      GALTAN: 6.09999990463257,
      ANTIELITE: 4.6999998,
    },
    2023: {
      LRECON: 4.66667,
      GALTAN: 6.66667,
      ANTIELITE: 7.2,
    },
  },
  "LŽP": {
    2019: {
      LRECON: 4.33333349227905,
      GALTAN: 3.33333325386047,
      ANTIELITE: 4.4285712,
    },
    2023: {
      LRECON: 4.66667,
      GALTAN: 3.66667,
      ANTIELITE: 4.0,
    },
  },
  "TS-LKD": {
    2014: {
      LRECON: 6.53846168518066,
      GALTAN: 7.2857141494751,
      ANTIELITE: 2.0,
    },
    2019: {
      LRECON: 6.72727251052856,
      GALTAN: 6.63636350631714,
      ANTIELITE: 2.2727273,
    },
    2023: {
      LRECON: 4.5,
      GALTAN: 4.0,
      ANTIELITE: 2.6,
    },
  },
  "LLRA-KŠS": {
    2014: {
      LRECON: 3.58333325386047,
      GALTAN: 8.85714244842529,
      ANTIELITE: 6.2727275,
    },
    2019: {
      LRECON: 2.81818175315857,
      GALTAN: 9.45454502105713,
      ANTIELITE: 5.090909,
    },
    2023: {
      LRECON: 1.66667,
      GALTAN: 9.75,
      ANTIELITE: 8.2,
    },
  },
  "LSDP": {
    2014: {
      LRECON: 3.30769228935242,
      GALTAN: 4.2857141494751,
      ANTIELITE: 1.8333334,
    },
    2019: {
      LRECON: 2.81818175315857,
      GALTAN: 2.72727274894714,
      ANTIELITE: 2.6363637,
    },
    2023: {
      LRECON: 2.5,
      GALTAN: 3.25,
      ANTIELITE: 4.8,
    },
  },
  "LP": {
    2023: {
      LRECON: 8.5,
      GALTAN: 1.5,
      ANTIELITE: 1.0,
    },
  },
  "AMT": {
    2019: {
      LRECON: 4.11111116409302,
      GALTAN: 3.11111116409302,
      ANTIELITE: 7.4444447,
    },
  },
  "DK": {
    2014: {
      LRECON: 3.33333325386047,
      GALTAN: 9.0,
      ANTIELITE: 9.416667,
    },
  },
}

# https://www.manobalsas.lt
party_values_MB = {
  "DSVL": {
    2024: {
      LRECON: 0.8571 - 2,
      GALTAN: 2 - 1.7500,
    },
  },
  "NS": {
    2020: {
      LRECON: 1.5000 - 2,
      GALTAN: 2 - 0.5000,
    },
    2024: {
      LRECON: 1.7143 - 2,
      GALTAN: 2 - 0.0000,
    },
  },
  "TS-LKD": {
    2016: {
      LRECON: 4 * 18.3889 / 28.0 - 2,
      GALTAN: 2 - 4 * 13.7593 / 32.0,
    },
    2019: {
      LRECON: 2.6000 - 2,
      GALTAN: 2 - 1.6667,
    },
    2020: {
      LRECON: 1.1667 - 2,
      GALTAN: 2 - 1.8750,
    },
    2024: {
      LRECON: 2.1429 - 2,
      GALTAN: 2 - 1.5000,
    },
  },
  "LP": {
    2020: {
      LRECON: 3.3333 - 2,
      GALTAN: 2 - 3.8750,
    },
    2024: {
      LRECON: 2.5714 - 2,
      GALTAN: 2 - 2.7500,
    },
  },
  "LŽP": {
    2016: {
      LRECON: 4 * 18.8000 / 28.0 - 2,
      GALTAN: 2 - 4 * 25.5333 / 32.0,
    },
    2019: {
      LRECON: 1.6000 - 2,
      GALTAN: 2 - 2.8333,
    },
    2020: {
      LRECON: 1.3333 - 2,
      GALTAN: 2 - 2.6250,
    },
    2024: {
      LRECON: 1.5714 - 2,
      GALTAN: 2 - 3.5000,
    },
  },
  "LSDP": {
    2016: {
      LRECON: 4 * 10.1087 / 28.0 - 2,
      GALTAN: 2 - 4 * 22.0652 / 32.0,
    },
    2019: {
      LRECON: 0.2000 - 2,
      GALTAN: 2 - 3.1429,
    },
    2020: {
      LRECON: 0.1667 - 2,
      GALTAN: 2 - 3.2500,
    },
    2024: {
      LRECON: 0.5714 - 2,
      GALTAN: 2 - 2.8750,
    },
  },
  "KS": {
    2024: {
      LRECON: 1.8571 - 2,
      GALTAN: 2 - 0.7500,
    },
  },
  "LS": {
    2016: {
      LRECON: 4 * 21.7500 / 28.0 - 2,
      GALTAN: 2 - 4 * 27.1250 / 32.0,
    },
    2019: {
      LRECON: 3.8000 - 2,
      GALTAN: 2 - 2.6000,
    },
    2020: {
      LRECON: 3.3333 - 2,
      GALTAN: 2 - 3.5000,
    },
    2024: {
      LRECON: 1.8571 - 2,
      GALTAN: 2 - 2.1429,
    },
  },
  "AMT": {
    2019: {
      LRECON: 0.6000 - 2,
      GALTAN: 2 - 2.8571,
    },
  },
  "VRSV": {
    2019: {
      LRECON: 1.0000 - 2,
      GALTAN: 2 - 0.0000,
    },
  },
  "LVŽS": {
    2016: {
      LRECON: 4 * 11.1818 / 28.0 - 2,
      GALTAN: 2 - 4 * 13.5455 / 32.0,
    },
    2019: {
      LRECON: 1.6000 - 2,
      GALTAN: 2 - 1.0000,
    },
    2020: {
      LRECON: 1.1667 - 2,
      GALTAN: 2 - 0.8750,
    },
  },
  "LSDDP": {
    2019: {
      LRECON: 1.8000 - 2,
      GALTAN: 2 - 1.7143,
    },
  },
  "LCP": {
    2016: {
      LRECON: 4 * 12.2340 / 28.0 - 2,
      GALTAN: 2 - 4 * 15.4255 / 32.0,
    },
    2019: {
      LRECON: 0.8000 - 2,
      GALTAN: 2 - 1.2857,
    },
  },
  "LLS": {
    2016: {
      LRECON: 4 * 13.7407 / 28.0 - 2,
      GALTAN: 2 - 4 * 24.5556 / 32.0,
    },
    2019: {
      LRECON: 3.0000 - 2,
      GALTAN: 2 - 2.2857,
    },
  },
  "RPJ": {
    2019: {
      LRECON: 0.0000 - 2,
      GALTAN: 2 - 0.0000,
    },
  },
  "LŠ": {
    2019: {
      LRECON: 3.4000 - 2,
      GALTAN: 2 - 3.2857,
    },
  },
  "TT": {
    2016: {
      LRECON: 4 * 15.3750 / 28.0 - 2,
      GALTAN: 2 - 4 * 16.8750 / 32.0,
    },
    2019: {
      LRECON: 1.0000 - 2,
      GALTAN: 2 - 1.0000,
    },
  },
  "LLRA-KŠS": {
    2016: {
      LRECON: 4 * 12.0000 / 28.0 - 2,
      GALTAN: 2 - 4 * 13.5000 / 32.0,
    },
    2019: {
      LRECON: 1.2000 - 2,
      GALTAN: 2 - 0.6000,
    },
  },
  "DP": {
    2016: {
      LRECON: 4 * 13.3333 / 28.0 - 2,
      GALTAN: 2 - 4 * 14.7778 / 32.0,
    },
    2019: {
      LRECON: 2.7500 - 2,
      GALTAN: 2 - 2.0000,
    },
    2020: {
      LRECON: 1.3333 - 2,
      GALTAN: 2 - 1.7500,
    },
  },
  "CP-T": {
    2020: {
      LRECON: 0.6667 - 2,
      GALTAN: 2 - 0.8750,
    },
  },
  "KSS-SL": {
    2020: {
      LRECON: 2.1667 - 2,
      GALTAN: 2 - 1.2500,
    },
  },
  "KS": {
    2020: {
      LRECON: 1.0000 - 2,
      GALTAN: 2 - 0.6250,
    },
  },
  "LT": {
    2020: {
      LRECON: 3.0000 - 2,
      GALTAN: 2 - 2.7500,
    },
  },
  "LV": {
    2020: {
      LRECON: 0.5000 - 2,
      GALTAN: 2 - 2.6250,
    },
  },
  "LLP": {
    2016: {
      LRECON: 4 * 9.0000 / 28.0 - 2,
      GALTAN: 2 - 4 * 9.5000 / 32.0,
    },
    2020: {
      LRECON: 1.5000 - 2,
      GALTAN: 2 - 0.5000,
    },
  },
  "DK": {
    2020: {
      LRECON: 0.6667 - 2,
      GALTAN: 2 - 1.2500,
    },
  },
  "PPLS": {
    2016: {
      LRECON: 4 * 15.2000 / 28.0 - 2,
      GALTAN: 2 - 4 * 21.8000 / 32.0,
    },
  },
  "JLTS": {
    2016: {
      LRECON: 4 * 16.0000 / 28.0 - 2,
      GALTAN: 2 - 4 * 14.0000 / 32.0,
    },
  },
}

election_dates = {
  "2016_LRS": date(2016, 10,  9),
  "2019_ST":  date(2019,  3,  3),
  "2019_EP":  date(2019,  5, 26),
  "2020_LRS": date(2020, 10, 11),
  "2023_ST":  date(2023,  3,  5),
  "2024_EP":  date(2024,  6,  9),
  "2024_LRS": date(2024, 10, 13),
}

DATE_HALFLIFE = timedelta(days=1461) # 4 years

def generate(
  first="2024_LRS",
  election_list=["2016_LRS", "2019_EP", "2020_LRS", "2024_EP"],
  force=False,
  combine_file="combined.json",
  csv_file="data.csv"
):
  """ Main method for generating map data """
  
  for election in election_list:
    print("Getting election results for %s..." % election)
    try:
      if force:
        raise FileNotFoundError
      with open(get_result_filename(election), 'r') as f:
        print("skip")
    except FileNotFoundError as e:
      get_results(election)

    print("Comparing shapefiles for %s -> %s..." % (election, first))
    try:
      if force:
        raise FileNotFoundError
      with open(get_compare_filename(first, election), 'r') as f:
        print("skip")
    except FileNotFoundError as e:
      compare(first, election)

    print("Mapping election results to party popularity for %s -> %s..." % (election, first))
    try:
      if force:
        raise FileNotFoundError
      with open(get_popularity_filename(first, election), 'r') as f:
        print("skip")
    except FileNotFoundError as e:
      results_to_popularity(first, election)

    print("Mapping election results to values for %s -> %s..." % (election, first))
    try:
      if force:
        raise FileNotFoundError
      with open(get_values_filename(first, election), 'r'):
        print("skip")
    except FileNotFoundError as e:
      results_to_values(first, election, party_values_MB)

  
  print("Combining popularity and values...")
  try:
    if force:
      raise FileNotFoundError
    with open(combine_file, 'r') as f:
      print("skip")
  except FileNotFoundError as e:
    combine(first, election_list, combine_file)

  print("Generating CSV data file...") 
  try:
    if force:
      raise FileNotFoundError
    with open(csv_file, 'r') as f:
      print("skip")
  except FileNotFoundError as e:
    compact_combine(combine_file, csv_file)

  print("Generating compact shapefile for %s..." % first)
  try:
    if force:
      raise FileNotFoundError
    with open(get_compact_geojson_filename(first), 'r') as f:
      print("skip")
  except FileNotFoundError as e:
    shape_to_geojson(first)
    compact_geojson(first)

  print("All done.")

def pav_to_slug (string):
  return re.sub("\\W", "", string).lower()

def process_id_field (raw):
  try:
    return str(int(raw))
  except Exception:
    return pav_to_slug(str(raw))

def sr_id (sr, election):
  return ':'.join([process_id_field(sr.record[k]) for k in id_fields[election]])

def bbox_check (sr1, sr2):
  try:
    bbox1 = sr1.shape.bbox
    bbox2 = sr2.shape.bbox
  except AttributeError as e:
    return false
  return shpf.bbox_overlap(bbox1, bbox2)

def sum_attr (_list, attr):
  return sum([x[attr] for x in _list])

def get_compare_filename (first, second):
  return "compare_%s_%s.json" % (first, second)

def compare (first, second):
  t = -time()
  first_shape = shpf.Reader(shape_paths[first])
  second_shape = shpf.Reader(shape_paths[second])
  
  pop_records = shpf.Reader(pop_path).shapeRecords()
  pop_cells = [shpl.Polygon(sr.shape.points) for sr in pop_records]
  pop_tree = shpl.STRtree(pop_cells)
  
  def estimate_pop (geom):
    pop = 0
    for i in pop_tree.query(geom):
      sr = pop_records[i]
      sr_geom = pop_cells[i]
      intersection = sr_geom.intersection(geom)
      sr_fraction = intersection.area / sr_geom.area
      pop += sr_fraction * sr.record['POP']
    return pop
  
  second_records = second_shape.shapeRecords()
  second_geoms = [shpl.from_geojson(json.dumps(sr.shape.__geo_interface__)) for sr in second_records]
  second_tree = shpl.STRtree(second_geoms)

  output = {}
  for sr1 in first_shape.shapeRecords():
    first_id = sr_id(sr1, first)
    first_geom = shpl.from_geojson(json.dumps(sr1.shape.__geo_interface__))
    first_area = first_geom.area
    first_pop = estimate_pop(first_geom)
    output[first_id] = []
    
    for i in second_tree.query(first_geom):
      sr2 = second_records[i]
      second_geom = second_geoms[i]
      second_id = sr_id(sr2, second)
      intersection = first_geom.intersection(second_geom)
      area_fraction = intersection.area / first_area if first_area else 0
      if not area_fraction:
        continue
      int_pop = estimate_pop(intersection)
      pop_fraction = int_pop / first_pop if first_pop else 0
      output[first_id].append({
        "id": second_id,
        "area_fraction": area_fraction,
        "pop_fraction": pop_fraction,
      })
      if sum_attr(output[first_id], "area_fraction") >= 1:
        break
  
  filename = get_compare_filename(first, second)
  with open(filename, "w") as f:
    json.dump(output, f, indent=2)
  return output

def list_fields ():
  output = {}
  for e in elections.keys():
    sh = shpf.Reader(shape_paths[e], encoding="utf8", encodingErrors="replace")
    output[e] = [f[0] for f in sh.fields]
  return output

def get_result_base_url (election, suffix = None):
  base = "https://www.vrk.lt/statiniai/puslapiai/rinkimai/%s" % urls[election]['dir']
  if suffix is not None:
    base += suffix
  return base

def get_result_rpl_url (election, rpl_id):
  suffix = "%s/rezultatai/rezultataiDaugmRpl%s.json" % (urls[election]['id'], rpl_id)
  return get_result_base_url(election, suffix)

def get_activity_rpg_url (election, rpg_id):
  suffix = "aktyvumas/aktyvumasRpg%s.json" % rpg_id
  return get_result_base_url(election, suffix)

def get_rpl_id_filename (election):
  return "rpl_id_map_%s.json" % election

def get_result_filename (election):
  return "results_%s.json" % election

def get_results (election):
  rpl_url = get_result_base_url(election, "rpl.json")
  with urllib.request.urlopen(rpl_url) as url:
    rpl_list = json.loads(url.read().decode())
  rpg_url = get_result_base_url(election, "rpg.json")
  with urllib.request.urlopen(rpg_url) as url:
    rpg_list = json.loads(url.read().decode())
  map_file = get_rpl_id_filename(election)
  out_file = get_result_filename(election)
  rpg_nr_map = {x['id']: x['nr'] for x in rpg_list['data']}
  rpl_id_map = {}
  output = {}
  output[TOTAL] = {}
  try:
    with open(out_file, 'r') as f:
      old_output = json.load(f)
  except FileNotFoundError:
    old_output = None
  old_output = None

  if old_output is None or TOTAL not in old_output:
    for rpl in rpl_list['data']:
      rpg_nr = rpg_nr_map[rpl['rpg_id']]
      rpl_id = "%s:%s:%s" % (rpg_nr, rpl['nr'], pav_to_slug(rpl['pav']))
      rpl_id_map[rpl_id] = rpl['id']
      with urllib.request.urlopen(get_result_rpl_url(election, rpl['id'])) as url:
        result = json.loads(url.read().decode())
      output[rpl_id] = {}
      for item in result['data']['balsai'][0:-1]:
        name = name_map[election][item['partija']] if item['partija'] in name_map[election] else item['partija']
        output[rpl_id][name] = item['proc_nuo_gal_biul']
        if name not in output[TOTAL]:
          output[TOTAL][name] = item['proc_nuo_gal_biul_lt']
    with open(map_file, 'w') as f:
      json.dump(rpl_id_map, f, indent=2, ensure_ascii=False)
    
    with open(out_file, 'w') as f:
      json.dump(output, f, indent=2, ensure_ascii=False)
  else:
    with open(map_file, 'r') as f:
      rpl_id_map = json.load(f)
    output = old_output

  if TURNOUT not in output[TOTAL]:
    rpl_id_reverse_map = {v: k for k, v in rpl_id_map.items()}
    total_voters = 0
    total_turnout = 0
    for rpl in rpl_list['data']:
      rpg_nr = rpg_nr_map[rpl['rpg_id']]
      rpl_id = "%s:%s:%s" % (rpg_nr, rpl['nr'], pav_to_slug(rpl['pav']))
      if TURNOUT in output[rpl_id]:
        continue
      try:
        with urllib.request.urlopen(get_activity_rpg_url(election, rpl['rpg_id'])) as url:
          activity = json.loads(url.read().decode())
      except urllib.error.HTTPError as e:
        print("FAIL: %s" % get_activity_rpg_url(election, rpl['rpg_id']))
        continue
      for item in activity['data'][0:-1]:
        sub_rpl_id = rpl_id_reverse_map[item['rpl_id']]
        output[sub_rpl_id][TURNOUT] = item['val_viso']
        output[sub_rpl_id][VOTERS] = item['rinkeju_skaicius']
        total_voters += int(output[sub_rpl_id][VOTERS])
        total_turnout += int(output[sub_rpl_id][VOTERS]) * float(output[sub_rpl_id][TURNOUT]) / 100.0
    output[TOTAL][VOTERS] = total_voters
    output[TOTAL][TURNOUT] = round(100 * total_turnout / total_voters, 2)

  with open(map_file, 'w') as f:
    json.dump(rpl_id_map, f, indent=2, ensure_ascii=False)
  
  with open(out_file, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
  return output

def get_popularity_filename (first, second):
  return "popularity_%s_for_%s.json" % (second, first)

def results_to_popularity (first, second):
  with open(get_compare_filename(first, second), 'r') as f:
    compare_data = json.load(f)
  with open(get_result_filename(second), 'r') as f:
    result_data = json.load(f)
  
  output = {'sds':{}}
  party_votes = {}
  for first_id, items in compare_data.items():
    if not items:
      continue
    weight_denom = sum([i["pop_fraction"] * float(result_data[i['id']][TURNOUT]) for i in items])
    apl_out = {}
    for party, alias_list in {**party_alias, **{TURNOUT: {}, VOTERS: {}}}.items():
      if second in alias_list:
        aliases = alias_list[second]
      else:
        aliases = [party]
      for item in items:
        result = result_data[item['id']]
        weight = (item['pop_fraction'] * float(result[TURNOUT])) / weight_denom
        vote_list = [float(result[alias]) for alias in aliases if alias in result]
        raw_vote = sum(vote_list) if vote_list else None
        if party not in apl_out:
          apl_out[party] = {
            "value": None,
            "bias": None,
            "bias_sd": None,
          }
        if raw_vote is not None:
          if apl_out[party]["value"] is None:
            apl_out[party]["value"] = 0
          apl_out[party]["value"] += raw_vote * weight
      if party not in party_votes:
        party_votes[party] = []
      if apl_out[party]["value"] is not None:
        party_votes[party].append(float(apl_out[party]["value"]))
    output[first_id] = apl_out
  
  party_sds = {}
  for party, votes in party_votes.items():
    if not votes:
      party_sds[party] = {
        "mean": None,
        "sd": None,
        "min": None,
        "max": None,
      }
      continue
    df = pd.DataFrame(votes)
    mean = float(df.mean().iloc[0])
    sd = float(df.std().iloc[0])
    party_sds[party] = {
      "mean": mean,
      "sd": sd,
      "min": min(votes),
      "max": max(votes),
    }
  output['sds'] = party_sds
    
  for first_id in compare_data.keys():
    if first_id not in output:
      continue
    apl_out = output[first_id]
    for party, sds in party_sds.items():
      if apl_out[party]["value"] is None:
        continue
      output[first_id][party]["bias"] = float(apl_out[party]["value"]) - sds["mean"]
      output[first_id][party]["bias_sd"] = (output[first_id][party]["bias"] / sds["sd"]) if sds["sd"] > 0 else 0
    
  filename = get_popularity_filename(first, second)
  with open(filename, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

def mean (_list):
  return sum(_list) / len(_list)

def round_floats (o, precision=4):
  if isinstance(o, float): return round(o, precision)
  if isinstance(o, dict): return {k: round_floats(v) for k, v in o.items()}
  if isinstance(o, (list, tuple)): return [round_floats(x) for x in o]
  return o

def combine (first, election_list, out_file):
  output = {}
  
  for second in election_list:
    votes_file = get_popularity_filename(first, second)
    values_file = get_values_filename(first, second)
    with open(votes_file, 'r') as f:
      votes_data = json.load(f)
    for apl_id, party_results in votes_data.items():
      
      if apl_id not in output:
        output[apl_id] = {}
      if 'votes' not in output[apl_id]:
        output[apl_id]['votes'] = {}
      for party, results in party_results.items():
        if party not in output[apl_id]['votes']:
          output[apl_id]['votes'][party] = {}
        output[apl_id]['votes'][party][second] = results

    with open(values_file, 'r') as f:
      values_data = json.load(f)
    for apl_id, value_results in values_data.items():
      if 'values' not in output[apl_id]:
        output[apl_id]['values'] = {}
      for key, value in value_results.items():
        if key not in output[apl_id]['values']:
          output[apl_id]['values'][key] = {}
        output[apl_id]['values'][key][second] = value

  value_lists = {}

  first_date = election_dates[first]
  date_weights = [2**((election_dates[e] - first_date) / DATE_HALFLIFE) for e in election_list]

  for apl_id, data in output.items():
    if apl_id == 'sds':
      continue
    
    turnout_weights = [data["votes"]["TURNOUT"][e]["value"] / 100 for e in election_list]
    raw_weights = {e: date_weights[i]*turnout_weights[i] for i, e in enumerate(election_list)}
    
    for category, category_data in data.items():
      if category not in value_lists:
        value_lists[category] = {}
      for key, election_data in category_data.items():
        if key not in value_lists[category]:
          value_lists[category][key] = []
        item_keys = tuple(election_data.values())[0].keys()
        output[apl_id][category][key]['summary'] = {}
        for k in item_keys:
          weights = []
          data_list = []
          for e in election_list:
            v = election_data[e][k]
            if v is None:
              continue
            weight = raw_weights[e]
            weights.append(weight)
            data_list.append(v * weight)
          if not data_list:
            out_val = None
          else:
            out_val = sum(data_list) / sum(weights)
          output[apl_id][category][key]['summary'][k] = out_val
        if output[apl_id][category][key]["summary"]["value"] is not None:
          value_lists[category][key].append(output[apl_id][category][key]["summary"]["value"])

  for category, category_data in value_lists.items():
    for key, data_list in category_data.items():
      if not data_list:
        output["sds"][category][key]["summary"] = {
          "mean": None,
          "sd": None,
          "min": None,
          "max": None,
        }
        continue
      df = pd.DataFrame(data_list)
      avg = float(df.mean().iloc[0])
      sd = float(df.std().iloc[0])
      output["sds"][category][key]["summary"] = {
        "mean": avg,
        "sd": sd,
        "min": min(data_list),
        "max": max(data_list),
      }

  for apl_id, data in output.items():
    if apl_id == "sds":
      continue
    for category, category_data in data.items():
      max_bias = None
      max_bias_key = None
      min_bias = None
      min_bias_key = None
      for key, election_data in category_data.items():
        if election_data["summary"]["value"] is None:
          continue
        output[apl_id][category][key]["summary"]["bias"] = election_data["summary"]["value"] - output["sds"][category][key]["summary"]["mean"]
        output[apl_id][category][key]["summary"]["bias_sd"] = output[apl_id][category][key]["summary"]["bias"] / output["sds"][category][key]["summary"]["sd"]
        if key in (TURNOUT, VOTERS):
          continue
        _bias = output[apl_id][category][key]["summary"]["bias_sd"]
        if category == "values":
          _bias = abs(_bias)
        if max_bias is None or _bias > max_bias:
          max_bias = _bias
          max_bias_key = key
        if min_bias is None or _bias < min_bias:
          min_bias = _bias
          min_bias_key = key
      output[apl_id][category]["summary"] = {
        "max_bias_key": max_bias_key,
        "min_bias_key": min_bias_key,
      }

  with open(out_file, 'w') as f:
    json.dump(round_floats(output), f, indent=2, ensure_ascii=False)

def linear_map (x, in_min, in_max, out_min, out_max):
  return (x - in_max) / (in_min - in_max) * (out_min - out_max) + out_max

def election_year (election):
  return int(election.split('_')[0])

def get_party_value (party_values, election, party, value):
  alias = None
  if party in party_values:
    alias = party
  else:
    for base, alias_list in party_alias.items():
      if base not in party_values:
        continue
      if election in alias_list and party in alias_list[election]:
        alias = base
        break
  if alias is None:
    return None
  
  year = election_year(election)
  values = party_values[alias]
  avail_years = values.keys()
  if year in values:
    return values[year][value]
  elif year < min(avail_years):
    return values[min(avail_years)][value]
  elif year > max(avail_years):
    return values[max(avail_years)][value]
  else:
    min_year = max([y for y in avail_years if y < year])
    max_year = min([y for y in avail_years if y > year])
    min_value = values[min_year][value]
    max_value = values[max_year][value]
    return linear_map(year, min_year, max_year, min_value, max_value)

def get_values_filename (first, second):
  return "values_%s_for_%s.json" % (second, first)

def results_to_values (first, second, party_values):
  with open(get_compare_filename(first, second), 'r') as f:
    compare_data = json.load(f)
  with open(get_result_filename(second), 'r') as f:
    result_data = json.load(f)
  
  output = {'sds':{}}
  value_lists = {}
  for first_id, items in compare_data.items():
    if not items:
      continue
    total_result = result_data['TOTAL']
    total_vote_sum = sum([float(v) for k, v in total_result.items() if k not in [TURNOUT, VOTERS]])
    weight_denom = sum([i["pop_fraction"] * float(result_data[i['id']][TURNOUT]) for i in items])
    apl_out = {}
    
    for value_key in values:
      for item in items:
        result = result_data[item['id']]
        weight = (item['pop_fraction'] * float(result[TURNOUT])) / weight_denom
        temp_list = []
        for party, vote in result.items():
          if party in [TURNOUT, VOTERS]:
            continue
          value = get_party_value(party_values, second, party, value_key)
          if value is None:
            continue
          if value_key not in value_lists:
            value_lists[value_key] = []
          if value_key not in apl_out:
            apl_out[value_key] = {
              "value": 0,
              "bias": 0,
              "bias_sd": 0,
            }
          temp_list.append([value, weight, float(vote)])
        vote_sum = sum_attr(temp_list, 2)
        apl_out[value_key]['value'] += sum([val * weight * (vote / vote_sum) for val, weight, vote in temp_list])
      value_lists[value_key].append(apl_out[value_key]["value"])
    output[first_id] = apl_out   
  
  value_sds = {}
  for value_key, value_list in value_lists.items():
    df = pd.DataFrame(value_list)
    mean = float(df.mean().iloc[0])
    sd = float(df.std().iloc[0])
    value_sds[value_key] = {
      "mean": mean,
      "sd": sd,
      "min": min(value_list),
      "max": max(value_list),
    }
  output['sds'] = value_sds
  
  for first_id in compare_data.keys():
    if first_id not in output:
      continue
    apl_out = output[first_id]
    for value_key, sds in value_sds.items():
      output[first_id][value_key]["bias"] = float(apl_out[value_key]["value"]) - sds["mean"]
      output[first_id][value_key]["bias_sd"] = (float(apl_out[value_key]["value"]) - sds["mean"]) / sds["sd"]
    
  filename = get_values_filename(first, second)
  with open(filename, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

def get_geojson_filename (election):
  return "%s.geojson" % election

def shape_to_geojson (election):
  output_filename = get_geojson_filename(election)

  sf = gpd.read_file(shape_paths[election])
  sf.to_crs(epsg=4326, inplace=True)
  fields = id_fields[election]
  sf.index = [':'.join([process_id_field(x) for x in p]) for p in zip(*[list(b) for a, b in sf[fields].items()])]
  
  sf.to_file(output_filename, index=True)

def compact_combine (combine_file, csv_file):
  with open(combine_file, 'r') as f:
    combine = json.load(f)

  csv_output = []
  csv_header = ["apl"]

  for category, category_data in combine["sds"].items():
    for key, election_data in category_data.items():
      for election, values in election_data.items():
        for value_key, value in values.items():
          if value_key not in combine:
            combine[value_key] = {}
          if category not in combine[value_key]:
            combine[value_key][category] = {}
          if key not in combine[value_key][category]:
            combine[value_key][category][key] = {}
          if election not in combine[value_key][category][key]:
            combine[value_key][category][key][election] = {}
          combine[value_key][category][key][election]["value"] = value
  del combine["sds"]

  first = True
  for apl_id, data in combine.items():
    csv_row = []
    csv_row.append(apl_id)
    for category, category_data in data.items():
      for key, election_data in category_data.items():
        if key == "summary":
          continue
        for election, values in election_data.items():
          header_key = "%s|%s" % (key, election)
          if header_key not in csv_header:
            csv_header.append(header_key)
          value = round(values["value"], 2) if values["value"] is not None else None
          csv_row.append(value)
    csv_output.append(csv_row)

  with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, dialect='unix')
    writer.writerow(csv_header)
    writer.writerows(csv_output)

def get_compact_geojson_filename (election):
  return "%s_geo.json" % election

def compact_geojson (election):
  filename = get_geojson_filename(election)
  output_filename = get_compact_geojson_filename(election)
  with open(filename, 'r') as f:
    data = json.load(f)

  for f, feature in enumerate(data["features"]):
    for l, line in enumerate(feature["geometry"]["coordinates"]):
      if feature["geometry"]["type"] == "Polygon":
        data["features"][f]["geometry"]["coordinates"][l] = polyline.encode(line, geojson=True)
      elif feature["geometry"]["type"] == "MultiPolygon":
        for p, pline in enumerate(line):
          data["features"][f]["geometry"]["coordinates"][l][p] = polyline.encode(pline, geojson=True)

  with open(output_filename, 'w') as f:
    json.dump(data, f, ensure_ascii=False)
