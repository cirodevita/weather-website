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
    },

    "Temp": {
        "name": "Temperatura",
        "unit": "°C",
        "icon": "temp_icon.png"
    },
    "Salt": {
        "name": "Salinità",
        "unit": "",
        "icon": ""
    },
    "Depth": {
        "name": "Profondità",
        "unit": "",
        "icon": ""
    },
    "Turbidity": {
        "name": "Torbidità",
        "unit": "",
        "icon": ""
    },
    "Oxygen": {
        "name": "Ossigeno Disciolto",
        "unit": "",
        "icon": ""
    },
    "Nitrates": {
        "name": "Nitrati",
        "unit": "",
        "icon": ""
    },
    "SeaLevel": {
        "name": "Livello del Mare",
        "unit": "",
        "icon": ""
    },
    "pm_2p5_nowcast": {
        "name": "Tipo di Precipitazione",
        "unit": "PM2.5",
        "icon": ""
    },
    "pm_1": {
        "name": "Tipo di Precipitazione",
        "unit": "PM1",
        "icon": ""
    },
    "pm_10_nowcast": {
        "name": "Tipo di Precipitazione",
        "unit": "PM10",
        "icon": ""
    },
    "aqi_nowcast_val": {
        "name": "Tipo di Precipitazione",
        "unit": "AQI",
        "icon": ""
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

(function(){
  const form   = document.getElementById('login-form');
  const errBox = document.getElementById('login-error');
  const modal  = document.getElementById('login-modal');

  // If the page has no login form, don't bind anything.
  if (!form) return;

  function getCsrf(){
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  function openLoginModal(){
    if (modal) modal.style.display = 'block';
  }

  function showError(msg){
    openLoginModal();
    if (errBox) {
      errBox.textContent = msg || 'Login failure.';
      errBox.style.display = 'block';
    } else {
      console.error('[login] ', msg);
      alert(msg || 'Login failure.');
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (errBox) { errBox.textContent = ''; errBox.style.display = 'none'; }

    const fd = new FormData(form);
    const csrf = getCsrf();

    try {
      const res = await fetch('/login', {
        method: 'POST',
        body: fd,
        headers: Object.assign(
          {'X-Requested-With': 'XMLHttpRequest'},
          csrf ? {'X-CSRFToken': csrf} : {}
        ),
      });

      // Try to parse JSON; if not JSON, treat as error
      let data = {};
      try { data = await res.json(); } catch (_) {}

      if (!res.ok || !data || !data.success) {
        const msg = (data && data.error) || 'Not valid credentials.';
        showError(msg);
        return;
      }

      window.location.href = data.redirect || '/dashboard';
    } catch (err) {
      showError('Network error. Retry');
    }
  });

  // Expose if you need to open the modal elsewhere
  window.openLoginModal = openLoginModal;
})();


let currentPage = 0;

function getItemsPerPage(page) {
    if (page === 1) {
        return 4;
    }
    return 6;
}

function getPageName(page) {
    switch (page) {
        case 0:
            return "Weather Station";
        case 1:
            return "Air Quality";
        default:
            return `Page ${page + 1}`;
    }
}

function createTable(variablesArray) {
    let variablesTable = '<table style="border-collapse: collapse; width: 100%;">';
    for (let i = 0; i < variablesArray.length; i += 3) {
        variablesTable += '<tr>';
        for (let j = i; j < i + 3 && j < variablesArray.length; j++) {
            variablesTable += variablesArray[j];
        }
        variablesTable += '</tr>';
    }
    variablesTable += '</table>';
    return variablesTable;
}

airlink_variables = ["pm_2p5_nowcast","pm_1","pm_10_nowcast" ,"aqi_nowcast_val"];

function updateTable(data, instrument, startIndex, itemsPerPage, currentPage) {

    let variablesArray = Object.entries(instrument.variables).slice(startIndex, startIndex + itemsPerPage).map(([key, value]) => {
        // If values are from AirLink, then cast to integer.
        if (airlink_variables.indexOf(key) > -1)
            val = Math.round(value);
        else
            val = value;

        let [integerPart, decimalPart] = val.toString().split(".");
        let backgroundIcon = `static/icons/weather/${variablesMap[key]["icon"]}`;
        return `
            <td class="table-cell" style="background-image: url('${backgroundIcon}');">
                <div style="font-size: 24px;">
                    ${integerPart}${decimalPart ? `<span style="font-size: 14px;">.${decimalPart}</span>` : ''}
                </div> 
                <div style="font-size: 14px;">${variablesMap[key]["unit"]}</div>
            </td>`;
    });

    let variablesTable = createTable(variablesArray);

    // Mostra le frecce solo se airlinkID ha un valore
    let paginationControls = '';
    if (instrument.airlinkID) {
        paginationControls = `
            <div style="text-align: center; margin-top: 10px;">
                <button id="prevPage" class="arrow-btn">◀</button> 
                <span>${getPageName(currentPage)}</span> 
                <button id="nextPage" class="arrow-btn">▶</button>
            </div>
        `;
    }

    let popupContent = `
        <div class="popup-content">
            ${instrument.image ? `<img src="${instrument.image}" class="popup-image" alt="Instrument Image">` : `<img src="static/images/noimage.png" class="popup-image" alt="Instrument Image">`}
            <div class="popup-details">
		<b>ID:</b> <a href="https://api.meteo.uniparthenope.it/grafana/d/edf1iu0nyyv40e/dashboard?orgId=1&refresh=30s&from=now-24h&to=now&var-station_name=${encodeURIComponent(instrument.name)}&var-station_id=${encodeURIComponent(instrument.id)}&kiosk" target="_blank">${instrument.id}</a><br>
                <b>Organization:</b> ${instrument.organization}<br>
                ${variablesArray.length > 0 ? `<br>${variablesTable}` : ''}
            </div>
        </div>
         ${paginationControls}
    `;

    return popupContent;
}

function updatePopupContent(marker, popupContent) {
    const popup = marker.getPopup();
    popup.options.closeOnClick = false;
    if (popup && marker.isPopupOpen()) {
        popup.setContent(popupContent); // Aggiorna solo il contenuto del popup
        popup.update(); // Aggiorna la visualizzazione del popup
    }
}

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

            let popupContent = updateTable(data, instrument, 0, getItemsPerPage(currentPage), currentPage);
            marker.bindPopup(popupContent);
            const pp = marker.getPopup();
            pp.options.closeOnClick = false;

            let updatePopup = (currentPage) => {
                let itemsPerPage = getItemsPerPage(currentPage); // Ottieni il numero di elementi per pagina
                let startIndex = currentPage * itemsPerPage;
                let popupContent = updateTable(data, instrument, startIndex, itemsPerPage, currentPage);
                updatePopupContent(marker, popupContent);
                
                if (instrument.airlinkID) {                    
                    document.getElementById("prevPage").onclick = function() {
                        if (currentPage > 0) {
                            currentPage--;
                            updatePopup(currentPage);
                        }
                    };
                    document.getElementById("nextPage").onclick = function() {
                        if ((currentPage + 1) * itemsPerPage < Object.entries(instrument.variables).length) {
                            currentPage++;
                            updatePopup(currentPage);
                        }
                    };
                }
            };

            marker.on('popupopen', function () {
                marker.options.closeOnClick = false;
                updatePopup(currentPage);
            });

        });
    })
    .catch(error => console.error('Error fetching instruments:', error));
