// var isCelsius;
let map = L.map('map').setView([40.8564635, 14.2846362], 10);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);


fetch('/coordinates')
    .then(response => response.json())
    .then(data => {
        console.log(data);
        Object.keys(data).forEach(key => {
            let coord = data[key]
            let temperature = (coord.TempIn - 32) * 5/9;
            /*
            if (isCelsius == true){
                temperature = (coord.TempIn - 32) * 5/9;
            }
            else {
                temperature = coord.TempIn
            }*/
            var popupContent = `
                <div>
                    <strong>${coord.place}</strong><br>
                    ${key}<br>
                    <img style="width:125px;" src="static/images/${key}.jpg"><br>
                    DAVIS Vantage Pro 2<br>
                    <strong>Installazione:</strong> 07/05/2024<br>
                    <strong>Temperatura:</strong> ${temperature.toFixed(2)}°C<br>
                    <strong>Umidità:</strong> ${coord.HumIn}%<br>
                    <strong>Posizione:</strong> ${coord.longitude}, ${coord.latitude}<br>
		    <img style="width:25px;" src="static/images/chart.png" onclick="openIcon('${key}','${coord.place}')">
                </div>
            `;

            let marker = L.marker([coord.longitude, coord.latitude]).addTo(map);
            marker.bindPopup(popupContent);
        });
    });

function openIcon(url, place) {
    let wsTitle = document.getElementById('ws-title');
    wsTitle.innerHTML = place;
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
