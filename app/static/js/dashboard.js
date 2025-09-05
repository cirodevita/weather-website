document.getElementById('import-btn').addEventListener('click', function() {
  fetch('/instruments', {
      method: 'POST',
  })
  .then(response => response.json())
  .then(data => {
    console.log(data);
    window.location.reload();
  })
  .catch(error => console.error('Error importing instruments:', error));
});

const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('image');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
  dropArea.classList.add('highlight');
});

['dragleave', 'drop'].forEach(eventName => {
  dropArea.classList.remove('highlight');
});

dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
  let dt = e.dataTransfer;
  let files = dt.files;
  fileInput.files = files;

  const event = new Event('change', { bubbles: true });
  fileInput.dispatchEvent(event);
}

dropArea.addEventListener('click', function() {
  const files = fileInput.files;
  if (files.length > 0) {
    console.log('Selected file:', files[0].name);
  } else {
    console.log("No file selected");
  }
});

document.getElementById("add-instrument-btn").onclick = function() {
  openModal();
};

function getInstrumentTypesFromSelect() {
  const instrumentTypes = {};
  const selectElement = document.getElementById("instrument_type");
  
  Array.from(selectElement.options).forEach(option => {
    if (option.value) {
      instrumentTypes[option.value] = option.text.trim();
    }
  });
  
  return instrumentTypes;
}

function openModal(instrument = null) {
  const modal = document.getElementById("instrument-modal");
  const title = document.getElementById("modal-title");
  const submitButton = document.getElementById("modal-submit-btn");
  const form = document.getElementById("instrument-form");

  const instrumentTypes = getInstrumentTypesFromSelect();

  if (instrument) {
      title.textContent = "Edit Instrument";
      submitButton.textContent = "Save";
      form.action = `/edit/${instrument.id}`;

      document.getElementById("instrument-id").value = instrument.id;
      document.getElementById("name").value = instrument.name;
      document.getElementById("airlinkID").value = instrument.airlinkID;
      document.getElementById("organization").value = instrument.organization;
      document.getElementById("installation_date").value = instrument.installation_date;
      document.getElementById("latitude").value = instrument.latitude;
      document.getElementById("longitude").value = instrument.longitude;
      
      const instrumentTypeValue = Object.keys(instrumentTypes).find(key => instrumentTypes[key] === instrument.instrument_type.trim());
      document.getElementById("instrument_type").value = instrumentTypeValue || "";
  } else {
      title.textContent = "Add New Instrument";
      submitButton.textContent = "Add Instrument";
      form.dataset.mode = "create";
      form.action = "/api/instruments";
      form.method = "POST";

      document.getElementById("instrument-id").value = "";
      document.getElementById("name").value = "";
      document.getElementById("airlinkID").value = "";
      document.getElementById("organization").value = "";
      document.getElementById("installation_date").value = "";
      document.getElementById("latitude").value = "";
      document.getElementById("longitude").value = "";
      document.getElementById("instrument_type").value = "";
  }

  modal.style.display = "block";
}

const editButtons = document.querySelectorAll('.edit-button');
editButtons.forEach(button => {
  button.addEventListener('click', () => {
      const instrumentId = button.getAttribute('data-id');

      const instrument = {
          id: instrumentId,
          name: button.closest('tr').querySelector('td:nth-child(3)').textContent,
          airlinkID: button.closest('tr').querySelector('td:nth-child(4)').textContent,
          organization: button.closest('tr').querySelector('td:nth-child(6)').textContent,
          installation_date: button.closest('tr').querySelector('td:nth-child(7)').textContent,
          latitude: button.closest('tr').querySelector('td:nth-child(8)').textContent.split(", ")[0],
          longitude: button.closest('tr').querySelector('td:nth-child(8)').textContent.split(", ")[1],
          instrument_type: button.closest('tr').querySelector('td:nth-child(9)').textContent.trim()
      };
      openModal(instrument);
  });
});

document.querySelector(".close").onclick = function() {
  document.getElementById("instrument-modal").style.display = "none";
};

window.onclick = function(event) {
  const modal = document.getElementById("instrument-modal");
  if (event.target === modal) {
      modal.style.display = "none";
  }
};

$(document).ready(function() {
  $('table').DataTable({
      responsive: true,
      order: [[1, 'asc']],
      paging: true,
      searching: true,
      columnDefs: [
          { orderable: true, targets: '_all' },
          { searchable: true, targets: '_all' }
      ]
  });
});

(function bindInstrumentFormSubmit(){
  const form = document.getElementById("instrument-form");
  const modal = document.getElementById("instrument-modal");

  // Recupera token CSRF se presente (hidden o meta)
  function getCsrfToken(){
    const input = form.querySelector('input[name="csrf_token"]');
    if (input && input.value) return input.value;
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  form.addEventListener('submit', async function(e){
    const mode = form.dataset.mode; // "create" o "edit"
    if (mode === "edit") {
      // Comportamento preesistente: POST tradizionale a /edit/<id>
      return; // non prevenire: lascia andare il submit normale
    }

    // mode === "create" -> intercettiamo e usiamo fetch verso /api/instruments
    e.preventDefault();

    // Validazione minima
    const id = document.getElementById("instrument-id").value.trim();
    const instrumentType = document.getElementById("instrument_type").value.trim();
    if (!id || !instrumentType) {
      alert("ID e Tipo strumento sono obbligatori.");
      return;
    }

    const fd = new FormData(form); // include anche l'immagine
    // Se serve normalizzare la data (YYYY-MM-DD):
    const dateEl = document.getElementById("installation_date");
    if (dateEl && dateEl.value) {
      // (Assumiamo già formato corretto)
      fd.set('installation_date', dateEl.value);
    }

    // CSRF header se presente
    const csrf = getCsrfToken();
    const headers = csrf ? { 'X-CSRFToken': csrf } : {};

    try {
      const res = await fetch('/api/instruments', {
        method: 'POST',
        body: fd,
        headers
      });

      if (!res.ok) {
        const err = await res.json().catch(()=>({}));
        throw new Error(err.error || ('HTTP '+res.status));
      }

      // Successo: chiudi modale e ricarica
      modal.style.display = "none";
      window.location.reload();

    } catch (err) {
      console.error('Create instrument failed:', err);
      alert('Errore nella creazione dello strumento: ' + err.message);
    }
  });
})();