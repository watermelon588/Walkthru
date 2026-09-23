// External file: the easy site's CSP (default-src 'self') blocks inline scripts.
document.getElementById('contact').addEventListener('submit', function (e) {
  e.preventDefault(); // fixture: never leaves the page
  var err = document.getElementById('error');
  if (!this.elements.name.value.trim() || !this.elements.email.value.trim() || !this.elements.message.value.trim()) {
    err.textContent = 'Please fill in your name, email and message.';
    err.hidden = false;
    return;
  }
  err.hidden = true;
  document.getElementById('sent').hidden = false;
});
