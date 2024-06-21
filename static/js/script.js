// var isCelsius;
let map = L.map('map').setView([40.8564635, 14.2846362], 10);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

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

            if (startsWithNumber(key)){
                imgPath = "static/images/work.png"
            }

            var popupContent = `
                <div>
                    ${ws.typology}<br>
                    <strong>${ws.place}</strong><br>
                    ${key}<br>
                    <img style="width:125px;" src="${imgPath}"><br>
                    ${ws.model}<br>
                    <strong>Ente Ospitante:</strong> ${ws.ente}<br>
                    <strong>Installazione:</strong> ${ws.installed}<br>
                    <strong>Temperatura:</strong> ${temperature.toFixed(2)}°C<br>
                    <strong>Umidità:</strong> ${ws.HumIn}%<br>
                    <strong>Posizione:</strong> ${ws.longitude}, ${ws.latitude}<br>
                    <img style="width:25px;" src="static/icons/chart.png" onclick="openIcon('${key}','${ws.place}')">
                </div>
            `;
            iconPath = 'static/icons/' + ws.type + '.png'
            var customIcon = new L.icon({iconUrl: iconPath,
                                        iconSize:     [40, 40],
                                        iconAnchor:   [0, 10],
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
