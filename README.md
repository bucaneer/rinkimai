### Rinkimų apžvalga

[Interaktyviame žemėlapyje](https://bucaneer.github.io/rinkimai) apžvelgiami parlamentinių rinkimų (Seimo ir EP) rezultatai nuo 2016 metų. Atvaizdavimas orientuotas į 2024 m. Seimo rinkimus – naudojamos šių rinkimų apylinkių ribos bei dalyvaujančių partijų pavadinimai.

Ankstesnių rinkimų rezultatai perskaičiuoti atsižvelgiant į besikeičiančių [apylinkių ribų](https://www.vrk.lt/rinkimu-teritoriju-gis-duomenys) persidengimą bei [gyventojų tankį pagal 2021 m. gyventojų surašymą](https://open-data-ls-osp-sdg.hub.arcgis.com/datasets/ff7b85eaf2e64032bdb564f878026a7c_21/about).

Ankstesniuose rinkimuose dalyvavusių partijų pavadinimai pakeisti atsižvelgiant į vėlesnius pervadinimus (pvz. LSDDP → LRP) ar susijungimus (pvz. TT + LLS → LT).

Politinės vertybės apskaičiuotos pagal partijų atsakymus projekto [Mano balsas](https://www.manobalsas.lt) anketose bei rinkimų rezultatus.

#### Failai
 * `data.csv` – apibendrinti rinkimų duomenys
 * `generate.py` – apibendrintų duomenų apskaičiavimo skriptas
 * `2024_LRS_geo.json` – 2024 m. Seimo rinkimų apylinkių ribos modfikuotu GeoJSON formatu (naudojant koordinačių kodavimą pagal [Google Polyline](https://developers.google.com/maps/documentation/utilities/polylinealgorithm) formatą)
 * `index.html` – interaktyvus žemėlapis atvaizdavimui naršyklėje
 * katalogas `includes` – interaktyvaus žemėlapio skriptai ir kiti pagalbiniai failai

-----------

### Election overview

[Interactive map](https://bucaneer.github.io/rinkimai) summarizes the results of parliamentary (Seimas and EP) election results in Lithuania since 2016.
