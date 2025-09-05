(function(){
  const form = document.getElementById('pw-form');
  const msg = document.getElementById('pw-msg');

  function getCsrf(){
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    msg.textContent = '';
    msg.className = 'msg';

    const fd = new FormData(form);
    const csrf = getCsrf();

    try {
      const res = await fetch('/api/users/change_password', {
        method: 'POST',
        body: fd,
        headers: csrf ? {'X-CSRFToken': csrf} : {}
      });
      const data = await res.json().catch(()=> ({}));

      if (!res.ok) {
        msg.textContent = data.error || ('HTTP ' + res.status);
        msg.classList.add('err');
        return;
      }
      msg.textContent = data.message || 'Password aggiornata.';
      msg.classList.add('ok');
      form.reset();
    } catch (err) {
      msg.textContent = 'Errore di rete.';
      msg.classList.add('err');
    }
  });
})();
