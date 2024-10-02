let variablesMap = {
    "TempOut": {
        "name": "Temperatura",
        "unit": "°C"
    },
    "HumOut": {
        "name": "Umidità",
        "unit": "%"
    },
    "WindSpeed": {
        "name": "Velocità Vento",
        "unit": "km/h"
    },
    "WindDir": {
        "name": "Direzione Vento",
        "unit": "°N"
    },
    "RainRate": {
        "name": "Rain Rate",
        "unit": "mm/h"
    },
    "Barometer": {
        "name": "Pressione",
        "unit": "hPa"
    },
}

const loginBtn = document.getElementById("login-btn");
const loginModal = document.getElementById("login-modal");

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

if (loginBtn) {
    loginBtn.onclick = function() {
        loginModal.style.display = "block";
    };
}

const closeBtn = document.getElementsByClassName("close")[0];
if (closeBtn) {
    closeBtn.onclick = function() {
        loginModal.style.display = "none";
    };
}

window.onclick = function(event) {
    if (event.target == loginModal) {
        loginModal.style.display = "none";
    }
};

fetch('/instruments')
    .then(response => response.json())
    .then(data => {
        data.forEach(instrument => {
            let iconUrl = 'static/icons/' + instrument.type + '.png';

            let marker = L.marker([instrument.latitude, instrument.longitude], {
                icon: L.icon({
                    iconUrl: iconUrl,
                    iconSize: [25, 25],
                    iconAnchor: [12, 12]
                })
            }).addTo(map);

            let variables = Object.entries(instrument.variables).map(([key, value]) => `<b>${variablesMap[key]["name"]}:</b> ${value} ${variablesMap[key]["unit"]}`).join('<br>');
            
            let popupContent = `
                <div class="popup-content">
                    ${instrument.image ? `<img src="${instrument.image}" class="popup-image" alt="Instrument Image">` : ''}
                    <div class="popup-details">
                        <b>ID:</b> <a href="https://api.meteo.uniparthenope.it/grafana/d/edf1iu0nyyv40e/dashboard?orgId=1&refresh=30s&from=now-24h&to=now&var-stations=${instrument.id}&kiosk" target="_blank">${instrument.id}</a><br>
                        <b>Organization:</b> ${instrument.organization}<br>
                        ${variables ? `<br>${variables}` : ''}
                    </div>
                </div>
            `;

            marker.bindPopup(popupContent);
        });
    })
    .catch(error => console.error('Error fetching instruments:', error));
