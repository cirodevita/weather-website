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

function openModal(instrument = null) {
  const modal = document.getElementById("instrument-modal");
  const title = document.getElementById("modal-title");
  const submitButton = document.getElementById("modal-submit-btn");
  const form = document.getElementById("instrument-form");

  if (instrument) {
      title.textContent = "Edit Instrument";
      submitButton.textContent = "Save";
      form.action = `/edit/${instrument.id}`;

      document.getElementById("instrument-id").value = instrument.id;
      document.getElementById("airlinkID").value = instrument.airlinkID;
      document.getElementById("organization").value = instrument.organization;
      document.getElementById("installation_date").value = instrument.installation_date;
      document.getElementById("latitude").value = instrument.latitude;
      document.getElementById("longitude").value = instrument.longitude;
      document.getElementById("variables").value = instrument.variables;
      document.getElementById("instrument_type").value = instrument.instrument_type;
  } else {
      title.textContent = "Add New Instrument";
      submitButton.textContent = "Add Instrument";
      form.action = "/admin";

      document.getElementById("instrument-id").value = "";
      document.getElementById("airlinkID").value = "";
      document.getElementById("organization").value = "";
      document.getElementById("installation_date").value = "";
      document.getElementById("latitude").value = "";
      document.getElementById("longitude").value = "";
      document.getElementById("variables").value = "";
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
          airlinkID: button.closest('tr').querySelector('td:nth-child(2)').textContent,
          organization: button.closest('tr').querySelector('td:nth-child(4)').textContent,
          installation_date: button.closest('tr').querySelector('td:nth-child(5)').textContent,
          latitude: button.closest('tr').querySelector('td:nth-child(6)').textContent.split(", ")[0],
          longitude: button.closest('tr').querySelector('td:nth-child(6)').textContent.split(", ")[1],
          variables: button.closest('tr').querySelector('td:nth-child(7)').textContent,
          instrument_type: button.closest('tr').querySelector('td:nth-child(8)').textContent
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

