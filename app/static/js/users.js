(function(){
  const modal = document.getElementById('add-user-modal');
  const btnTop = document.getElementById('add-user-btn');
  const btnBottom = document.getElementById('add-user-btn-bottom');
  const closeBtn = document.getElementById('add-user-close');
  const cancelBtn = document.getElementById('add-user-cancel');
  const form = document.getElementById('add-user-form');
  const usersList = document.getElementById('users-list');

  function getCsrf(){
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  function openModal(){ modal.style.display = 'block'; }
  function closeModal(){ modal.style.display = 'none'; form.reset(); }

  [btnTop, btnBottom].forEach(b => b && b.addEventListener('click', openModal));
  closeBtn && closeBtn.addEventListener('click', closeModal);
  cancelBtn && cancelBtn.addEventListener('click', closeModal);
  window.addEventListener('click', (e)=>{ if(e.target === modal) closeModal(); });

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const fd = new FormData(form);
    const csrf = getCsrf();
    const res = await fetch('/api/users', {
      method: 'POST',
      body: fd,
      headers: csrf ? {'X-CSRFToken': csrf} : {}
    });
    const data = await res.json().catch(()=> ({}));
    if(!res.ok){
      alert(data.error || ('HTTP '+res.status));
      return;
    }
    window.location.reload();
  });

  // DELETE user
  usersList.addEventListener('click', async (e)=>{
    const btn = e.target.closest('.delete-user-btn');
    if(!btn) return;
    const row = btn.closest('.user-row');
    const id = row.getAttribute('data-user-id');
    if(!id) return;

    if(!confirm('Confermi l\'eliminazione di questo utente?')) return;

    const csrf = getCsrf();
    const res = await fetch(`/api/users/${id}`, {
      method: 'DELETE',
      headers: Object.assign({'Accept':'application/json'}, csrf ? {'X-CSRFToken': csrf} : {})
    });
    const data = await res.json().catch(()=> ({}));
    if(!res.ok){
      alert(data.error || ('HTTP '+res.status));
      return;
    }
    row.remove();
  });
})();
