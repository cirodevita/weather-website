// var isCelsius;
let map = L.map('map').setView([40.8564635, 14.2846362], 10);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri'
}).addTo(map);

let legend = L.control({position: 'topright'});

legend.onAdd = function (map) {
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML +=  '<img src="static/images/logo_most.png" style="width:150px;"><br>'
    div.innerHTML +=  '<img src="static/images/logo_parthenope_black.png" style="width:150px;"><br><br><br>'
    
    div.innerHTML +=  '<img src="static/icons/ws_on.png" style="width:15px;">' + '     Stazione Meteorologica' + '<br>'
    div.innerHTML +=  '<img src="static/icons/radar_off.png" style="width:15px;">' + '     Radar Meteorologico' + '<br>'
    div.innerHTML +=  '<img src="static/icons/tidegauge_off.png" style="width:15px;">' + '     Mareografo' + '<br>'
    div.innerHTML +=  '<img src="static/icons/wavebuoy_off.png" style="width:15px;">' + '     Ondametro ' + '<br>'
    div.innerHTML +=  '<img src="static/icons/mooring_off.png" style="width:15px;">' + '     Mooring' + '<br>'
    div.innerHTML +=  '<img src="static/icons/owbuoy_off.png" style="width:15px;">' + '     Boa Meteo-Oceanografica ' + '<br>'
    div.innerHTML +=  '<img src="static/icons/hf_off.png" style="width:15px;">' + '     HF Radar' + '<br>'
    div.innerHTML +=  '<img src="static/icons/glider_off.png" style="width:15px;">' + '     Glider' + ''
    



    return div;
};

legend.addTo(map);

function startsWithNumber(str) {
    return /^\d/.test(str);
}

fetch('/coordinates')
    .then(response => response.json())
    .then(rawData => {
        console.log(rawData);
        Object.keys(rawData).forEach(key => {
            let ws = rawData[key]
            let temperature = (ws.TempOut - 32) * 5/9;
            var model = `${ws.model}`
            var imgPath = `static/images/${key}.jpg`
            var ente = `<strong>Ente Ospitante:</strong> ${ws.ente}<br>`
            var installed = `<strong>Installazione:</strong> ${ws.installed}<br>`
            var temperatures = `<strong>Temperatura:</strong> ${temperature.toFixed(2)}°C<br> <strong>Umidità:</strong> ${ws.HumOut}%<br>`
            if (key == 'it.uniparthenope.meteo.ws5'){
                temperatures = `<strong>Temperatura:</strong> ${temperature.toFixed(2)} °C<br> <strong>Umidità:</strong> ${ws.HumOut} %<br> <strong>Pressione:</strong> ${ws.Barometer} hPa<br> <strong>Velocità Vento:</strong> ${ws.WindSpeed} km/h<br> <strong>Direzione Vento:</strong> ${ws.WindDir} °<br> <strong>Rain Rate:</strong> ${ws.RainRate} mm/h<br>`
                ente = `<strong>Ente Ospitante:</strong> IMAT<br>`;
            }
            if (startsWithNumber(key)){
                imgPath = "static/images/work.png";
                if (key == 22){
                    imgPath = "static/images/21.jpg";
                    temperatures = `<strong>Temperatura:</strong> N/A°C<br><strong>Salinità:</strong> N/A<br><strong>Profondità:</strong> N/A<br><strong>Torbidità:</strong> N/A <br><strong>Ossigeno Disciolto:</strong> N/A <br><strong>Nitrati:</strong> N/A<br>`
                    installed = ''
                    ente = `<strong>Ente Proprietario:</strong> Parthenope<br>`
                    model = `Sea Explorer`
                }
                if (key == 0){
                    imgPath = "static/images/it.uniparthenope.meteo.ws2.jpg";

                }
                if (key == 9){
                    imgPath = "static/images/radar_santelmo.jpg";
                    ente = `<strong>Ente Ospitante:</strong> Castel Sant'Elmo<br>`
                    temperatures = `<strong>Tipo di Precipitazione:</strong> N/A<br>`
                    model = `WR-10X `
                    installed = `<strong>Installazione:</strong> 2011<br>`

                }
                if (key == 11){
                    imgPath = "static/images/ischia_mareografo.png";
                }
                if (key == 12){
                    imgPath = "static/images/tide_cmare.png";
                    temperatures = `<strong>Livello del Mare:</strong> N/A<br>`
                    installed = `<strong>Installazione:</strong> 2011<br>`
                    ente = `<strong>Ente Ospitante:</strong>Porto Turistico<br>`
                }
            }
            

            var popupContent = `
                <div>
                    ${ws.typology}<br>
                    <strong>${ws.place}</strong><br>
                    ${key}<br>
                    <img style="width:125px;" src="${imgPath}"><br>
                    ${model}<br>
                    ${ente}
                    ${installed}
                    ${temperatures}
                    <strong>Posizione:</strong> ${ws.longitude}, ${ws.latitude}<br>
                    <img style="width:25px;" src="static/icons/chart.png" onclick="openIcon('${key}','${ws.place}')">
                </div>
            `;
            iconPath = 'static/icons/' + ws.type + '.png'
            var customIcon = new L.icon({iconUrl: iconPath,
                                        iconSize:     [25, 25],
                                        iconAnchor:   [20, 20],
                                        });
            let marker = L.marker([ws.longitude, ws.latitude], {icon: customIcon}).addTo(map);
            marker.bindPopup(popupContent);
        });
    });

function openIcon(url, place) {
    let mapContainer = document.getElementById('map-container');
    let iframeContainer = document.getElementById('iframe-container');
    let grafanaIframe = document.getElementById('grafana-iframe');
    grafanaIframe.src = `http://193.205.230.6:3000/d/edf1iu0nyyv40e/dashboard?orgId=1&refresh=30s&from=now-24h&to=now&var-stations=${url}&kiosk`;
    iframeContainer.style.display = 'flex';
    mapContainer.style.flex = '1';
    iframeContainer.style.flex = '1';
}

/*
document.getElementById('toggle-temp').addEventListener('click', function() {
    isCelsius = !isCelsius;
    // Update the temperature display logic here
    alert('Temperature unit changed to ' + (isCelsius ? 'Celsius' : 'Fahrenheit'));
});
*/
