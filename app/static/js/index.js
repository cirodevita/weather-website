let variablesMap = {
    
    "HumOut": {
        "name": "Umidità",
        "unit": "%",
        "icon": "humidity_icon.png"
    },
    "WindSpeed": {
        "name": "Velocità Vento",
        "unit": "km/h",
        "icon": "wind_speed_icon.png"
    },
    "WindDir": {
        "name": "Direzione Vento",
        "unit": "°N",
        "icon": "wind_dir_icon.png"
    },
    "RainRate": {
        "name": "Rain Rate",
        "unit": "mm/h",
        "icon": "rain_icon.png"
    },
    "Barometer": {
        "name": "Pressione",
        "unit": "hPa",
        "icon": "press_icon.png"
    },
    "TempOut": {
        "name": "Temperatura",
        "unit": "°C",
        "icon": "temp_icon.png"
    }
};


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

            let variablesArray = Object.entries(instrument.variables).map(([key, value]) => {
                let [integerPart, decimalPart] = value.toString().split(".");

                let backgroundIcon = `static/icons/weather/${variablesMap[key]["icon"]}`;

                return `
                        <td class="table-cell" style="background-image: url('${backgroundIcon}');">
                            <div class="large-text">
                                ${integerPart}${decimalPart ? `<span class="small-text">.${decimalPart}</span>` : ''}
                            </div> 
                            <div class="small-text">${variablesMap[key]["unit"]}</div>
                        </td>`;
            });

            let variablesTable = '<table style="border-collapse: collapse; width: 100%;">';
            for (let i = 0; i < variablesArray.length; i += 3) {
                variablesTable += '<tr>';
                for (let j = i; j < i + 3 && j < variablesArray.length; j++) {
                    variablesTable += variablesArray[j];
                }
                variablesTable += '</tr>';
            }
            variablesTable += '</table>';

            let popupContent = `
                <div class="popup-content">
                    ${instrument.image ? `<img src="${instrument.image}" class="popup-image" alt="Instrument Image">` : `<img src="static/images/noimage.png" class="popup-image" alt="Instrument Image">`}
                    <div class="popup-details">
                        <b>ID:</b> <a href="https://api.meteo.uniparthenope.it/grafana/d/edf1iu0nyyv40e/dashboard?orgId=1&refresh=30s&from=now-24h&to=now&var-stations=${instrument.id}&kiosk" target="_blank">${instrument.id}</a><br>
                        <b>Organization:</b> ${instrument.organization}<br>
                        <img style="width: 20px"; src="static/icons/csv_icon.png">
                        ${variablesArray.length > 0 ? `<br>${variablesTable}` : ''}
                    </div>
                </div>
            `;

            marker.bindPopup(popupContent);
        });
    })
    .catch(error => console.error('Error fetching instruments:', error));