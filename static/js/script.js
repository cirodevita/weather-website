// var isCelsius;
let map = L.map('map').setView([40.8564635, 14.2846362], 10);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri'
}).addTo(map);

let legend = L.control({position: 'topright'});

legend.onAdd = function (map) {
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML +=  '<img src="static/icons/ws_on.png" style="width:15px;">' + '     Weather Station' + '<br>'
    div.innerHTML +=  '<img src="static/icons/radar_off.png" style="width:15px;">' + '     Weather Radar' + '<br>'
    div.innerHTML +=  '<img src="static/icons/tidegauge_off.png" style="width:15px;">' + '     Tide gauge' + '<br>'
    div.innerHTML +=  '<img src="static/icons/wavebuoy_off.png" style="width:15px;">' + '     Wavebuoy ' + '<br>'
    div.innerHTML +=  '<img src="static/icons/mooring_off.png" style="width:15px;">' + '     Mooring' + '<br>'
    div.innerHTML +=  '<img src="static/icons/owbuoy_off.png" style="width:15px;">' + '     Ocean-Weather buoy ' + '<br>'
    div.innerHTML +=  '<img src="static/icons/hf_off.png" style="width:15px;">' + '     HF Radar System' + '<br>'
    div.innerHTML +=  '<img src="static/icons/glider_off.png" style="width:15px;">' + '     Glider' + '<br>'



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
            let temperature = (ws.TempIn - 32) * 5/9;
            var imgPath = `static/images/${key}.jpg`
            var installed = `<strong>Installazione:</strong> ${ws.installed}<br>`
            if (startsWithNumber(key)){
                imgPath = "static/images/work.png";
                if (key == 22){
                    imgPath = "static/images/21.jpg";
                    installed = ''
                }
                if (key == 0){
                    imgPath = "static/images/it.uniparthenope.meteo.ws2.jpg";
                }
                if (key == 9){
                    imgPath = "static/images/radar_santelmo.jpg";
                }
                if (key == 11){
                    imgPath = "static/images/ischia_mareografo.png";
                }
                if (key == 12){
                    imgPath = "static/images/tide_cmare.png";
                }
            }
            

            var popupContent = `
                <div>
                    ${ws.typology}<br>
                    <strong>${ws.place}</strong><br>
                    ${key}<br>
                    <img style="width:125px;" src="${imgPath}"><br>
                    ${ws.model}<br>
                    <strong>Ente Ospitante:</strong> ${ws.ente}<br>
                    ${installed}
                    <strong>Temperatura:</strong> ${temperature.toFixed(2)}°C<br>
                    <strong>Umidità:</strong> ${ws.HumIn}%<br>
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
